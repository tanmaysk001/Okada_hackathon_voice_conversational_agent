from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    agent_entry,
    classify_csv_intent,
    generate_direct,
    generate_with_context,
    query_csv_tool,
    retrieve_from_rag,
    route_after_rag,
    run_web_search,
    triage_query,
)

def create_agent_graph():
    """Creates the LangGraph agent with intelligent, session-based routing."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent_entry", agent_entry)
    graph.add_node("retrieve_from_rag", retrieve_from_rag)
    graph.add_node("run_web_search", run_web_search)
    graph.add_node("generate_with_context", generate_with_context)
    graph.add_node("generate_direct", generate_direct)
    graph.add_node("query_csv_tool", query_csv_tool)
    graph.add_node("classify_csv_intent", classify_csv_intent)
    graph.add_node("route_after_rag", route_after_rag) # Add the router as a node

    # --- Define Edges ---
    graph.set_entry_point("agent_entry")

    # This is the first routing step. It checks the file type.
    graph.add_conditional_edges(
        source="agent_entry",
        path=triage_query,
        path_map={
            "classify_csv_intent": "classify_csv_intent", 
            "retrieve_from_rag": "retrieve_from_rag",   
            "run_web_search": "run_web_search",
            "generate_direct": "generate_direct",
        }
    )

    # This is the second routing step, specifically for CSVs.
    # It uses the intent to decide between the analytical tool and the semantic retriever.
    graph.add_conditional_edges(
        source="classify_csv_intent",
        path=lambda x: x['csv_intent'], 
        path_map={
            "analytical": "query_csv_tool",
            "semantic": "retrieve_from_rag",
        }
    )

    # After retrieving from RAG, route to the next step
    graph.add_edge("retrieve_from_rag", "route_after_rag")

    # Conditional routing after the RAG router node
    graph.add_conditional_edges(
        source="route_after_rag",
        path=lambda x: x.get("next_node"), # Read the next node from the state
        path_map={
            "generate_with_context": "generate_with_context",
            "run_web_search": "run_web_search",
            "generate_direct": "generate_direct",
        }
    )

    # After web search, always generate with the context found
    graph.add_edge("run_web_search", "generate_with_context")

    # End points
    graph.add_edge("generate_with_context", END)
    graph.add_edge("generate_direct", END)
    graph.add_edge("query_csv_tool", END) # This ensures the graph terminates after the CSV tool runs.

    # Compile the graph
    return graph.compile()