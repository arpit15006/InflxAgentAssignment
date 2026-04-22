"""
Inflx Agent State Schema
Defines the conversation state maintained across turns.
Session-based memory retains context for 5-6 turns using LangGraph state.
"""

from typing import TypedDict, Literal


class AgentState(TypedDict):
    """
    Core state object maintained throughout the conversation.
    
    Attributes:
        messages: Conversation history (capped at 6 turns for memory retention)
        intent: Detected intent - strictly one of: greeting | pricing | high_intent
        stage: Current lead capture stage in the workflow
        name: User's name (captured during lead flow)
        email: User's email (captured during lead flow)
        platform: User's content platform (captured during lead flow)
        plan: User's selected plan - basic or pro (captured during lead flow)
        response: Generated agent response for the current turn
        session_id: Unique session identifier for multi-turn tracking
    """
    messages: list
    intent: Literal["greeting", "pricing", "high_intent", "unknown", ""]
    confidence: float
    stage: Literal["idle", "ask_name", "ask_email", "ask_platform", "ask_plan", "complete", ""]
    name: str
    email: str
    platform: str
    plan: str
    response: str
    session_id: str


def create_initial_state(session_id: str) -> AgentState:
    """Create a fresh state for a new conversation session."""
    return AgentState(
        messages=[],
        intent="",
        confidence=0.0,
        stage="idle",
        name="",
        email="",
        platform="",
        plan="",
        response="",
        session_id=session_id,
    )


# Maximum number of message pairs to retain (5-6 turns)
MAX_MEMORY_TURNS = 6
