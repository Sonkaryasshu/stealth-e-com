import logging
from pathlib import Path
from typing import List
from src.data_models import ParsedDocument
from src.data_loader import (
    load_products_from_csv,
    load_brand_info_from_txt,
    load_reviews_from_txt,
    load_tickets_from_txt,
    create_product_documents_for_rag
)
from src.rag_pipeline import (
    chunk_parsed_documents,
    initialize_vector_store_collection,
    add_chunks_to_vector_store
)

_BACKEND_ROOT = Path(__file__).resolve().parent

DATA_DIR = _BACKEND_ROOT / "data"
PRODUCT_CATALOG_FILE = DATA_DIR / "skincare_catalog.csv"
BRAND_INFO_TXT_FILE = DATA_DIR / "brand_info.txt"
VERIFIED_REVIEWS_TXT_FILE = DATA_DIR / "verified_reviews.txt"
CUSTOMER_TICKETS_TXT_FILE = DATA_DIR / "customer_tickets.txt"

logger = logging.getLogger(__name__)

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting data ingestion process...")
    all_parsed_docs: List[ParsedDocument] = []

    logger.info(f"Attempting to load product catalog from: {PRODUCT_CATALOG_FILE.resolve()}")
    if not PRODUCT_CATALOG_FILE.exists():
        logger.warning(f"Product catalog file not found: {PRODUCT_CATALOG_FILE}")
    else:
        products = load_products_from_csv(str(PRODUCT_CATALOG_FILE))
        logger.info(f"Loaded {len(products)} products from CSV.")
        
        if products:
            product_rag_docs = create_product_documents_for_rag(products)
            all_parsed_docs.extend(product_rag_docs)
            logger.info(f"Added {len(product_rag_docs)} product documents to RAG ingestion list.")
        else:
            logger.warning("No products loaded from CSV, so no product documents will be added to RAG.")

    if not BRAND_INFO_TXT_FILE.exists():
        logger.warning(f"Brand info text file not found: {BRAND_INFO_TXT_FILE}")
    else:
        brand_info_docs = load_brand_info_from_txt(str(BRAND_INFO_TXT_FILE))
        all_parsed_docs.extend(brand_info_docs)
        logger.info(f"Loaded {len(brand_info_docs)} document(s) from brand info text file.")

    if not VERIFIED_REVIEWS_TXT_FILE.exists():
        logger.warning(f"Verified reviews text file not found: {VERIFIED_REVIEWS_TXT_FILE}")
    else:
        review_docs = load_reviews_from_txt(str(VERIFIED_REVIEWS_TXT_FILE))
        all_parsed_docs.extend(review_docs)
        logger.info(f"Loaded {len(review_docs)} review document(s) from text file.")

    if not CUSTOMER_TICKETS_TXT_FILE.exists():
        logger.warning(f"Customer tickets text file not found: {CUSTOMER_TICKETS_TXT_FILE}")
    else:
        ticket_docs = load_tickets_from_txt(str(CUSTOMER_TICKETS_TXT_FILE))
        all_parsed_docs.extend(ticket_docs)
        logger.info(f"Loaded {len(ticket_docs)} ticket document(s) from text file.")

    if not all_parsed_docs:
        logger.error("No documents found from any source. Aborting RAG ingestion.")
        return
    
    logger.info(f"Total parsed documents from all sources: {len(all_parsed_docs)}")

    doc_chunks = chunk_parsed_documents(all_parsed_docs)
    if not doc_chunks:
        logger.error("No chunks created from parsed documents. Aborting RAG ingestion.")
        return

    vector_store_collection = initialize_vector_store_collection()

    logger.info(f"Clearing existing documents from collection '{vector_store_collection.name}' before new ingestion...")
    existing_ids = vector_store_collection.get(include=[])['ids']
    if existing_ids:
        vector_store_collection.delete(ids=existing_ids)
        logger.info(f"Cleared {len(existing_ids)} existing documents from collection.")
    else:
        logger.info("Collection was already empty or no IDs found to clear.")
    
    add_chunks_to_vector_store(vector_store_collection, doc_chunks)

    logger.info("Data ingestion process completed.")


if __name__ == "__main__":
    main()
