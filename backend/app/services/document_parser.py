
from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    CSVLoader,
    JSONLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def parse_file(file_path: str, file_type: str) -> List[Document]:
    """
    Parses a file based on its type and returns a list of Document chunks.
    Now with dedicated handlers for CSV and JSON.
    """
    file_type = file_type.lower().strip('.')
    
    # Loader-based parsing for unstructured or semi-structured text
    loader_map = {
        'pdf': PyPDFLoader,
        'docx': Docx2txtLoader,
        'doc': Docx2txtLoader,
        'txt': TextLoader,
        'md': TextLoader,
        'csv': CSVLoader,
        'json': JSONLoader,
    }

    loader_class = loader_map.get(file_type)
    if not loader_class:
        raise ValueError(f"Unsupported file type for standard loading: {file_type}")

    loader = loader_class(file_path)
    documents = loader.load()

    # Split the loaded documents into smaller chunks for non-CSV/JSON files
    if file_type not in ['csv', 'json']:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        return text_splitter.split_documents(documents)
    
    return documents
