from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """Defines the state of the agent, including all relevant data for processing.

    Attributes:
        messages: A list of LangChain BaseMessages representing the conversation history.
        session_id: A unique identifier for the user's session.
        use_rag: A boolean flag to enable or disable Retrieval-Augmented Generation (RAG).
        use_web_search: A boolean flag to enable or disable web searches.
        context: A string to store context from RAG, web search, or other tools.
        csv_intent: The classified intent of a user's query related to a CSV file, 
                    which can be 'analytical' or 'semantic'.
        next_node: The next node to be executed in the graph, used for conditional routing.
    """
    messages: List[BaseMessage]
    session_id: str
    use_rag: bool
    use_web_search: bool
    context: str
    csv_intent: Optional[str]
    next_node: Optional[str]
