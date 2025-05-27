from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid

class Product(BaseModel):
    product_id: str = Field(..., alias="product_id")
    product_name: str = Field(..., alias="name")
    
    category: Optional[str] = Field(default=None, alias="category")
    
    description: Optional[str] = Field(default=None, alias="description")
    
    price_usd: Optional[float] = Field(default=None, alias="price (USD)")
    currency_code: Optional[str] = Field(default="USD", alias="currency_code")

    margin_percentage: Optional[float] = Field(default=None, alias="margin (%)")
    
    key_ingredients: Optional[List[str]] = Field(default_factory=list, alias="top_ingredients")
    tags: Optional[List[str]] = Field(default_factory=list, alias="tags")
    image_url: Optional[str] = Field(default=None, alias="image_url")

    class Config:
        populate_by_name = True

class ParsedDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    text_chunk: str
    source_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchQuery(BaseModel):
    query: str
    session_id: Optional[str] = None

class ProductResult(BaseModel):
    product: Product
    justification: Optional[str] = None
    supporting_reviews: List[DocumentChunk] = Field(default_factory=list)

class SearchResponse(BaseModel):
    session_id: Optional[str] = None
    results: Optional[List[ProductResult]] = None
    rag_contexts: Optional[List[DocumentChunk]] = None
    follow_up_questions: Optional[List[str]] = None
    answer: Optional[str] = None
    contextual_justification: Optional[str] = None
