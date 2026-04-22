"""
Inflx Lead Capture Tool
Executes lead capture ONLY when ALL required fields are collected.

STRICT GUARD: Tool must NOT be triggered until name, email, AND platform
are ALL present and validated.
"""

import re
import logging

logger = logging.getLogger("inflx.tools")


def is_valid_name(text: str) -> bool:
    """Validate name: letters, spaces, hyphens, dots, and apostrophes, length >= 2"""
    # Block purely numeric strings and ensure it contains at least one letter
    has_letter = any(c.isalpha() for c in text)
    valid_chars = bool(re.match(r"^[a-zA-Z0-9\s\-\.\']{2,}$", text.strip()))
    return has_letter and valid_chars


def is_valid_email(text: str) -> bool:
    """Validate email format using regex"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return bool(re.match(pattern, text.strip()))


def is_valid_platform(text: str) -> bool:
    """Validate platform is one of allowed platforms"""
    allowed = {"youtube", "instagram", "tiktok"}
    return text.strip().lower() in allowed


def is_valid_plan(text: str) -> bool:
    """Validate plan is one of allowed plans"""
    allowed = {"basic", "pro"}
    return text.strip().lower() in allowed


def looks_like_intent(text: str) -> bool:
    """Check if text contains high-intent keywords"""
    high_intent_keywords = {
        "buy", "purchase", "subscribe", "sign up", "signup", "sign me up", "register",
        "i want", "i need", "interested", "get started", "enroll",
        "join", "i'll take", "i'd like to", "count me in", "let's go",
        "start", "upgrade", "go with", "choose", "pick",
    }
    text_lower = text.lower()
    return any(kw in text_lower for kw in high_intent_keywords)


def looks_like_question(text: str) -> bool:
    """Check if text looks like a question"""
    question_indicators = ['?', 'what', 'how', 'why', 'when', 'where', 'who', 'which', 'can you', 'could you', 'do you', 'is there', 'tell me', 'explain']
    text_lower = text.lower().strip()
    return text_lower.endswith('?') or any(indicator in text_lower for indicator in question_indicators)


def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return bool(re.match(pattern, email.strip()))


def mock_lead_capture(name: str, email: str, platform: str, plan: str) -> str:
    """
    Execute lead capture after collecting all user details.
    
    STRICT GUARD: This function must NOT be called unless ALL four
    fields (name, email, platform, plan) are present and valid.
    
    Args:
        name: User's full name
        email: User's email address
        platform: User's content creation platform
        plan: User's selected plan (basic or pro)
        
    Returns:
        Success or error message
        
    Raises:
        ValueError: If any required field is missing
    """
    # ==========================================
    # STRICT GUARD — MANDATORY CHECK
    # Tool must NOT be triggered until ALL fields are collected
    # ==========================================
    if not name or not name.strip():
        raise ValueError("Tool must NOT be triggered until ALL fields are collected. Missing: name")
    if not email or not email.strip():
        raise ValueError("Tool must NOT be triggered until ALL fields are collected. Missing: email")
    if not platform or not platform.strip():
        raise ValueError("Tool must NOT be triggered until ALL fields are collected. Missing: platform")
    if not plan or not plan.strip():
        raise ValueError("Tool must NOT be triggered until ALL fields are collected. Missing: plan")

    # Validate email format
    if not validate_email(email):
        logger.warning(f"Invalid email format: {email}")
        return f"Invalid email format '{email}'. Please provide a valid email address."

    # Clean inputs
    name = name.strip()
    email = email.strip().lower()
    platform = platform.strip()
    plan = plan.strip().capitalize()

    # Execute lead capture
    logger.info("=" * 50)
    logger.info("[Tool Triggered: Lead Capture]")
    logger.info(f"Lead captured successfully: {name}, {email}, {platform}, {plan}")
    logger.info("=" * 50)

    # Simulate CRM storage (print as required by assignment)
    print(f"\n{'='*50}")
    print(f"[Tool Triggered: Lead Capture]")
    print(f"Lead captured successfully: {name}, {email}, {platform}, {plan}")
    print(f"{'='*50}\n")

    return f"Lead captured successfully for {name} ({email}) on {platform} with {plan} plan!"


def extract_plan_from_context(message: str, conversation_history: list) -> str:
    """
    Use LLM to extract the intended plan from the conversation history.
    This helps resolve "this", "that", "the 720p one", etc.
    """
    from langchain_groq import ChatGroq
    import json

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        max_tokens=100,
    )

    history_context = ""
    if conversation_history:
        recent = conversation_history[-4:]
        history_context = "\n".join(
            [f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content']}" for m in recent]
        )

    prompt = f"""Analyze the conversation and determine which subscription plan the user wants.
Available plans: "Basic" (720p, $29) or "Pro" (4K, AI captions, $79).

Context:
{history_context}

User message: "{message}"

If the user specifies a plan (e.g. "Basic", "Pro") or refers to one (e.g. "this", "the 720p one", "the first one"), extract it.
Output ONLY valid JSON: {{"plan": "Basic" | "Pro" | ""}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        plan = data.get("plan", "")
        if plan in ["Basic", "Pro"]:
            return plan
        return ""
    except Exception:
        return ""
