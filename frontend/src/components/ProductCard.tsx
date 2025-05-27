import { ProductResult, RagContext } from '@/types/definitions';
import Image from 'next/image';
import { useState } from 'react';

interface ProductCardProps {
  productResult: ProductResult;
}

const cardStyle: React.CSSProperties = {
  border: '1px solid #ddd',
  borderRadius: '8px',
  padding: '16px',
  margin: '8px',
  width: '300px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  position: 'relative',
};

const imageStyle: React.CSSProperties = {
  maxWidth: '100%',
  height: 'auto',
  maxHeight: '200px',
  objectFit: 'contain',
  borderRadius: '4px',
  marginBottom: '12px',
};

const getDynamicPlaceholderUri = (productName?: string): string => {
  let name = productName || "Product";
  if (name.length > 30) {
    name = name.substring(0, 27) + "...";
  }
  const sanitizedName = name.replace(/&/g, '&amp;')
                           .replace(/</g, '&lt;')
                           .replace(/>/g, '&gt;')
                           .replace(/"/g, '&quot;')
                           .replace(/'/g, '&apos;');

  const svgString = `<svg width="280" height="200" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 200" preserveAspectRatio="none">
    <rect width="280" height="200" fill="#868e96"></rect>
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="white" font-family="sans-serif" font-size="16px" dy=".1em">${sanitizedName}</text>
  </svg>`;
  return `data:image/svg+xml;base64,${typeof window !== 'undefined' ? window.btoa(unescape(encodeURIComponent(svgString))) : ''}`;
};

const reviewSectionStyle: React.CSSProperties = {
  marginTop: '10px',
  borderTop: '1px solid #eee',
  paddingTop: '10px',
};

const reviewStyle: React.CSSProperties = {
  fontSize: '0.8em',
  color: '#333',
  marginBottom: '8px',
  padding: '8px',
  backgroundColor: '#f9f9f9',
  borderRadius: '4px',
};

const toggleButtonStyle: React.CSSProperties = {
  background: 'none',
  border: '1px solid #ccc',
  padding: '4px 8px',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.8em',
  marginTop: '5px',
  display: 'inline-block',
};


export default function ProductCard({ productResult }: ProductCardProps) {
  if (!productResult || !productResult.product) {
    return null;
  }
  const { product, justification, supporting_reviews } = productResult;
  const hasReviews = supporting_reviews && supporting_reviews.length > 0;

  const [useFallback, setUseFallback] = useState(false);
  const [showReviews, setShowReviews] = useState(false);

  let imgSrcToUse: string;
  let altTextToUse: string = product.name || "Product image";

  if (product.image_url && !useFallback) {
    imgSrcToUse = product.image_url;
  } else {
    imgSrcToUse = getDynamicPlaceholderUri(product.name);
    altTextToUse = product.name ? `Placeholder for ${product.name}` : "Placeholder image";
  }

  return (
    <div style={cardStyle}>
      <div>
        <Image
          src={imgSrcToUse}
          alt={altTextToUse}
          width={280}
          height={200}
          style={imageStyle}
          onError={() => {
            if (product.image_url && !useFallback) {
              setUseFallback(true);
            }
          }}
        />
        <h3>{product.name || "[Product Name Missing]"}</h3>
        
        {product.category && (
          <p><strong>Category:</strong> {product.category}</p>
        )}
        
        {typeof product["price (USD)"] === 'number' ? (
          <p>
            <strong>Price:</strong> ${product["price (USD)"].toFixed(2)} {product.currency_code || 'USD'} 
          </p>
        ) : (
          <p><strong>Price:</strong> N/A</p>
        )}
        
        {product.description && (
          <p style={{ fontSize: '0.9em', color: '#555', maxHeight: '60px', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: '10px' }}>
            {product.description}
          </p>
        )}

        {product["top_ingredients"] && product["top_ingredients"].length > 0 && (
          <p style={{ fontSize: '0.85em' }}>
            <strong>Key Ingredients:</strong> {product["top_ingredients"].join(', ')} 
          </p>
        )}
        
        {product.tags && product.tags.length > 0 && (
          <p style={{ fontSize: '0.8em', color: '#777' }}>
            <em>Tags: {product.tags.join(', ')}</em>
          </p>
        )}

        {justification && (
            <p style={{ fontSize: '0.85em', fontStyle: 'italic', color: '#28a745', marginTop: '5px' }}>
                <strong>Why this product?</strong> {justification}
            </p>
        )}

        {hasReviews && (
          <button 
            onClick={() => setShowReviews(!showReviews)} 
            style={toggleButtonStyle}
            aria-expanded={showReviews}
            aria-controls={`reviews-${product.product_id}`}
          >
            {showReviews ? 'Hide References' : `Show References (${supporting_reviews?.length})`}
          </button>
        )}
      </div>
      
      {hasReviews && showReviews && (
        <div style={reviewSectionStyle} id={`reviews-${product.product_id}`}>
          <h4 style={{ fontSize: '0.9em', marginBottom: '5px' }}>References:</h4>
          {supporting_reviews?.map((review, index) => (
            <div key={review.chunk_id || index} style={reviewStyle}>
              <p>"{review.text_chunk}"</p>
              {review.metadata?.reviewer && (
                <p style={{ fontSize: '0.9em', textAlign: 'right' }}><em>- {review.metadata.reviewer}
                  {review.metadata?.rating && ` (${review.metadata.rating})`}
                </em></p>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  );
}
