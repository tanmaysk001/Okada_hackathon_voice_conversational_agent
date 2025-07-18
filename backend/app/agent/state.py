from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """The state of the agent.

    Attributes:
        messages: The list of messages in the conversation. The `Annotated` type hint
                  with `operator.add` tells LangGraph how to update this field.
        context: The retrieved context for the RAG agent.
        use_rag: A boolean flag to indicate if RAG should be used.
        use_web_search: A boolean flag to indicate if web search should be used.
        processing_strategy: The strategy used for processing the intent.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    context: Optional[str]
    use_rag: bool
    use_web_search: bool
    csv_intent: Optional[str]
    next_node: Optional[str]
    processing_strategy: Optional[str]
