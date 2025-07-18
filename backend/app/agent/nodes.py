# Add this near the top of backend/app/agent/nodes.py with other definitions

OKADA_SYSTEM_PROMPT = """You are a specialized, professional, and friendly **commercial real estate** assistant for Okada.

Your primary purpose is to assist users with inquiries related to Okada's business, which includes:
- Answering questions about **commercial property listings** using provided documents (RAG).
- Providing **commercial property** recommendations from Okada's internal database.
- Booking property viewing appointments.
- Scheduling maintenance appointments for existing tenants.
- Searching the web for information specifically about New York City when relevant to a user's query.

Rules:
- If a user greets you, respond with: "Hello! I'm your Okada Leasing assistant for commercial properties. How can I help you today?"
- If the user asks about your capabilities, briefly list your main functions.
- If the user asks a question NOT related to commercial real estate, Okada's business, or New York City, you must politely decline.
"""

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
    Generates a response directly, anchored by the Okada system prompt.
    """
    print("--- Node: Direct Generation ---")
    messages = state["messages"]

    # If the last message is from the AI, pass through to avoid errors.
    if messages and isinstance(messages[-1], AIMessage):
        return {"messages": []}

    # Prepend the system prompt to the user's query
    # We combine the system prompt with the latest user message for a focused generation
    user_query = messages[-1].content
    prompt_messages = [
        HumanMessage(content=f"{OKADA_SYSTEM_PROMPT}\n\nUSER QUESTION: {user_query}")
    ]

    # Invoke the LLM with the specific prompt
    response = llm_gemini.invoke(prompt_messages)
    return {"messages": [response]}

def retrieve_from_rag(state: AgentState, config: dict) -> dict:
    """Retrieves relevant documents from the vector store."""
    user_query = state["messages"][-1].content
    session_id = state.get("session_id")

    # --- ROBUSTNESS FIX ---
    # If session_id is missing from the state, extract it from the config's thread_id.
    # This is a fallback for when the initial state isn't populated correctly.
    if not session_id:
        print("Warning: session_id missing from state. Attempting fallback from config.")
        configurable = config.get("configurable", {})
        session_id = configurable.get("thread_id") # thread_id is the session_id
        if session_id:
            print(f"Success: Found session_id in config: {session_id}")
            state["session_id"] = session_id # Persist it in the state for subsequent nodes
        else:
            print("Error: Could not find session_id in state or config. RAG will fail.")

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
    """Executes a web search scoped to New York City and formats the results."""
    print("--- Node: Web Search ---")
    user_query = state["messages"][-1].content
    
    # ** THE FIX IS HERE **
    # Append "in New York City" to the query to constrain the search.
    scoped_query = f"{user_query} in New York City"
    print(f"Original query: '{user_query}', Scoped query: '{scoped_query}'")

    search_tool = web_search.get_web_search_tool()
    search_results = search_tool.invoke({"query": scoped_query}) # Use the scoped query

    if isinstance(search_results, (list, tuple)):
        joined_results = "\n\n".join([str(r) for r in search_results])
    else:
        joined_results = str(search_results)

    context = f"Source: From a web search.\n\n{joined_results}"
    return {"context": context}

# =================================================================
# REPLACEMENT #1: The Triage Function
# =================================================================
async def triage_query(state: AgentState) -> str:
    """
    Intelligently routes the user's query. This is the simple, robust fix.
    """
    print("--- Triage Node (Robust Fix) ---")
    use_rag = state.get("use_rag", False)
    use_web = state.get("use_web_search", False)

    # --- THE CORE FIX IS HERE ---
    # If the user has RAG mode enabled, we ALWAYS go to the retrieval step first.
    # The decision of what to do if no documents are found is handled later.
    if use_rag:
        print("Routing Decision: RAG is enabled, attempting document retrieval.")
        return "retrieve_from_rag"

    # --- Fallback logic if RAG is turned off by the user ---
    if use_web:
        print("Routing Decision: RAG is off, using web search.")
        return "run_web_search"
    
    print("Routing Decision: RAG and Web Search are off, using direct generation.")
    return "generate_direct"


# =================================================================
# REPLACEMENT #2: The Post-RAG Routing Function
# =================================================================
def route_after_rag(state: AgentState) -> dict:
    """
    Decides the next step after attempting RAG retrieval. This is the crucial fallback logic.
    """
    print("--- Post-RAG Router (Robust Fix) ---")
    context = state.get("context", "")
    use_web_search = state.get("use_web_search", False)

    # --- THE SECOND CORE FIX IS HERE ---
    if context and context.strip():
        # If we have context, we MUST use it to generate a response.
        print("Decision: Context FOUND. Routing to generate_with_context.")
        return {"next_node": "generate_with_context"}
    else:
        # If RAG returned no results, tell the user and then decide what to do.
        print("Decision: Context NOT found.")
        
        # Create a message to inform the user what's happening.
        no_context_message = AIMessage(
            content="I could not find any relevant information in your uploaded documents for that query. I will answer from my general knowledge."
        )
        # Add the message to the state history.
        state["messages"].append(no_context_message)
        
        # Now, decide the fallback path.
        if use_web_search:
            print("Fallback: Web Search.")
            return {"next_node": "run_web_search"}
        else:
            print("Fallback: Direct Generation.")
            return {"next_node": "generate_direct"}


# =================================================================
# REPLACEMENT #3: The Strict Context Generation Function
# =================================================================
def generate_with_context(state: AgentState) -> dict:
    """
    Generates a response using the context. The prompt is now extremely strict
    to prevent the model from using outside knowledge.
    """
    print("--- Generating with Context (Robust Fix) ---")
    user_query = state["messages"][-1].content
    context = state.get("context", "")
    
    # --- THE THIRD CORE FIX: THE STRICT PROMPT ---
    prompt = f'''You are a helpful assistant. Your task is to answer the user's question based ONLY on the information provided in the "CONTEXT" section below.

You are forbidden from using any external knowledge. You must not answer if the information is not present in the context.

CONTEXT:
---
{context}
---

If the context does not contain the answer to the user's question, you MUST respond with EXACTLY this phrase: "I could not find the answer in the provided documents."

Based *only* on the context above, answer this question:
USER'S QUESTION: "{user_query}"
'''
    new_message = HumanMessage(content=prompt)
    response = llm_gemini_rag.invoke([new_message])
    return {"messages": [response]}

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
    """Handles both viewing and maintenance appointments by starting the workflow with the correct context."""
    print("--- Node: Handling Scheduling ---")
    user_message = state["messages"][-1].content
    user_id = state.get("session_id")
    strategy = state.get("processing_strategy")

    # Determine the title based on the routing strategy
    if strategy == ProcessingStrategy.MAINTENANCE_WORKFLOW.value:
        initial_title = f"Maintenance Request"
        # Try to get more specific from the user's message
        match = re.search(r'(fix|repair|broken|leaking|issue with)\s+(?:my\s+)?(.*)', user_message, re.IGNORECASE)
        if match and match.group(2):
            initial_title += f": {match.group(2).strip()}"
    else:
        initial_title = "Property Viewing"
    
    print(f"Starting appointment workflow with initial title: '{initial_title}'")

    # Use the existing appointment workflow manager, but pass the dynamic title
    workflow_response = await appointment_workflow_manager.start_appointment_booking(
        user_id=user_id,
        message=user_message,
        initial_title=initial_title  # Pass the context-aware title
    )
    
    response_text = workflow_response.message
    return {"messages": [AIMessage(content=response_text)]}




from app.services import property_service # Make sure this import is at the top of the file

async def handle_recommendation(state: AgentState) -> dict:
    """
    This is the new, intelligent recommendation node. It has access to the full
    conversation history and follows a strict, proactive script.
    """
    print("--- Node: Handling Recommendation (Demo-Proof Fix) ---")
    
    # 1. Get the full conversation history to understand all context
    full_history = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
    latest_user_query = state["messages"][-1].content

    try:
        # 2. Use our resilient service to get property data from MongoDB
        context_str = await property_service.get_properties_as_text(latest_user_query)

        if "No properties were found" in context_str:
            return {"messages": [AIMessage(content="I'm sorry, but I couldn't find any properties in our database right now. Please check back later.")]}

        # 3. --- THE DEMO-WINNING PROMPT ---
        prompt = f"""You are a professional and proactive commercial real estate assistant for Okada. Your ONLY task is to help the user find a property from the internal database and book a viewing.

        **Full Conversation History (for context):**
        ---
        {full_history}
        ---

        **Available Property Information from Okada's Database:**
        ---
        {context_str}
        ---

        **Your Instructions (Follow Exactly):**
        1.  Analyze the user's request using the FULL conversation history to understand all requirements (location, budget, etc.).
        2.  If the database results do not perfectly match, acknowledge it briefly (e.g., "While I couldn't find an exact match for your budget, I did find a great option nearby...").
        3.  Select the SINGLE BEST property from the list to recommend.
        4.  Present the details of this single best property in a friendly, concise summary.
        5.  Your response MUST mention the assigned associate by name from the data (e.g., "The associate for this property is Jack Sparrow.").
        6.  Your response MUST end with a proactive question to book a viewing with that specific associate. For example: "I can set up an appointment with the property associate, Jack Sparrow, for you. Would you like me to proceed?"
        
        **DO NOT** ask for information you already have from the history.
        **DO NOT** say you cannot access the database. Your goal is to recommend one property and book a viewing.
        """

        # 4. Call the LLM
        response = llm_gemini.invoke([HumanMessage(content=prompt)])
        return {"messages": [response]}

    except Exception as e:
        logger.error(f"Error in handle_recommendation: {e}")
        return {"messages": [AIMessage(content="I'm sorry, I encountered an error while looking for recommendations. Please try again.")]}