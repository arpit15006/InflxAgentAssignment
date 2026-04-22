"""
AutoStream LangGraph Agent — Stateful Conversational Workflow
Implements a state machine with 4 nodes and conditional routing.

Nodes:
  1. detect_intent → Classifies into 3 categories (greeting | pricing | high_intent)
  2. handle_greeting → Returns friendly greeting
  3. handle_rag → FAISS retrieval + LLM response generation
  4. handle_lead_flow → Multi-step lead capture (ask_name → ask_email → ask_platform → tool)

Session-based memory maintains 5-6 turns per conversation.
"""

import logging
from typing import Dict

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from state import AgentState, create_initial_state, MAX_MEMORY_TURNS
from intent import detect_intent
from rag import retrieve_and_respond
from tools import (
    mock_lead_capture,
    is_valid_name,
    is_valid_email,
    is_valid_platform,
    is_valid_plan,
    looks_like_intent,
    looks_like_question,
    extract_plan_from_context,
)

load_dotenv()
logger = logging.getLogger("autostream.agent")

# ============================================================
# Session Store — Dictionary-based memory for 5-6 turn retention
# ============================================================
session_store: Dict[str, AgentState] = {}


def get_or_create_session(session_id: str) -> AgentState:
    """Retrieve existing session or create a new one."""
    if session_id not in session_store:
        session_store[session_id] = create_initial_state(session_id)
        logger.info(f"New session created: {session_id}")
    return session_store[session_id]


def save_session(state: AgentState):
    """Persist session state with memory trimming (max 5-6 turns)."""
    session_id = state["session_id"]
    # Trim messages to maintain 5-6 turn window
    if len(state["messages"]) > MAX_MEMORY_TURNS * 2:
        state["messages"] = state["messages"][-(MAX_MEMORY_TURNS * 2):]
    session_store[session_id] = state


# ============================================================
# Node 1: Intent Detection
# ============================================================
def intent_detection_node(state: AgentState) -> dict:
    """
    Detect intent from user message.
    If already in lead capture flow (stage != idle), keep high_intent.
    """
    # We allow ML detection to process every message so we can handle interruptions (like a user suddenly asking a pricing question while in the flow)

    user_message = state["messages"][-1]["content"] if state["messages"] else ""
    intent, confidence = detect_intent(user_message, state["messages"])
    
    logger.info(f"[Intent: {intent}] [Confidence: {confidence}]")
    return {"intent": intent, "confidence": confidence}


# ============================================================
# Node 2: Greeting Handler
# ============================================================
def greeting_node(state: AgentState) -> dict:
    """Handle greeting messages with a friendly response."""
    responses = [
        "Hey there! Welcome to AutoStream! I'm your AI assistant. I can help you with our pricing plans, features, or get you started with our platform. What would you like to know?",
        "Hello! Great to have you here at AutoStream! I can help you explore our content creation plans, answer your questions, or help you get started. How can I assist you today?",
        "Hi! Welcome to AutoStream - your AI-powered content creation platform! Feel free to ask me about our plans, features, or anything else. What's on your mind?",
    ]
    import random
    response = random.choice(responses)
    logger.info("[Response: Greeting]")
    return {"response": response}


# ============================================================
# Node 3: RAG Retrieval Handler
# ============================================================
def rag_node(state: AgentState) -> dict:
    """Handle pricing/product queries using FAISS RAG pipeline."""
    user_message = state["messages"][-1]["content"] if state["messages"] else ""
    
    logger.info("[RAG: Retrieving from FAISS vector store]")
    response = retrieve_and_respond(user_message, state["messages"])
    logger.info("[Response: RAG-generated]")
    return {"response": response}


# ============================================================
# Node 4: Fallback / Unknown Intent Handler
# ============================================================
def unknown_node(state: AgentState) -> dict:
    """Handle unclear, low-confidence, or gibberish inputs."""
    logger.info("[Response: Fallback requested clarification]")
    return {
        "response": "I didn't quite catch that. Could you please clarify your request? I can help you with pricing, features, or sign you up!"
    }


