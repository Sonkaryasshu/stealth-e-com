'use client';

import { useEffect, useState } from 'react';
import ProductGrid from '@/components/ProductGrid';
import SearchBar from '@/components/SearchBar';
import { fetchProducts } from '@/lib/api';
import { Product } from '@/types/definitions';

const pageContainerStyle: React.CSSProperties = {
  maxWidth: '1200px',
  margin: '0 auto',
  padding: '20px',
};

const headerStyle: React.CSSProperties = {
  textAlign: 'center'
};

const companyNameStyle: React.CSSProperties = {
  marginBottom: '2px'
};

const philosophyStyle: React.CSSProperties = {
  fontSize: '1.1em',
  color: '#555',
  maxWidth: '800px',
  margin: '0 auto 10px auto',
  lineHeight: '1.6',
};

const sectionTitleStyle: React.CSSProperties = {
  marginTop: '30px',
  marginBottom: '15px',
  fontSize: '1.8em',
  borderBottom: '2px solid #eee',
  paddingBottom: '10px',
};

const categoryTitleStyle: React.CSSProperties = {
  marginTop: '25px',
  marginBottom: '10px',
  fontSize: '1.5em',
  color: '#333',
};

const categoryFilterStyle: React.CSSProperties = {
  marginBottom: '20px',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
};

const labelStyle: React.CSSProperties = {
  fontSize: '1em',
  fontWeight: 'bold',
};

const selectStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: '1em',
  borderRadius: '4px',
  border: '1px solid #ccc',
  minWidth: '200px',
};


export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [productError, setProductError] = useState<string | null>(null);
  const [isChatActive, setIsChatActive] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  const brandName = "EverGlow Labs";
  const brandPhilosophy = "EverGlow Labs exists to prove that nature and science can co-author skincare that actually works.";

  const categories = ['All', ...new Set(products.map(p => p.category).filter(Boolean) as string[])].sort();

  const filteredProducts = selectedCategory === 'All'
    ? products
    : products.filter(p => p.category === selectedCategory);

  useEffect(() => {
    async function loadProducts() {
      setIsLoadingProducts(true);
      setProductError(null);
      try {
        const fetchedProducts = await fetchProducts();
        setProducts(fetchedProducts);
      } catch (err: any) {
        setProductError(`Failed to load products. Please ensure the backend is running and accessible. Error: ${err.message}`);
      } finally {
        setIsLoadingProducts(false);
      }
    }
    loadProducts();
  }, []);

  return (
    <div style={pageContainerStyle}>
      <header style={headerStyle}>
        <h1 style={companyNameStyle}>{brandName}</h1>
        <p style={philosophyStyle}>{brandPhilosophy}</p>
      </header>
      
      <SearchBar onSearchActivity={setIsChatActive} />
      
      {!isChatActive && (
        <section>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <h2 style={sectionTitleStyle}>Our Products</h2>
            {!isLoadingProducts && products.length > 0 && (
              <div style={categoryFilterStyle}>
                <label htmlFor="category-select" style={labelStyle}>Filter by Category:</label>
                <select 
                  id="category-select"
                  value={selectedCategory} 
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  style={selectStyle}
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          
          {isLoadingProducts && <p>Loading products...</p>}
          {productError && <p style={{ color: 'red' }}>{productError}</p>}
          {!isLoadingProducts && !productError && filteredProducts.length > 0 && (
            <ProductGrid
              productResults={filteredProducts.map(product => ({
                product: product,
                justification: undefined,
                supporting_reviews: null
              }))}
            />
          )}
          {!isLoadingProducts && !productError && products.length > 0 && filteredProducts.length === 0 && (
             <p>No products found in the selected category &quot;{selectedCategory}&quot;.</p>
          )}
          {!isLoadingProducts && !productError && products.length === 0 && (
            <p>No products available at the moment.</p>
          )}
        </section>
      )}
    </div>
  );
}
