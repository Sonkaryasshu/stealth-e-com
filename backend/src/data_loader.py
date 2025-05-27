import pandas as pd
from typing import List, Dict, Any
import logging
from .data_models import Product, ParsedDocument

logger = logging.getLogger(__name__)

def load_products_from_csv(file_path: str) -> List[Product]:
    df = pd.read_csv(file_path)
    products: List[Product] = []
    for _, row in df.iterrows():
        product_data_dict = row.to_dict()

        if "top_ingredients" in product_data_dict:
            value = product_data_dict["top_ingredients"]
            if isinstance(value, str):
                product_data_dict["top_ingredients"] = [item.strip() for item in value.split(';') if item.strip()]
            elif pd.isna(value):
                product_data_dict["top_ingredients"] = []
        
        if "tags" in product_data_dict:
            value = product_data_dict["tags"]
            if isinstance(value, str):
                product_data_dict["tags"] = [item.strip() for item in value.split('|') if item.strip()]
            elif pd.isna(value):
                product_data_dict["tags"] = []
        
        try:
            product = Product(**product_data_dict)
            
            products.append(product)
        except Exception as e:
            logger.error(f"Skipping row due to error: {e}. Row data: {product_data_dict}", exc_info=True)
    return products

def create_product_documents_for_rag(products: List[Product]) -> List[ParsedDocument]:
    product_docs: List[ParsedDocument] = []
    for p in products:
        content_parts = [
            f"Product Name: {p.product_name}",
            f"Category: {p.category or 'N/A'}",
            f"Description: {p.description or ''}",
        ]
        if p.key_ingredients:
            content_parts.append(f"Key Ingredients: {', '.join(p.key_ingredients)}")
        if p.tags:
            content_parts.append(f"Tags: {', '.join(p.tags)}")
        
        content = "\n".join(filter(None, content_parts))

        if content.strip():
            product_docs.append(ParsedDocument(
                id=f"product_{p.product_id}",
                source_type="product_info",
                content=content,
                metadata={
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "category": p.category or 'N/A',
                    "price_usd": p.price_usd,
                }
            ))
    logger.info(f"Created {len(product_docs)} ParsedDocument objects from product data for RAG.")
    return product_docs

def load_brand_info_from_txt(file_path: str) -> List[ParsedDocument]:
    parsed_documents: List[ParsedDocument] = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.strip():
            parsed_documents.append(ParsedDocument(
                id="brand_info_main_content",
                source_type="brand_info",
                content=content.strip(),
                metadata={"source_file": file_path}
            ))
        logger.info(f"Loaded brand information from {file_path}")
    except FileNotFoundError:
        logger.warning(f"Brand info file not found at {file_path}")
    except Exception as e:
        logger.error(f"Error loading brand info from {file_path}: {e}", exc_info=True)
    return parsed_documents

def load_reviews_from_txt(file_path: str) -> List[ParsedDocument]:
    parsed_documents: List[ParsedDocument] = []
    doc_content_identifier = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            logger.warning(f"Review file is empty: {file_path}")
            return parsed_documents

        header_line = lines[0].strip()
        headers = [h.strip() for h in header_line.split('\t')]
        try:
            reviewer_idx = headers.index("Reviewer")
            product_idx = headers.index("Product")
            rating_idx = headers.index("Rating")
            review_text_idx = headers.index("Review")
        except ValueError as e:
            logger.error(f"Error parsing review headers in {file_path}: {e}. Expected 'Reviewer', 'Product', 'Rating', 'Review'. Found: {headers}")
            return parsed_documents

        for i, line in enumerate(lines[1:]):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) == len(headers):
                try:
                    reviewer = parts[reviewer_idx].strip()
                    product_name = parts[product_idx].strip()
                    rating = parts[rating_idx].strip()
                    review_text = parts[review_text_idx].strip()
                    
                    content = f"Review for {product_name} by {reviewer} (Rating: {rating}): {review_text}"
                    
                    metadata = {
                        "source_file": file_path,
                        "reviewer": reviewer,
                        "product_name": product_name,
                        "rating": rating,
                        "line_number": i + 2
                    }
                    
                    parsed_documents.append(ParsedDocument(
                        id=f"review_txt_{doc_content_identifier}",
                        source_type="review",
                        content=content,
                        metadata=metadata
                    ))
                    doc_content_identifier += 1
                except IndexError:
                    logger.warning(f"Skipping malformed review line (not enough columns) in {file_path} at line {i+2}: {line}")
            else:
                logger.warning(f"Skipping malformed review line (column count mismatch) in {file_path} at line {i+2}: {line}")
        
        logger.info(f"Loaded {len(parsed_documents)} reviews from {file_path}")

    except FileNotFoundError:
        logger.warning(f"Reviews file not found at {file_path}")
    except Exception as e:
        logger.error(f"Error loading reviews from {file_path}: {e}", exc_info=True)
    return parsed_documents

def load_tickets_from_txt(file_path: str) -> List[ParsedDocument]:
    parsed_documents: List[ParsedDocument] = []
    doc_content_identifier = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            logger.warning(f"Customer tickets file is empty: {file_path}")
            return parsed_documents

        header_line = lines[0].strip()
        headers = [h.strip() for h in header_line.split('\t')]
        try:
            ticket_id_idx = headers.index("Ticket ID")
            customer_message_idx = headers.index("Customer Message")
            support_response_idx = headers.index("Support Response")
        except ValueError as e:
            logger.error(f"Error parsing ticket headers in {file_path}: {e}. Expected 'Ticket ID', 'Customer Message', 'Support Response'. Found: {headers}")
            return parsed_documents

        for i, line in enumerate(lines[1:]):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) == len(headers):
                try:
                    ticket_id = parts[ticket_id_idx].strip()
                    customer_message = parts[customer_message_idx].strip()
                    support_response = parts[support_response_idx].strip()
                    
                    content = f"Ticket ID: {ticket_id}\nCustomer Message: {customer_message}\nSupport Response: {support_response}"
                    
                    metadata = {
                        "source_file": file_path,
                        "ticket_id": ticket_id,
                        "line_number": i + 2
                    }
                    
                    parsed_documents.append(ParsedDocument(
                        id=f"ticket_txt_{doc_content_identifier}",
                        source_type="customer_ticket",
                        content=content,
                        metadata=metadata
                    ))
                    doc_content_identifier += 1
                except IndexError:
                    logger.warning(f"Skipping malformed ticket line (not enough columns) in {file_path} at line {i+2}: {line}")
            else:
                logger.warning(f"Skipping malformed ticket line (column count mismatch) in {file_path} at line {i+2}: {line}")
        
        logger.info(f"Loaded {len(parsed_documents)} tickets from {file_path}")

    except FileNotFoundError:
        logger.warning(f"Customer tickets file not found at {file_path}")
    except Exception as e:
        logger.error(f"Error loading tickets from {file_path}: {e}", exc_info=True)
    return parsed_documents
