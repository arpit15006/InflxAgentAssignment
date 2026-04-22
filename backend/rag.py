"""
Inflx RAG Module — FAISS-Based Knowledge Retrieval
Uses sentence-transformers for embeddings + FAISS for vector similarity search.
Retrieves relevant documents and generates grounded responses via LLM.
"""

import json
import logging
import os
from pathlib import Path

from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("inflx.rag")

# Global FAISS store (initialized once at startup)
_vector_store = None
_embeddings = None


def _get_knowledge_base_path() -> str:
    """Get the path to the knowledge base JSON file."""
    return str(Path(__file__).parent / "knowledge_base.json")


def initialize_rag():
    """
    Initialize the FAISS vector store with knowledge base documents.
    Called once at application startup.
    
    Pipeline:
    1. Load knowledge_base.json → parse into document chunks
    2. Embed with sentence-transformers/all-MiniLM-L6-v2 (local model)
    3. Index into FAISS vector store for similarity search
    """
    global _vector_store, _embeddings

    logger.info("Initializing FAISS RAG pipeline...")

    # Load knowledge base
    kb_path = _get_knowledge_base_path()
    with open(kb_path, "r") as f:
        kb_data = json.load(f)

    # Convert to LangChain documents
    documents = []
    for doc in kb_data["documents"]:
        documents.append(
            Document(
                page_content=doc["content"],
                metadata={
                    "id": doc["id"],
                    "category": doc["category"],
                    "title": doc["title"],
                },
            )
        )

    logger.info(f"Loaded {len(documents)} documents from knowledge base")

    # Initialize embeddings (local model — no API key needed)
    _embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    # Build FAISS index
    _vector_store = FAISS.from_documents(documents, _embeddings)
    logger.info("FAISS vector store initialized successfully")


def retrieve_and_respond(query: str, conversation_history: list = None) -> str:
    """
    RAG pipeline: Retrieve relevant docs via FAISS → Generate grounded response.
    
    Args:
        query: User's question
        conversation_history: Previous messages for context
        
    Returns:
        LLM-generated response grounded in retrieved knowledge
    """
    global _vector_store

    if _vector_store is None:
        initialize_rag()

    # Step 1: Similarity search — retrieve top 3 relevant documents
    retrieved_docs = _vector_store.similarity_search(query, k=3)
    
    logger.info(f"Retrieved {len(retrieved_docs)} documents for query: '{query[:50]}...'")
    for doc in retrieved_docs:
        logger.debug(f"  → {doc.metadata.get('title', 'Unknown')}")

    # Step 2: Build context from retrieved documents
    context = "\n\n".join(
        [f"[{doc.metadata.get('title', '')}]: {doc.page_content}" for doc in retrieved_docs]
    )

    # Step 3: Generate response grounded in context
    history_context = ""
    if conversation_history and len(conversation_history) > 0:
        recent = conversation_history[-4:]
        history_context = "\n".join(
            [f"{'User' if m['role'] == 'user' else 'Agent'}: {m['content']}" for m in recent]
        )

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.3,
        max_tokens=300,
    )

    prompt = f"""You are Inflx AI, a helpful assistant for a content creator SaaS platform.
Answer the user's question using ONLY the information provided in the context below.
Do NOT make up information. If the answer is not in the context, say you don't have that information.
Be concise, friendly, and professional.

Context:
{context}

Recent conversation:
{history_context}

User question: {query}

Respond naturally and helpfully:"""

    response = llm.invoke(prompt)
    return response.content.strip()
