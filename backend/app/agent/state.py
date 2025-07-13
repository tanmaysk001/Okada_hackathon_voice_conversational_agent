from typing import TypedDict

from typing import TypedDict

class AgentState(TypedDict):
    """The state of the agent.

    Attributes:
        messages: The list of messages in the conversation.
        session_id: The unique identifier for the session.
        use_rag: A flag to determine whether to use RAG.
        use_web_search: A flag to determine whether to use web search.
        context: A string to hold context from RAG or web search.
    """
    messages: list
    session_id: str
    use_rag: bool
    use_web_search: bool
    context: str
