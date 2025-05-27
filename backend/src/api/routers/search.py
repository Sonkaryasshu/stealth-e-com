import uuid
import logging
import chromadb
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional

from src.rag_pipeline import initialize_vector_store_collection, query_vector_store
from src.data_models import (
    Product as FullProductModel,
    SearchQuery,
    ProductResult,
    SearchResponse
)
from src.llm_handler import get_conversational_response
from .products import get_products_from_file

router = APIRouter()
logger = logging.getLogger(__name__)

_user_conversations: Dict[str, List[Dict[str, Any]]] = {}


async def get_current_vector_store_collection() -> chromadb.api.models.Collection.Collection:
    try:
        collection = initialize_vector_store_collection()
        if collection is None:
            logger.error("Failed to initialize vector store collection for request (returned None).")
            raise HTTPException(status_code=503, detail="Vector store is not available.")
        return collection
    except Exception as e:
        logger.error(f"Error initializing vector store collection for request: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Vector store is not available due to an initialization error.")


@router.post("/", response_model=SearchResponse)
async def conversational_search(
    search_query: SearchQuery,
    vector_store_collection: chromadb.api.models.Collection.Collection = Depends(get_current_vector_store_collection)
):
    logger.info(f"Received search query: '{search_query.query}' from session: {search_query.session_id}")

    try:
        rag_results = query_vector_store(
            collection=vector_store_collection,
            query_text=search_query.query,
            n_results=10
        )
        
        product_catalog_list: List[FullProductModel]
        product_catalog_dict: Dict[str, FullProductModel]
        try:
            product_catalog_list = get_products_from_file()
            product_catalog_dict = {p.product_id: p for p in product_catalog_list}
        except HTTPException as e:
            logger.warning(f"Could not load product catalog for LLM/enrichment: {e.detail}")
            product_catalog_list = []
            product_catalog_dict = {}
        
        history_for_llm = []
        if search_query.session_id and search_query.session_id in _user_conversations:
            history_for_llm = _user_conversations[search_query.session_id]

        llm_response = await get_conversational_response(
            query=search_query.query,
            rag_contexts_raw_dicts=rag_results,
            session_id=search_query.session_id,
            conversation_history=history_for_llm
        )

        if llm_response.results:
            valid_results: List[ProductResult] = []
            for p_res_from_llm in llm_response.results:
                if p_res_from_llm.product and p_res_from_llm.product.product_id in product_catalog_dict:
                    authoritative_product = product_catalog_dict[p_res_from_llm.product.product_id]
                    valid_results.append(
                        ProductResult(
                            product=authoritative_product,
                            justification=p_res_from_llm.justification,
                            supporting_reviews=p_res_from_llm.supporting_reviews
                        )
                    )
                else:
                    product_id_for_warning = p_res_from_llm.product.product_id if p_res_from_llm.product else "N/A"
                    logger.warning(f"LLM recommended product_id '{product_id_for_warning}' not found in catalog or product data incomplete. Filtering out.")
            llm_response.results = valid_results
        
        if llm_response.results:
            
            products_with_margin_percentage = [p_res for p_res in llm_response.results if p_res.product and p_res.product.margin_percentage is not None]
            products_without_margin_percentage = [p_res for p_res in llm_response.results if not p_res.product or p_res.product.margin_percentage is None]
            
            if products_with_margin_percentage:
                products_with_margin_percentage.sort(key=lambda p_res: p_res.product.margin_percentage, reverse=True)
                
                llm_response.results = products_with_margin_percentage + products_without_margin_percentage
                
        
        all_relevant_contexts_from_llm = list(llm_response.rag_contexts) if llm_response.rag_contexts else []
        final_top_level_contexts = []
        moved_review_chunk_ids = set()

        if llm_response.results and len(llm_response.results) > 0:
            for product_res in llm_response.results:
                product_id_to_match = product_res.product.product_id
                product_name_to_match = product_res.product.product_name.lower() if product_res.product and hasattr(product_res.product, 'product_name') and product_res.product.product_name else ""

                existing_review_ids_for_this_product = {rev.chunk_id for rev in product_res.supporting_reviews}

                for context_chunk in all_relevant_contexts_from_llm:
                    if context_chunk.chunk_id in moved_review_chunk_ids:
                        continue
                    if context_chunk.chunk_id in existing_review_ids_for_this_product:
                        continue

                    if context_chunk.source_type == "review":
                        matches_product = False
                        metadata_product_id = context_chunk.metadata.get("product_id")
                        metadata_product_name_raw = context_chunk.metadata.get("product_name", "")
                        metadata_product_name = metadata_product_name_raw.lower() if isinstance(metadata_product_name_raw, str) else ""
                        
                        if metadata_product_id and metadata_product_id == product_id_to_match:
                            matches_product = True
                        elif not metadata_product_id and metadata_product_name and metadata_product_name == product_name_to_match:
                            matches_product = True
                        
                        if matches_product:
                            rating_str = context_chunk.metadata.get("rating", "").strip()
                            star_count = rating_str.count('★')
                            if star_count >= 3:
                                product_res.supporting_reviews.append(context_chunk)
                                moved_review_chunk_ids.add(context_chunk.chunk_id)
                                existing_review_ids_for_this_product.add(context_chunk.chunk_id) 
            
            for context_chunk in all_relevant_contexts_from_llm:
                if context_chunk.chunk_id not in moved_review_chunk_ids:
                    final_top_level_contexts.append(context_chunk)
            llm_response.rag_contexts = final_top_level_contexts
            logger.info(f"Processed RAG contexts: {len(moved_review_chunk_ids)} positive reviews associated with products. "
                        f"Top-level RAG contexts now count {len(llm_response.rag_contexts)}.")
        else:
            for context_chunk in all_relevant_contexts_from_llm:
                if context_chunk.chunk_id not in moved_review_chunk_ids:
                    final_top_level_contexts.append(context_chunk)
            llm_response.rag_contexts = final_top_level_contexts
            logger.info(f"No products recommended. All {len(llm_response.rag_contexts)} LLM-cited RAG contexts are set as top-level.")

        current_session_id_for_history = llm_response.session_id

        if current_session_id_for_history not in _user_conversations:
            _user_conversations[current_session_id_for_history] = []
        
        _user_conversations[current_session_id_for_history].append({"role": "user", "parts": [search_query.query]})
        
        response_parts = []
        if llm_response.answer:
            response_parts.append(llm_response.answer)
        if llm_response.contextual_justification:
             response_parts.append(llm_response.contextual_justification)
        if llm_response.follow_up_questions and len(llm_response.follow_up_questions) > 0:
            response_parts.append("Follow-up questions: " + "; ".join(llm_response.follow_up_questions))
        
        if not response_parts:
            response_parts.append("Okay.")

        response_summary_for_history = " ".join(response_parts)
        
        _user_conversations[current_session_id_for_history].append({"role": "model", "parts": [response_summary_for_history.strip()]})

        MAX_HISTORY_TURNS = 10
        if len(_user_conversations[current_session_id_for_history]) > MAX_HISTORY_TURNS * 2:
            _user_conversations[current_session_id_for_history] = _user_conversations[current_session_id_for_history][-(MAX_HISTORY_TURNS * 2):]

        return llm_response

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error during conversational search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during search: {str(e)}")
