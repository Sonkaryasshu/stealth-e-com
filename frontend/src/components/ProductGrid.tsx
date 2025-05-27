import { ProductResult } from '@/types/definitions';
import ProductCard from './ProductCard';

interface ProductGridProps {
  productResults: ProductResult[];
}

const gridStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '16px',
  justifyContent: 'center',
  padding: '20px 0',
};

export default function ProductGrid({ productResults }: ProductGridProps) {
  if (!productResults || productResults.length === 0) {
    return <p>No products to display.</p>;
  }

  return (
    <div style={gridStyle}>
      {productResults.map((productResult) => (
        <ProductCard 
          key={productResult.product?.product_id || Math.random()}
          productResult={productResult}
        />
      ))}
    </div>
  );
}
