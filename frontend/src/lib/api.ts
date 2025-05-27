import { Product, SearchQuery, SearchResponse } from '@/types/definitions';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function fetchProducts(): Promise<Product[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/products/`); 
    if (!response.ok) {
      const errorData = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorData}`);
    }
    const products: Product[] = await response.json();
    return products;
  } catch (error) {
    return [];
  }
}

export async function postSearchQuery(searchQuery: SearchQuery): Promise<SearchResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/search/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(searchQuery),
    });
    if (!response.ok) {
      const errorData = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorData}`);
    }
    const searchResponse: SearchResponse = await response.json();
    return searchResponse;
  } catch (error) {
    return null;
  }
}
