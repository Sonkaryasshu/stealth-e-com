import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
import asyncio
import logging
import pydantic
from google.api_core import exceptions as google_api_exceptions
from google.generativeai import types as google_genai_types

from src.config import GOOGLE_API_KEY, GEMINI_MODEL_NAME_E_COM
from src.data_models import (
    SearchResponse,
    ProductResult,
    DocumentChunk
)

logger = logging.getLogger(__name__)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    logger.warning("GOOGLE_API_KEY not found at llm_handler module load. LLM will be disabled if not set by runtime.")


def _format_rag_contexts(rag_contexts: List[Dict[str, Any]]) -> str:
    if not rag_contexts:
        return "No specific context found from knowledge base."
    
    formatted_contexts = []
    for i, context in enumerate(rag_contexts):
        text_chunk = context.get('text_chunk', 'N/A')
        if len(text_chunk) > 300:
            text_chunk = text_chunk[:297] + "..."
        metadata_info = context.get('metadata', {})
        source_type = metadata_info.get('source_type', 'unknown source')
        chunk_id = context.get('id', f'missing_id_for_context_{i+1}')
        formatted_contexts.append(f"Context {i+1} (Chunk ID: {chunk_id}, Source: {source_type}):\n{text_chunk}\nMetadata: {metadata_info}")
    return "\n\n".join(formatted_contexts)