# ============================================================
# Node 5: Lead Capture Flow Handler
# ============================================================
def _get_return_prompt(stage: str) -> str:
    """Get the appropriate prompt to return user to the correct stage."""
    prompts = {
        "ask_name": "Please share your **name** to continue.",
        "ask_email": "Please share your **email address** to continue.",
        "ask_platform": "Please tell me which **platform** you use (YouTube, Instagram, or TikTok) to continue.",
        "ask_plan": "Please select a **plan** (Basic or Pro) to continue.",
    }
    return prompts.get(stage, "Let's continue the signup process.")


def lead_flow_node(state: AgentState) -> dict:
    """
    Multi-step lead capture workflow with input validation and interruption handling.
    
    Flow: ask_name → ask_email → ask_platform → tool execution
    
    Key behaviors:
    - Validates input semantically before field assignment
    - Handles interruptions (questions, new intents) gracefully
    - Maintains stage progression
    - STRICT GUARD: Tool executes ONLY when ALL 3 fields collected
    """
    stage = state["stage"]
    user_message = state["messages"][-1]["content"].strip() if state["messages"] else ""

    # ---- Entry point: first time high intent is detected ----
    if stage in ("idle", "complete", ""):
        logger.info("[Stage: idle → ask_name]")
        
        # Try to extract plan from history using LLM
        plan = extract_plan_from_context(user_message, state["messages"])
        
        if not plan:
            # Fallback to keyword matching in current message
            user_message_lower = user_message.lower()
            if "pro" in user_message_lower or "4k" in user_message_lower:
                plan = "Pro"
            elif "basic" in user_message_lower or "720p" in user_message_lower:
                plan = "Basic"
        
        response_msg = "That's great to hear! I'd love to help you get started. Could you please share your **name**?"
        if plan:
            response_msg = f"That's great to hear! I'd love to help you get started with our **{plan}** plan. Could you please share your **name**?"
        
        return {
            "stage": "ask_name",
            "plan": plan,
            "response": response_msg,
        }

    # ---- INTERRUPTION HANDLING ----
    # If user asks a question during lead flow, answer it then return to flow
    if looks_like_question(user_message):
        logger.info(f"[Interruption: Question detected in stage '{stage}']")
        rag_response = retrieve_and_respond(user_message, state["messages"])
        prompt_to_return = _get_return_prompt(stage)
        return {
            "response": f"{rag_response}\n\n{prompt_to_return}",
            # Keep the same stage - don't advance
        }
    
    # If user shows high intent again during lead flow, acknowledge and continue
    if looks_like_intent(user_message) and stage != "idle":
        logger.info(f"[Interruption: High intent detected in stage '{stage}']")
        
        # Check if user is changing their plan selection
        new_plan = ""
        user_message_lower = user_message.lower()
        if "basic" in user_message_lower:
            new_plan = "Basic"
        elif "pro" in user_message_lower:
            new_plan = "Pro"
        
        prompt_to_return = _get_return_prompt(stage)
        
        if new_plan:
            # User specified a plan change, acknowledge and update
            logger.info(f"[Plan changed to: {new_plan}]")
            return {
                "plan": new_plan,
                "response": f"Got it! I've updated your selection to the **{new_plan}** plan. Let's continue signup. {prompt_to_return}",
            }
        else:
            # Just high intent, continue flow
            return {
                "response": f"Got it! Let's continue signup. {prompt_to_return}",
            }

    # ---- Stage: Collecting Name ----
    if stage == "ask_name":
        if len(user_message) < 2:
            return {"response": "I didn't catch that. Could you please tell me your name?"}
        
        if not is_valid_name(user_message):
            return {
                "response": "That doesn't look like a valid name. Could you please provide your name? (Letters only, at least 2 characters)",
            }
        
        name = user_message.strip()
        logger.info(f"[Stage: ask_name → ask_email] Name captured: {name}")
        return {
            "stage": "ask_email",
            "name": name,
            "response": f"Thanks, **{name}**! Could you share your **email address** so we can set up your account?",
        }

    # ---- Stage: Collecting Email ----
    if stage == "ask_email":
        email = user_message.strip()
        
        # Validate email format
        if not is_valid_email(email):
            logger.warning(f"Invalid email format: {email}")
            return {
                "response": "That doesn't look like a valid email address. Could you please provide a valid email? (e.g., name@example.com)",
            }
        
        logger.info(f"[Stage: ask_email → ask_platform] Email captured: {email}")
        return {
            "stage": "ask_platform",
            "email": email,
            "response": f"Perfect! And which **platform** do you primarily create content on? (e.g., YouTube, Instagram, TikTok)",
        }

    # ---- Stage: Collecting Platform ----
    if stage == "ask_platform":
        if len(user_message) < 1:
            return {"response": "Could you please tell me which platform you create content on?"}
        
        platform_input = user_message.strip().lower()
        allowed_platforms = ["youtube", "instagram", "tiktok"]
        
        # Simple Validation Layer
        matched_platform = None
        for allowed in allowed_platforms:
            if allowed in platform_input:
                matched_platform = allowed.capitalize()
                break
                
        if not matched_platform:
            logger.warning(f"Invalid platform entered: {platform_input}")
            return {
                "response": "I didn't recognize that platform. We currently support **YouTube**, **Instagram**, and **TikTok**. Which of these do you use?",
            }
            
        platform = matched_platform
        existing_plan = state.get("plan", "")
        
        logger.info(f"[Stage: ask_platform] Platform captured: {platform}, Existing plan: {existing_plan}")
        
        # If plan was already captured from initial message, skip asking for it
        if existing_plan:
            name = state.get("name", "")
            email = state.get("email", "")
            plan = existing_plan

            logger.info(f"[Stage: ask_platform → execute] Using existing plan: {plan}")

            # ==========================================
            # STRICT GUARD — Execute tool ONLY when ALL fields present
            # ==========================================
            if not name or not email or not platform or not plan:
                logger.error("GUARD TRIGGERED: Attempted tool execution with missing fields")
                return {
                    "response": "I still need some information. Let me ask again — what is your name?",
                    "stage": "ask_name",
                    "name": "",
                    "email": "",
                    "platform": "",
                    "plan": "",
                }

            # Execute lead capture tool
            logger.info("[Tool Triggered: Lead Capture]")
            result = mock_lead_capture(name, email, platform, plan)
            logger.info(f"[Lead Captured: {name}, {email}, {platform}, {plan}]")

            return {
                "stage": "complete",
                "platform": platform,
                "plan": plan,
                "response": (
                    f"**Awesome, {name}!** Your lead has been captured successfully!\n\n"
                    f"Here's a summary:\n"
                    f"- **Name:** {name}\n"
                    f"- **Email:** {email}\n"
                    f"- **Platform:** {platform}\n"
                    f"- **Plan:** {plan}\n\n"
                    f"Our team will reach out to you shortly to help you get started with AutoStream. "
                    f"Welcome aboard!"
                ),
            }
        else:
            # Plan not specified, ask for it
            return {
                "stage": "ask_plan",
                "platform": platform,
                "response": "Great choice! Now, which **plan** are you interested in? We offer **Basic** ($29/month - 10 videos, 720p) and **Pro** ($79/month - unlimited videos, 4K, AI captions).",
            }

    # ---- Stage: Collecting Plan ----
    if stage == "ask_plan":
        if len(user_message) < 1:
            return {"response": "Could you please tell me which plan you're interested in (Basic or Pro)?"}
        
        plan_input = user_message.strip().lower()
        
        # Validate plan
        if not is_valid_plan(plan_input):
            logger.warning(f"Invalid plan entered: {plan_input}")
            return {
                "response": "I didn't recognize that plan. We offer **Basic** ($29/month) and **Pro** ($79/month). Which one would you like?",
            }
        
        # Match plan
        plan = "Basic" if "basic" in plan_input else "Pro"
        name = state.get("name", "")
        email = state.get("email", "")
        platform = state.get("platform", "")

        logger.info(f"[Stage: ask_plan → execute] Plan captured: {plan}")

        # ==========================================
        # STRICT GUARD — Execute tool ONLY when ALL fields present
        # ==========================================
        if not name or not email or not platform or not plan:
            logger.error("GUARD TRIGGERED: Attempted tool execution with missing fields")
            return {
                "response": "I still need some information. Let me ask again — what is your name?",
                "stage": "ask_name",
                "name": "",
                "email": "",
                "platform": "",
                "plan": "",
            }

        # Execute lead capture tool
        logger.info("[Tool Triggered: Lead Capture]")
        result = mock_lead_capture(name, email, platform, plan)
        logger.info(f"[Lead Captured: {name}, {email}, {platform}, {plan}]")

        return {
            "stage": "complete",
            "plan": plan,
            "response": (
                f"**Awesome, {name}!** Your lead has been captured successfully!\n\n"
                f"Here's a summary:\n"
                f"- **Name:** {name}\n"
                f"- **Email:** {email}\n"
                f"- **Platform:** {platform}\n"
                f"- **Plan:** {plan}\n\n"
                f"Our team will reach out to you shortly to help you get started with AutoStream. "
                f"Welcome aboard!"
            ),
        }

    # Fallback
    return {"response": "I'm here to help! What would you like to know about AutoStream?", "stage": "idle"}


