from typing import List, Any, Dict
import logging
from pathlib import Path
from .data_models import DocumentChunk, ParsedDocument
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

TEXT_CHUNK_SIZE = 512
TEXT_CHUNK_OVERLAP = 50
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
CHROMA_COLLECTION_NAME = "skincare_documents"
CHROMA_PERSIST_DIRECTORY = str(_BACKEND_ROOT / "chroma_db_store")

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

def chunk_parsed_documents(parsed_docs: List[ParsedDocument]) -> List[DocumentChunk]:
    all_chunks: List[DocumentChunk] = []
    for p_doc in parsed_docs:
        text = p_doc.content
        start = 0
        doc_id = p_doc.id
        while start < len(text):
            end = start + TEXT_CHUNK_SIZE
            chunk_text = text[start:end]
            
            all_chunks.append(DocumentChunk(
                document_id=doc_id,
                text_chunk=chunk_text,
                source_type=p_doc.source_type,
                metadata={
                    **p_doc.metadata,
                    "original_doc_id": doc_id,
                    "source_type": p_doc.source_type
                }
            ))
            start += TEXT_CHUNK_SIZE - TEXT_CHUNK_OVERLAP
            if start >= len(text):
                break
    logger.info(f"Created {len(all_chunks)} chunks from {len(parsed_docs)} parsed documents.")
    return all_chunks

def initialize_vector_store_collection():
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)
    
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME
    )
    logger.info(f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' initialized/retrieved from '{CHROMA_PERSIST_DIRECTORY}'.")
    return collection

def add_chunks_to_vector_store(collection: chromadb.api.models.Collection.Collection, chunks: List[DocumentChunk]):
    if not chunks:
        logger.info("No chunks to add to the vector store.")
        return

    chunk_texts = [chunk.text_chunk for chunk in chunks]
    
    logger.info(f"Generating embeddings for {len(chunk_texts)} chunks using '{EMBEDDING_MODEL_NAME}'...")
    embeddings = embedding_model.encode(chunk_texts, show_progress_bar=True).tolist()
    logger.info("Embeddings generated.")

    ids = [chunk.chunk_id for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]
    documents_to_store = chunk_texts

    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents_to_store
        )
        logger.info(f"Successfully added {len(ids)} chunks to ChromaDB collection '{collection.name}'.")
    except Exception as e:
        logger.error(f"Error adding chunks to ChromaDB: {e}", exc_info=True)

def query_vector_store(collection: chromadb.api.models.Collection.Collection, query_text: str, n_results: int = 10) -> List[Dict[str, Any]]:
    query_embedding = embedding_model.encode(query_text).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['documents', 'metadatas', 'distances']
    )
    
    formatted_results = []
    if results and results['ids'] and results['ids'][0]:
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "text_chunk": results['documents'][0][i] if results['documents'] else None,
                "metadata": results['metadatas'][0][i] if results['metadatas'] else None,
                "distance": results['distances'][0][i] if results['distances'] else None,
            })
    return formatted_results
