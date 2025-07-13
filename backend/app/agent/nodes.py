from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from app.agent.state import AgentState
from app.services import vector_store
from app.tools import web_search
from app.core.session_manager import get_session_file_info
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# LLM Definitions
llm_gemini = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"), temperature=0)
llm_gemini_rag = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL"),
    temperature=0.7,
    convert_system_message_to_human=True
)

# --- NODE DEFINITIONS ---

def agent_entry(state: AgentState) -> AgentState:
    """The entry point for the agent graph."""
    return state

def generate_direct(state: AgentState) -> dict:
    """Generates a response directly without any tools or context."""
    last_message = state["messages"][-1]
    response = llm_gemini.invoke([last_message])
    return {"messages": [response]}

def retrieve_from_rag(state: AgentState) -> dict:
    """Retrieves relevant documents from the vector store."""
    user_query = state["messages"][-1].content
    session_id = state.get("session_id")
    retriever = vector_store.get_retriever(session_id=session_id)
    retrieved_docs = retriever.invoke(user_query)
    
    if not retrieved_docs:
        return {"context": ""}
        
    # Format the context with source and row/record metadata if available
    context_parts = []
    for doc in retrieved_docs:
        source_info = doc.metadata.get('source', 'Unknown Source')
        if 'row' in doc.metadata:
            source_info += f" (Row: {doc.metadata['row']})"
        elif 'record' in doc.metadata:
            source_info += f" (Record: {doc.metadata['record']})"
        context_parts.append(f"Source: {source_info}\nContent: {doc.page_content}")
        
    context = "\n\n---\n\n".join(context_parts)
    return {"context": context}

def run_web_search(state: AgentState) -> dict:
    """Executes a web search and formats the results as context."""
    user_query = state["messages"][-1].content
    search_tool = web_search.get_web_search_tool()
    search_results = search_tool.invoke({"query": user_query})

    if isinstance(search_results, (list, tuple)):
        joined_results = "\n\n".join([str(r) for r in search_results])
    else:
        joined_results = str(search_results)

    context = f"Source: From a web search.\n\n{joined_results}"
    return {"context": context}

def generate_with_context(state: AgentState) -> dict:
    """Generates a response using the context retrieved from RAG or web search."""
    user_query = state["messages"][-1].content
    context = state.get("context", "")
    
    prompt = f'''You are a helpful assistant. Answer the user's question based *only* on the information provided in the context below.

    If the context does not contain the answer, state that you could not find the information in the provided sources.

    CONTEXT:
    ---
    {context}
    ---

    Based on the context above, please answer the following question:
    USER'S QUESTION: "{user_query}"
    '''
    new_message = HumanMessage(content=prompt)
    response = llm_gemini_rag.invoke([new_message])
    return {"messages": [response]}

def triage_query(state: AgentState) -> str:
    """Routes the query based on user flags and the presence and type of a RAG file."""
    use_rag = state.get("use_rag", False)
    use_web = state.get("use_web_search", False)
    session_id = state.get("session_id")
    file_info = get_session_file_info(session_id)

    if use_rag and file_info and file_info.get("file_path"):
        file_path = file_info["file_path"]
        # Check the file extension to decide the route
        if file_path.lower().endswith('.csv'):
            return "query_csv_tool"
        else:
            # For other file types like PDF, TXT, etc.
            return "retrieve_from_rag"

    # Fallback to web search or direct generation if RAG is not used or no file is found
    if use_web:
        return "run_web_search"
    
    return "generate_direct"

def route_after_rag(state: AgentState) -> dict:
    """Decides the next step after attempting RAG or web search."""
    context = state.get("context", "")
    next_node = ""
    if context and context.strip():
        # If we have context, use it to generate a response
        next_node = "generate_with_context"
    else:
        # If RAG returned no results, decide whether to fallback to web search
        if state.get("use_web_search"):
            next_node = "run_web_search"
        else:
            # If no context and no web search, generate a direct response
            next_node = "generate_direct"
    # The return value must be a dictionary to update the state correctly
    return {"next_node": next_node}

def classify_csv_intent(state: AgentState) -> str:
    """Classifies the user's query for a CSV file as 'semantic' or 'analytical' to decide the routing."""
    user_query = state["messages"][-1].content

    intent_classifier_prompt = f"""
    You are an expert at classifying user queries for CSV data.
    Determine if the query is 'semantic' or 'analytical'.

    - **Semantic questions** are about understanding the content, like "What is this document about?" or "Summarize the key points."
    - **Analytical questions** involve calculations, counting, or data manipulation, like "What is the average of the 'Sales' column?" or "How many properties are associated with Jack Sparrow?"

    Return *only* the word 'semantic' or 'analytical'.

    USER'S QUERY: "{user_query}"
    """
    
    print("--- Classifying CSV Intent ---")
    print(f"> User Query: {user_query}")
    intent_response = llm_gemini.invoke([HumanMessage(content=intent_classifier_prompt)])
    intent = intent_response.content.strip().lower()
    print(f"> Classified Intent: {intent}")
    print("-----------------------------")

    if "analytical" in intent:
        return "analytical"
    else:
        return "semantic"

def query_csv_tool(state: AgentState) -> dict:
    """Handles analytical queries directed at the CSV tool."""
    user_query = state["messages"][-1].content
    session_id = state.get("session_id")
    file_info = get_session_file_info(session_id)
    
    if not file_info or not file_info.get("file_path"):
        return {"messages": [HumanMessage(content="No CSV file found for this session.")]}
    
    file_path = file_info.get("file_path")

    print("> Path Chosen: Analytical Query (CSV Agent)")
    print("---------------------------\n")
    from app.tools.csv_tool import get_csv_agent_executor
    response_text = get_csv_agent_executor(file_path, user_query)
    return {"messages": [HumanMessage(content=response_text)]}