# ============================================================
# Conditional Edge: Route based on intent
# ============================================================
def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate handler based on detected intent."""
    stage = state.get("stage")
    intent = state.get("intent", "")
    confidence = state.get("confidence", 1.0)
    user_message = state["messages"][-1]["content"].lower() if state["messages"] else ""
    
    # --- PRIORITY RULE: If in lead flow, stay in lead flow ---
    if stage and stage not in ("idle", "complete", ""):
        # The lead_flow_node will handle interruptions internally
        return "lead_flow"

    # --- IF WE ARE IDLE (Standard Routing) ---
    # Fallback for completely unclear inputs
    if intent == "unknown" or confidence < 0.3:
        return "unknown"
    
    if intent == "greeting":
        return "greeting"
    elif intent == "pricing":
        return "rag"
    elif intent == "high_intent":
        return "lead_flow"
    else:
        return "unknown"


# ============================================================
# Build LangGraph Workflow
# ============================================================
def build_agent_graph() -> StateGraph:
    """
    Construct the LangGraph state machine.
    
    Graph structure:
        START → detect_intent
        detect_intent → greeting | rag | lead_flow (conditional)
        greeting → END
        rag → END
        lead_flow → END
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("detect_intent", intent_detection_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("lead_flow", lead_flow_node)
    workflow.add_node("unknown", unknown_node)

    # Set entry point
    workflow.set_entry_point("detect_intent")

    # Add conditional edges from intent detection
    workflow.add_conditional_edges(
        "detect_intent",
        route_by_intent,
        {
            "greeting": "greeting",
            "rag": "rag",
            "lead_flow": "lead_flow",
            "unknown": "unknown",
        },
    )

    # All handler nodes go to END
    workflow.add_edge("greeting", END)
    workflow.add_edge("rag", END)
    workflow.add_edge("lead_flow", END)
    workflow.add_edge("unknown", END)

    return workflow


# Compile the graph
agent_graph = build_agent_graph()
agent_app = agent_graph.compile()


# ============================================================
# Main entry point for processing messages
# ============================================================
def process_message(message: str, session_id: str) -> str:
    """
    Process a user message through the agent workflow.
    
    Args:
        message: User's message text
        session_id: Unique session identifier for state tracking
        
    Returns:
        Agent's response string
    """
    if not message or not message.strip():
        return "I didn't receive a message. Could you try again?"

    # Get or create session state
    state = get_or_create_session(session_id)

    # Add user message to conversation history
    state["messages"].append({"role": "user", "content": message.strip()})

    # Run the agent graph
    result = agent_app.invoke(state)

    # Update state with results
    state.update({
        "intent": result.get("intent", state.get("intent", "")),
        "stage": result.get("stage", state.get("stage", "idle")),
        "name": result.get("name", state.get("name", "")),
        "email": result.get("email", state.get("email", "")),
        "platform": result.get("platform", state.get("platform", "")),
        "plan": result.get("plan", state.get("plan", "")),
        "response": result.get("response", ""),
    })

    # Add agent response to conversation history
    response = state["response"]
    state["messages"].append({"role": "assistant", "content": response})

    # Save session with memory trimming
    save_session(state)

    logger.info(f"[Session: {session_id}] [Messages: {len(state['messages'])}] [Stage: {state['stage']}]")

    return response