async def get_conversational_response(
    query: str,
    rag_contexts_raw_dicts: List[Dict[str, Any]],
    session_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> SearchResponse:
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not found. LLM functionality will be disabled.")
        return SearchResponse(
            session_id=session_id,
            answer="LLM service is not configured. Please provide an API key.",
            contextual_justification="LLM service unavailable.",
            results=[],
            rag_contexts=[],
            follow_up_questions=[]
        )
    
    system_instruction = """You are a helpful and friendly AI personal shopper for an online skincare store.
Your goal is to understand the user's needs and provide relevant product recommendations, 
answer questions about products or skincare, or ask clarifying questions if the user's query is vague.
Maintain a conversational tone and refer to previous interactions if relevant."""

    valid_history = []
    if conversation_history:
        for turn in conversation_history:
            if isinstance(turn, dict) and "role" in turn and "parts" in turn:
                valid_history.append(turn)

    model = genai.GenerativeModel(
        GEMINI_MODEL_NAME_E_COM,
        system_instruction=system_instruction
    )
    
    chat = model.start_chat(history=valid_history if valid_history else None)
    
    max_retries = 3
    retry_delay_seconds = 2

    formatted_rag = _format_rag_contexts(rag_contexts_raw_dicts)
    
    simplified_json_output_structure_description = """
    {
      "session_id": "string (a unique ID for this conversational session, reuse if provided in input)",
      "results": [
        {
          "product": {
            "product_id": "string (Product's unique ID from catalog)",
            "product_name": "string (Product name from catalog)",
            "category": "string (optional, Product category from catalog)",
            "description": "string (optional, Brief product description, can be summarized)",
            "price_usd": "number (Product price in USD from catalog)",
            "currency_code": "string (optional, e.g., USD)",
            "margin_percentage": "number (optional, product's margin percentage from catalog or RAG context, e.g., 0.48 for 48%)",
            "key_ingredients": ["string (optional, list of key ingredients from catalog or RAG)"],
            "tags": ["string (optional, list of relevant tags, can be from catalog or derived from RAG context)"],
            "image_url": "string (optional, URL of product image from catalog if available)"
          },
          "justification": "string (optional, brief explanation why this specific product is recommended)",
          "supporting_review_chunk_ids": ["string (list of chunk_ids of relevant reviews from RAG context that specifically support THIS product recommendation. Include if the review offers substantive feedback (e.g., 3 stars or more), is relevant, and its source_type is 'review'.)"]
        }
      ] (optional, list of recommended products if applicable, aim for up to 5 products if distinct and relevant products are found in context),
      "used_rag_context_ids": ["string (list of chunk_ids for ALL RAG contexts you found relevant and used to generate this response, including for products, answers, or justifications. The backend will use these IDs to populate supporting information.)"],
      "follow_up_questions": ["string (optional, list of 1-2 relevant, contextual follow-up questions.
        - If the query is vague (e.g., 'something for summer'), ask questions to clarify BEFORE showing products (results should be null/empty). Example: 'What products are you interested in - toners, serums or SPF focused?'.
        - If the query is for a general product type (e.g., 'serums', 'moisturizers') and you are showing initial results, ALSO ask follow-up questions to refine the search. Example: 'Great choice! What skin concern are you targeting - hydration, blemishes, something else?' or 'Tell me more about your skin, say oily, acne-prone or dry and flakey — I’ll narrow your search!'.
        - If the query is very specific and recommendations are highly targeted, or if you are providing a direct answer to a non-recommendation question, this field can be null or an empty list unless further clarification is truly essential.)"],
      "answer": "string (optional, a direct, concise answer to a non-recommendation question, synthesized from RAG context if used. Do not just repeat RAG context. If recommending products, this field should typically be null.)",
      "contextual_justification": "string (A brief, friendly, overall explanation of why these results/questions are being shown. This should be user-facing and should NOT mention internal ranking logic, profitability, or margin percentages. E.g., 'Based on your interest in products for oily skin, here are some suggestions.' or 'I found some information about our brand philosophy for you.' or 'To help find the best products for you, I have a couple more questions.')"
    }
    """

    prompt = f"""
You are a helpful and friendly AI personal shopper for an online skincare store.
Your goal is to understand the user's needs and provide relevant product recommendations, 
answer questions about products or skincare, or ask clarifying questions if the user's query is vague.
Consider the ongoing conversation history if provided.

Current User's query: "{query}"

Relevant information retrieved from our knowledge base (RAG contexts) for the CURRENT query:
---
{formatted_rag}
---
The RAG contexts above may contain:
- `product_info`: Official details about a product (name, description, ingredients, etc.). Metadata includes `product_id`.
- `review`: Customer reviews. Metadata includes `product_name`, `rating`.
- `customer_ticket`: Customer support interactions.
- `brand_info`: General information about our brand.

Your task for THE CURRENT query is to:
1.  Analyze the user's query, taking into account the conversation history (if any).
    - **If the current query seems to refine or add detail to a topic discussed in the conversation history (e.g., specifying a skin type after previously asking for a product type, or asking about a specific feature of a product just mentioned), you MUST use the history to understand the full context. For example, if the user previously asked for "serums" and now says "for oily skin", you should interpret the current need as "serums for oily skin". Do not ask for the product type again if it was recently established.**
2.  **Deeply analyze the provided RAG contexts.** Synthesize these details with the user's current query and conversation history.
    - If a RAG context has `source_type: "product_info"`, treat its content as authoritative product data. Use its `metadata.product_id` if recommending this product.
    - If a RAG context has `source_type: "review"`, pay attention to the `metadata.rating` and the sentiment of the review text.
3.  Decide on the best course of action:
    a.  If the query is a request for product recommendations (e.g., "serums", "moisturizer for dry skin") AND the RAG contexts or query suggest specific products or product types:
        - Recommend up to 5 relevant products if distinct and relevant products are found in the RAG contexts. **Crucially, only recommend products if you can confidently identify their `product_id` from the `metadata` of a retrieved RAG context (especially from `source_type: "product_info"` or a review/ticket clearly linked to a product).** Do not invent products or `product_id`s.
        - If you identify suitable products, for each one, populate its 'product' object. The `product_id` is mandatory. Other details (name, category, description, price_usd, currency_code, margin_percentage, key_ingredients, tags, image_url) should be populated if found in the RAG context for that product. The backend will verify and fill in missing details from the main catalog if you provide a valid `product_id`.
        - For each recommended product, if there are relevant positive reviews in the RAG context (source_type: "review"), list their `chunk_id`s in the `supporting_review_chunk_ids` field for that product. Only include reviews that are clearly positive and directly relevant to the product.
        - Provide a 'justification' for each recommended product, referencing insights from RAG (e.g., "A customer review mentioned this serum helped with similar concerns...").
        - The overall 'contextual_justification' should explain the recommendation set in a user-friendly way (e.g., 'Based on your interest in serums, here are a few options I found.'). Do NOT mention internal ranking logic, profitability, or margin percentages in this user-facing text.
        - **If the user's query is for a general product category (e.g., "serums", "face wash") and you are providing initial product recommendations, you SHOULD ALSO generate 1-2 follow-up questions in the `follow_up_questions` field to help narrow down the selection further or understand specific needs. For example: 'Great choice! What skin concern are you targeting - hydration, blemishes, something else?' or 'To help me find the perfect moisturizer for you, could you tell me a bit about your skin type?'.**
        - **If the user's query is very specific (e.g., 'vitamin C serum for brightening dark spots for sensitive skin') and you are confident the recommendations fully address it, then `follow_up_questions` can be null or an empty list.**
        - Focus on providing accurate `product_id` and any available `price_usd` and `margin_percentage` from the context, as these details are important for backend processing, but do not mention margin or profitability to the user.
        - The `answer` field should typically be null when providing product recommendations.
    b.  If the query is very vague (e.g., "something for summer", "help me") and it's difficult to provide initial recommendations or a direct answer:
        - Focus on providing a list of 1-2 relevant, contextual follow-up questions in the 'follow_up_questions' field to clarify the user's needs (e.g., 'What products are you interested in — toners, serums or SPF focused?' → 'Any skin concerns or ingredients to avoid?').
        - Provide an overall 'contextual_justification' explaining why you are asking these questions (e.g., 'To help find the best products for you, I have a couple of questions.').
        - `results` should be empty or null, and `answer` should be null.
    c.  If the query is a specific question that can be answered using the RAG contexts (e.g., "Is product X good for sensitive skin?", "What are the ingredients of product Y?", "What is your brand's philosophy on animal testing?", "Tell me about your return policy."):
        - Provide a concise, direct, and synthesized answer in the 'answer' field, formulated based on the RAG contexts.
        - Do NOT embed raw snippets from RAG contexts directly into the 'answer'. The frontend displays RAG contexts separately. Your answer should be a helpful summary or extraction.
        - You can subtly mention the source type if it adds credibility (e.g., "According to our brand information...", "Customer reviews suggest...").
        - `results` should be empty or null, and `follow_up_questions` should generally be null or empty unless the question itself implies a need for further interaction.
        - Provide an overall 'contextual_justification' explaining the basis of your answer (e.g., 'I found some information about our brand philosophy for you.').
    d.  If the query cannot be reasonably answered with the provided RAG contexts, or if no relevant information is found:
        - Politely state that you cannot help with the specific request or that no information was found in the 'answer' field.
        - Provide a 'contextual_justification'.
        - `results` and `follow_up_questions` should be null or empty.
4.  **Crucially, identify ALL `chunk_id`s from the provided RAG contexts that you used or found relevant in generating any part of your response (recommendations, answer, justifications, etc.). List these `chunk_id`s in the `used_rag_context_ids` field of your JSON response.** This allows the backend to provide the user with the specific sources of information.

IMPORTANT: Respond ONLY with a single, valid JSON object that strictly adheres to the following structure. Do NOT include any text outside of this JSON object (no preamble, no explanation before or after the JSON).

JSON Output Structure:
```json
{simplified_json_output_structure_description}
```

Ensure your response is well-formatted JSON.
If recommending products, ensure the `product_id` and other details are accurate based on the provided product information if available.
If asking follow-up questions, make them concise and relevant.
The `contextual_justification` should always be present and explain your response.
The `used_rag_context_ids` field MUST be populated with the `chunk_id`s of all RAG contexts you deemed relevant.
If no products are recommended, `results` should be an empty list or null.
If no follow-up questions are asked, `follow_up_questions` should be an empty list or null.
If no direct answer is given, `answer` should be null.
The `session_id` in the response should be the same as the `session_id` from the input if provided, otherwise a new one can be generated (though the backend API layer will handle new ID generation if missing).
"""
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"LLM call attempt {attempt + 1} of {max_retries} for session {session_id}")
            response = await chat.send_message_async(prompt)
            raw_llm_output = response.text
            
            json_start_index = raw_llm_output.find('{')
            json_end_index = raw_llm_output.rfind('}')
            
            if json_start_index == -1 or json_end_index == -1:
                raise ValueError("LLM output not in expected JSON format (markers not found).")
                
            json_string = raw_llm_output[json_start_index : json_end_index+1]
            llm_json_response = json.loads(json_string)
            
            parsed_response = SearchResponse(**llm_json_response)
            
            used_ids_from_llm = llm_json_response.get("used_rag_context_ids", [])
            hydrated_rag_contexts: List[DocumentChunk] = []
            
            raw_dict_map = {}
            if rag_contexts_raw_dicts:
                raw_dict_map = {raw_dict.get('id'): raw_dict for raw_dict in rag_contexts_raw_dicts if raw_dict.get('id')}

            if used_ids_from_llm:
                for chunk_id_from_llm in used_ids_from_llm:
                    raw_dict = raw_dict_map.get(chunk_id_from_llm)
                    if raw_dict:
                        try:
                            current_metadata = raw_dict.get('metadata', {})
                            if not isinstance(current_metadata, dict):
                                current_metadata = {}
                            
                            doc_id_val = current_metadata.get('original_doc_id') 
                            source_type_val = current_metadata.get('source_type')
                            text_chunk_val = raw_dict.get('text_chunk')

                            if not all([chunk_id_from_llm, doc_id_val, source_type_val, text_chunk_val]):
                                logger.warning(f"Skipping RAG context due to missing critical field(s) for chunk_id {chunk_id_from_llm}. Details - doc_id: {doc_id_val}, source_type: {source_type_val}, text_chunk_present: {bool(text_chunk_val)}")
                                continue
                            
                            hydrated_rag_contexts.append(DocumentChunk(
                                chunk_id=chunk_id_from_llm,
                                document_id=doc_id_val,
                                source_type=source_type_val,
                                text_chunk=text_chunk_val,
                                metadata=current_metadata
                            ))
                        except Exception as chunk_parse_error:
                            logger.error(f"Error hydrating RAG context for chunk_id {chunk_id_from_llm}: {chunk_parse_error}. Dict: {raw_dict}", exc_info=True)
                    else:
                        logger.warning(f"LLM specified used_rag_context_id '{chunk_id_from_llm}' not found in provided rag_contexts_raw_dicts.")
            
            parsed_response.rag_contexts = hydrated_rag_contexts
            
            if parsed_response.results and rag_contexts_raw_dicts:
                raw_llm_results = llm_json_response.get("results", [])
                for i, product_result_obj in enumerate(parsed_response.results):
                    if i < len(raw_llm_results):
                        raw_llm_product_item = raw_llm_results[i]
                        review_chunk_ids_for_product = raw_llm_product_item.get("supporting_review_chunk_ids", [])
                        
                        hydrated_reviews_for_product: List[DocumentChunk] = []
                        for review_chunk_id in review_chunk_ids_for_product:
                            raw_review_dict = raw_dict_map.get(review_chunk_id)
                            if raw_review_dict:
                                try:
                                    current_metadata = raw_review_dict.get('metadata', {})
                                    if not isinstance(current_metadata, dict): current_metadata = {}
                                    
                                    doc_id_val = current_metadata.get('original_doc_id')
                                    source_type_val = current_metadata.get('source_type')
                                    text_chunk_val = raw_review_dict.get('text_chunk')

                                    if not all([review_chunk_id, doc_id_val, source_type_val, text_chunk_val]):
                                        logger.warning(f"Skipping supporting review due to missing critical field(s) for chunk_id {review_chunk_id} for product {product_result_obj.product.product_id if product_result_obj.product else 'Unknown'}.")
                                        continue
                                    
                                    if source_type_val != 'review':
                                        logger.warning(f"LLM suggested a non-review chunk_id {review_chunk_id} (type: {source_type_val}) as supporting review for product {product_result_obj.product.product_id if product_result_obj.product else 'Unknown'}. Skipping.")
                                        continue

                                    hydrated_reviews_for_product.append(DocumentChunk(
                                        chunk_id=review_chunk_id,
                                        document_id=doc_id_val,
                                        source_type=source_type_val,
                                        text_chunk=text_chunk_val,
                                        metadata=current_metadata
                                    ))
                                except Exception as review_hydrate_error:
                                    logger.error(f"Error hydrating supporting review for chunk_id {review_chunk_id} for product {product_result_obj.product.product_id if product_result_obj.product else 'Unknown'}: {review_hydrate_error}. Dict: {raw_review_dict}", exc_info=True)
                            else:
                                logger.warning(f"LLM specified supporting_review_chunk_id '{review_chunk_id}' for product {product_result_obj.product.product_id if product_result_obj.product else 'Unknown'} not found in provided rag_contexts_raw_dicts.")
                        product_result_obj.supporting_reviews = hydrated_reviews_for_product
            
            if not parsed_response.session_id:
                if session_id:
                    parsed_response.session_id = session_id
                else:
                    import uuid
                    parsed_response.session_id = str(uuid.uuid4())
            
            if parsed_response.follow_up_questions is None:
                parsed_response.follow_up_questions = []
            elif isinstance(parsed_response.follow_up_questions, str):
                parsed_response.follow_up_questions = [parsed_response.follow_up_questions]

            return parsed_response

        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt + 1}: LLM output was not valid JSON: {e}. Output: {raw_llm_output[:500]}")
            last_exception = e
        except pydantic.ValidationError as e:
            logger.warning(f"Attempt {attempt + 1}: LLM JSON did not match Pydantic model: {e}. JSON: {json_string[:500]}")
            last_exception = e
        except ValueError as e:
             logger.warning(f"Attempt {attempt + 1}: LLM output format error: {e}. Output: {raw_llm_output[:500]}")
             last_exception = e
        except google_api_exceptions.ResourceExhausted as e:
            logger.warning(f"Attempt {attempt + 1}: Rate limit hit (429 - ResourceExhausted): {e}. Retrying...")
            last_exception = e
        except (google_api_exceptions.InternalServerError,
                google_api_exceptions.ServiceUnavailable,
                google_api_exceptions.DeadlineExceeded) as e:
            logger.warning(f"Attempt {attempt + 1}: Server/gateway error (5xx-like): {e}. Retrying...")
            last_exception = e
        except google_genai_types.BlockedPromptException as e:
            logger.error(f"LLM prompt blocked (non-retriable): {e}", exc_info=True)
            return SearchResponse(
                session_id=session_id,
                answer="The request could not be processed due to content policy.",
                contextual_justification="Content policy violation.",
                results=[], rag_contexts=[], follow_up_questions=[]
            )
        except google_genai_types.StopCandidateException as e:
            logger.error(f"LLM generation stopped (non-retriable): {e}", exc_info=True)
            return SearchResponse(
                session_id=session_id,
                answer="The response generation was stopped. This might be due to safety settings or other reasons.",
                contextual_justification="Response generation incomplete.",
                results=[], rag_contexts=[], follow_up_questions=[]
            )
        except google_api_exceptions.GoogleAPIError as e:
            logger.warning(f"Attempt {attempt + 1}: Google API Error: {e}. Retrying...")
            last_exception = e
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Unexpected error: {e.__class__.__name__} - {e}. Retrying...", exc_info=True)
            last_exception = e
        
        if attempt < max_retries - 1:
            logger.info(f"Waiting {retry_delay_seconds}s before next LLM attempt...")
            await asyncio.sleep(retry_delay_seconds)

    logger.error(f"All {max_retries} LLM attempts failed. Last error: {last_exception.__class__.__name__ if last_exception else 'Unknown'}: {last_exception}", exc_info=True if last_exception else False)
    
    error_message = "Sorry, I'm having trouble connecting to my brain right now. Please try again later."
    error_justification = "LLM API call failed after multiple attempts."

    if isinstance(last_exception, json.JSONDecodeError):
        error_message = "Sorry, I had trouble processing that. Could you try rephrasing?"
        error_justification = "LLM response parsing error after multiple attempts."
    elif isinstance(last_exception, pydantic.ValidationError):
        error_message = "Sorry, I encountered an issue with the response structure. Please try again."
        error_justification = "LLM response validation error after multiple attempts."
    elif isinstance(last_exception, ValueError) and "LLM output not in expected JSON format" in str(last_exception):
        error_message = "Sorry, I couldn't generate a structured response. Please try again."
        error_justification = "LLM output format error after multiple attempts."
    elif isinstance(last_exception, google_api_exceptions.ResourceExhausted):
        error_message = "I'm a bit overwhelmed at the moment. Please try again in a few moments."
        error_justification = "Rate limit reached. Please try again later."
    elif isinstance(last_exception, (google_api_exceptions.InternalServerError, google_api_exceptions.ServiceUnavailable, google_api_exceptions.DeadlineExceeded)):
        error_message = "There seems to be a temporary issue with the AI service. Please try again shortly."
        error_justification = "AI service unavailable or server error."
    elif isinstance(last_exception, google_api_exceptions.GoogleAPIError):
        error_message = "An issue occurred while communicating with the AI service. Please try again."
        error_justification = "AI service communication error."


    return SearchResponse(
        session_id=session_id,
        answer=error_message,
        contextual_justification=error_justification,
        results=[], rag_contexts=[], follow_up_questions=[]
    )
