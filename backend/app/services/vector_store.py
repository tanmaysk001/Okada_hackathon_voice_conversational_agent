# # apps/backend/app/services/vector_store.py
# from langchain_community.vectorstores import FAISS
# from langchain_openai import OpenAIEmbeddings
# from langchain_core.documents import Document
# from typing import List

# # In a production app, use a persistent vector store like ChromaDB or a managed service.
# # For this example, we use an in-memory FAISS store. It will reset on server restart.
# embeddings = OpenAIEmbeddings()

# # A simple in-memory store. You'll need a more robust, persistent solution for production.
# # We initialize it with a dummy document to create the index.
# _vector_store = FAISS.from_texts(
#     ["This is the initial content."], 
#     embedding=embeddings
# )

# def get_retriever(search_kwargs={"k": 3}):
#     """Returns a retriever for the global vector store."""
#     return _vector_store.as_retriever(search_kwargs=search_kwargs)

# def add_documents_to_store(documents: List[Document]):
#     """Adds a list of LangChain documents to the vector store."""
#     global _vector_store
#     if documents:
#         _vector_store.add_documents(documents)



# apps/backend/app/services/vector_store.py
import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from typing import List
from app.core.config import settings
from google import genai
import os 
from dotenv import load_dotenv

load_dotenv()


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Configuration ---
# Configure the Google API key for the embedding model
client = genai.Client(api_key=GOOGLE_API_KEY)

# Define the path for the persistent ChromaDB database and the collection name
CHROMA_PERSIST_DIRECTORY = "chroma_db"
CHROMA_COLLECTION_NAME = "multimodal_rag_vector_store"

# --- Initialization ---
# Initialize the Google Generative AI embedding model
# We use LangChain's wrapper for seamless integration.
embedding_function = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", 
    task_type="retrieval_document"
)

# Initialize a persistent ChromaDB client
persistent_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)

# Initialize the Chroma vector store with the client, collection name, and embedding function
vector_store = Chroma(
    client=persistent_client,
    collection_name=CHROMA_COLLECTION_NAME,
    embedding_function=embedding_function,
)

# --- Service Functions ---
def add_documents_to_store(documents: List[Document],session_id: str):
    """
    Adds a list of LangChain documents to the persistent Chroma vector store.
    The documents will be embedded using the GoogleGenerativeAIEmbeddings function.
    """
    if not documents:
        return
    
    # --- CORE CHANGE: Add metadata to each document chunk ---
    for doc in documents:
        doc.metadata = {"session_id": session_id, **doc.metadata}
    # --------------------------------------------------------

    print(f"Adding {len(documents)} document chunks with session_id '{session_id}' to ChromaDB.")
    vector_store.add_documents(documents)
    print("Successfully added documents to the store.")


def get_retriever(session_id: str, search_kwargs={"k": 10}):
    """
    Returns a retriever for the Chroma vector store that is filtered
    to only search documents matching the given session_id.
    """
    print(f"Creating retriever for session_id: {session_id}")
    # --- CORE CHANGE: Use the 'filter' argument in as_retriever ---
    return vector_store.as_retriever(
        search_kwargs={
            "k": search_kwargs.get("k", 10),
            "filter": {"session_id": session_id}
        }
    )

def delete_documents_by_session_id(session_id: str):
    """
    Deletes all documents from the ChromaDB collection that match the given session_id.
    This is a direct-to-DB operation for efficiency.
    """
    if not session_id:
        print("Warning: No session_id provided for document deletion.")
        return

    try:
        # Access the underlying collection from the Chroma client
        collection = persistent_client.get_collection(name=CHROMA_COLLECTION_NAME)
        
        # Use the 'where' filter to target documents by session_id
        collection.delete(where={"session_id": session_id})
        
        print(f"Successfully deleted all RAG documents for session_id: {session_id}")

    except Exception as e:
        print(f"Error deleting documents for session_id {session_id}: {e}")
        # Depending on requirements, you might want to re-raise the exception
        # or handle it gracefully.
        raise

async def query_vector_store(session_id: str, query_text: str, n_results: int = 2) -> str:
    """Query the vector store for a given session and query text asynchronously."""
    async_client = chromadb.AsyncClient(path=CHROMA_PERSIST_DIRECTORY)
    collection = await async_client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding_function
    )
    
    results = await collection.query(
        query_texts=[query_text],
        n_results=n_results,
        filter={"session_id": session_id}
    )
    
    documents = results.get('documents')
    if documents and documents[0]:
        return "\n".join(documents[0])
    return ""