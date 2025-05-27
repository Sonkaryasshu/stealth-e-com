export interface Product {
  product_id: string;
  name: string;
  category: string | null;
  description: string | null;
  "top_ingredients": string[] | null;
  tags: string[] | null;
  "price (USD)": number;
  currency_code: string | null;
  "margin (%)": number | null;
  image_url: string | null;
}

export interface ProductResult {
  product: Product;
  justification?: string;
  supporting_reviews: RagContext[] | null;
}

export interface RagContextMetadata {
  product_name?: string;
  reviewer?: string;
  rating?: string;
  ticket_id?: string;
  source_file?: string;
  [key: string]: any;
}

export interface RagContext {
  chunk_id: string;
  document_id: string;
  text_chunk: string;
  source_type: string;
  metadata: RagContextMetadata;
}

export interface SearchResponse {
  session_id: string | null;
  results: ProductResult[] | null;
  rag_contexts: RagContext[] | null;
  follow_up_questions: string[] | null;
  answer: string | null;
  contextual_justification: string | null;
}

export interface SearchQuery {
  query: string;
  session_id?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text?: string;
  response?: SearchResponse;
  timestamp: Date;
}
