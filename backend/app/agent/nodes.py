from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage, AIMessage
from app.services.appointment_workflow import appointment_workflow_manager
from app.services.recommendation_workflow import recommendation_workflow_manager
from app.agent.state import AgentState
from app.services import vector_store
from app.tools import web_search
from app.services.fast_message_classifier import FastMessageClassifier
from app.models.crm_models import MessageType, ProcessingStrategy
from app.core.session_manager import get_session_file_info
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# LLM Definitions
llm_gemini = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"), temperature=0)
llm_gemini_rag = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL"),
    temperature=0.3,
    convert_system_message_to_human=True
)

# --- NODE DEFINITIONS ---

def agent_entry(state: AgentState) -> AgentState:
    """The entry point for the agent graph."""
    return state

def generate_direct(state: AgentState) -> dict:
    """
    Generates a response directly using the full conversation history.
    If the conversation is new, it provides a greeting.
    If the last message is from the AI, it passes it through to avoid errors.
    """
    messages = state["messages"]

    # 1. Handle a new, empty conversation
    if not messages:
        greeting = "Hello! I'm your Okada Leasing assistant. How can I help you today?"
        return {"messages": [AIMessage(content=greeting)]}

    # 2. Safety Check: If the last message is already from the AI, do nothing.
    #    This prevents the "must end with a user role" error.
    last_message = messages[-1]
    if isinstance(last_message, AIMessage):
        # Pass the state through without modification
        return {"messages": []} # Returning an empty list won't add new messages

    # 3. If the last message is from the user, invoke the LLM with the full history
    response = llm_gemini.invoke(messages) # <-- Pass the entire history
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

async def triage_query(state: AgentState) -> str:
    """
    Intelligently routes the user's query to the correct tool or workflow.
    This is the agent's main decision-making node.
    """
    print("--- Triage Node: Classifying Query ---")
    # Ensure 'messages' is a list and get the last message's content
    messages = state.get("messages", [])
    if not messages:
        # Handle case where there are no messages
        print("No messages in state, routing to direct generation.")
        return "generate_direct"
    user_message = messages[-1].content
    session_id = state.get("session_id")
    
    # Use the fast classifier for initial categorization
    classifier = FastMessageClassifier()
    classification = classifier.classify_message(user_message)
    
    print(f"Fast Classification: {classification.message_type.value}, Strategy: {classification.processing_strategy.value}")
    
    # Route based on the determined strategy
    if classification.processing_strategy == ProcessingStrategy.APPOINTMENT_WORKFLOW:
        print("Routing to: Appointment Workflow")
        return "handle_scheduling"
        
    if classification.processing_strategy == ProcessingStrategy.PROPERTY_WORKFLOW:
        print("Routing to: Recommendation Workflow")
        return "handle_recommendation"

    # Fallback to original logic for RAG, Web Search, or Direct Chat
    use_rag = state.get("use_rag", False)
    use_web = state.get("use_web_search", False)
    file_info = await get_session_file_info(session_id)

    if use_rag and file_info and file_info.get("file_path"):
        file_path = file_info["file_path"]
        if file_path.lower().endswith('.csv'):
            print("Routing to: CSV Tool")
            return "query_csv_tool"
        else:
            print("Routing to: RAG Retrieval")
            return "retrieve_from_rag"

    if use_web:
        print("Routing to: Web Search")
        return "run_web_search"
    
    print("Routing to: Direct Generation")
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

def classify_csv_intent(state: AgentState) -> dict:
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

    # The key in the returned dictionary must match the conditional edge.
    return {"csv_intent": "analytical" if "analytical" in intent else "semantic"}

def query_csv_tool(state: AgentState) -> dict:
    """Handles analytical queries directed at the CSV tool."""
    user_query = state["messages"][-1].content
    session_id = state.get("session_id")
    file_info = get_session_file_info(session_id)
    
    if not file_info or not file_info.get("file_path"):
        return {"messages": [AIMessage(content="No CSV file found for this session.")]}
    
    file_path = file_info.get("file_path")

    print("> Path Chosen: Analytical Query (CSV Agent)")
    print("---------------------------\n")
    from app.tools.csv_tool import get_csv_agent_executor
    response_text = get_csv_agent_executor(file_path, user_query)
    return {"messages": [AIMessage(content=response_text)]}

async def handle_scheduling(state: AgentState) -> dict:
    """Handles the appointment scheduling workflow."""
    print("--- Node: Handling Scheduling ---")
    user_message = state["messages"][-1].content
    user_id = state.get("session_id") # Using session_id as the user identifier

    # This node will now properly manage the appointment workflow.
    # It checks for an active session or starts a new one.
    from app.services.database_service import get_database
    db = get_database()
    session_collection = db["appointment_sessions"]
    active_session = await session_collection.find_one({
        "user_id": user_id,
        "status": {"$in": ["collecting_info", "confirming"]}
    })

    if active_session:
        workflow_response = await appointment_workflow_manager.process_user_response(
            session_id=active_session["_id"],
            user_response=user_message
        )
    else:
        workflow_response = await appointment_workflow_manager.start_appointment_booking(
            user_id=user_id,
            message=user_message
        )
    
    response_text = workflow_response.message
    return {"messages": [AIMessage(content=response_text)]}

async def handle_recommendation(state: AgentState) -> dict:
    """Handles the property recommendation workflow."""
    print("--- Node: Handling Recommendation ---")
    user_message = state["messages"][-1].content
    user_id = state.get("session_id")

    # This node will manage the recommendation workflow.
    workflow_session = await recommendation_workflow_manager.start_recommendation_workflow(user_id=user_id, message=user_message)
    next_step = await recommendation_workflow_manager.get_next_step(workflow_session.session_id)
    response_text = next_step.response_message if next_step else "I'm ready to find some properties for you! What are you looking for?"

    return {"messages": [AIMessage(content=response_text)]}