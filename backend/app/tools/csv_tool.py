from llama_index.experimental.query_engine import PandasQueryEngine
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import pandas as pd
from llama_index.llms.langchain import LangChainLLM


def get_csv_agent_executor(file_path: str, user_query: str):
    """
    Creates and runs a CSV agent to answer a query about a CSV file.

    Args:
        file_path: The absolute path to the CSV file.
        user_query: The user's question about the CSV data.

    Returns:
        The agent's answer as a string.
    """
    print(f"--- TOOL: Running CSV Agent on {file_path} for query: '{user_query}' ---")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        return "Error: The specified CSV file was not found."

    # Create the LLM for the agent
    llm = LangChainLLM(llm=ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"), temperature=0))

    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Create the PandasQueryEngine
    query_engine = PandasQueryEngine(df=df, llm=llm, verbose=True)

    try:
        # Run the query
        raw_response = query_engine.query(user_query)

        # Rephrase the raw response to be more conversational
        rephrase_prompt = f"""
        Based on the following user query and the raw data result from a query engine, 
        formulate a polite, natural-sounding, single-sentence answer.

        **User Query:**
        {user_query}

        **Raw Data Result:**
        {raw_response}

        **Your Answer (must be a single, polite sentence):**
        """

        final_response = llm.invoke(rephrase_prompt)

        # The response from the LLM is an AIMessage object, so we access its content.
        return final_response.content
    except Exception as e:
        print(f"--- ERROR in CSV Agent: {e} ---")
        return "Sorry, an error occurred while querying the CSV file."