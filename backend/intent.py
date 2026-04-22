"""
Inflx Intent Detection Module
Classifies user messages into exactly 3 categories:
  - greeting: Casual greetings and hellos
  - pricing: Product, pricing, feature, or policy inquiries
  - high_intent: User signals readiness to buy, sign up, or convert

Uses LLM-based classification with keyword fallback for robustness.
"""

import logging
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("inflx.intent")

# Keyword fallback sets
GREETING_KEYWORDS = {
    "hi", "hello", "hey", "howdy", "greetings", "good morning",
    "good afternoon", "good evening", "what's up", "sup", "yo",
}

HIGH_INTENT_KEYWORDS = {
    "buy", "purchase", "subscribe", "sign up", "signup", "register",
    "i want", "i need", "interested", "get started", "enroll",
    "join", "i'll take", "i'd like to", "count me in", "let's go",
    "start", "upgrade", "go with", "choose", "pick",
}

PRICING_KEYWORDS = {
    "price", "pricing", "cost", "plan", "plans", "how much",
    "basic", "pro", "features", "refund", "support", "policy",
    "video", "quality", "4k", "720p", "caption", "captions",
    "platform", "youtube", "instagram", "tiktok", "compare",
    "difference", "include", "offer", "what do you",
}


from typing import Tuple
import json

def _keyword_fallback(message: str) -> Tuple[str, float]:
    """Fallback intent detection using keyword matching."""
    msg_lower = message.lower().strip()

    # Check high intent first (more specific) - action words take priority
    for kw in HIGH_INTENT_KEYWORDS:
        if kw in msg_lower:
            return "high_intent", 0.7

    # Check pricing/product - but only if no action words found
    for kw in PRICING_KEYWORDS:
        if kw in msg_lower:
            # If message has both pricing keywords AND action context, treat as high_intent
            has_action_context = any(action in msg_lower for action in ["i want", "i need", "i'll take", "sign me", "buy", "purchase"])
            if has_action_context:
                return "high_intent", 0.7
            return "pricing", 0.7

    # Check greeting
    for kw in GREETING_KEYWORDS:
        if kw in msg_lower:
            return "greeting", 0.8

    # Unclear input
    return "unknown", 0.2


def detect_intent(message: str, conversation_history: list = None) -> Tuple[str, float]:
    """
    Classify user message into one of 3 intents using LLM with confidence output.
    
    Args:
        message: The user's current message
        conversation_history: Previous messages for context
        
    Returns:
        Tuple[str, float]: (intent_label, confidence_score)
    """
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0,
            max_tokens=150,
        )

        # Build context from history
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            recent = conversation_history[-4:]  # Last 2 turns
            history_context = "\n".join(
                [f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content']}" for m in recent]
            )

        prompt = f"""You are an expert intent classifier for an AI agent.
Analyze the user message and determine the correct intent block.
If the message is entirely unclear, gibberish, or irrelevant, classify as "unknown".

Categories:
1. "greeting" - Casual greetings, hellos, how are you
2. "pricing" - Questions about products, pricing, features, plans, policies, support, platforms. (e.g. "Tell me your plans", "What are the features?")
3. "high_intent" - User explicitly wants to buy, subscribe, sign up, get started, or shows direct transaction intent. (e.g. "I want to buy", "Sign me up", "I want Pro plan")
4. "unknown" - Unclear, gibberish, or entirely out of scope

CRITICAL RULES:
- If the message contains action words ("I want", "I need", "I'll take", "sign me up", "buy", "purchase") combined with a plan name, classify as "high_intent".
- Merely asking about "plans" or "pricing" without action words is "pricing", NOT "high_intent".
- "high_intent" requires a clear action phrase indicating readiness to convert right now.
- Examples: "I want Pro plan" = high_intent, "Tell me about Pro plan" = high_intent, "What are the plans?" = pricing

Recent conversation context:
{history_context}

User message: "{message}"

Output ONLY valid JSON with no markdown formatting.
Schema: {{"intent": "one of the 4 categories", "confidence": <float between 0.0 and 1.0>}}"""

        response = llm.invoke(prompt)
        content = response.content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        intent = data.get("intent", "unknown").lower()
        confidence = float(data.get("confidence", 0.5))

        # Validate response
        valid_intents = {"greeting", "pricing", "high_intent", "unknown"}
        if intent in valid_intents:
            logger.info(f"[Intent: {intent}] [Confidence: {confidence}] (LLM)")
            return intent, confidence
        
        # If LLM returned invalid intent, fall back
        logger.warning(f"LLM returned invalid intent '{intent}', using fallback")
        intent, conf = _keyword_fallback(message)
        logger.info(f"[Intent: {intent}] [Confidence: {conf}] (Fallback)")
        return intent, conf

    except Exception as e:
        logger.error(f"LLM intent detection failed: {e}")
        intent, conf = _keyword_fallback(message)
        logger.info(f"[Intent: {intent}] [Confidence: {conf}] (Fallback Error)")
        return intent, conf
