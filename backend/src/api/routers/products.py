from pathlib import Path
from typing import List, Optional
import logging
import os
from fastapi import APIRouter, HTTPException
from src.data_models import Product
from src.data_loader import load_products_from_csv

router = APIRouter()
logger = logging.getLogger(__name__)

_BACKEND_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PRODUCT_CATALOG_FILE = _BACKEND_PROJECT_ROOT / "data" / "skincare_catalog.csv"

_products_cache: List[Product] = []
_products_cache_mtime: Optional[float] = None

def get_products_from_file() -> List[Product]:
    global _products_cache, _products_cache_mtime

    try:
        current_mtime = PRODUCT_CATALOG_FILE.stat().st_mtime
    except FileNotFoundError:
        logger.error(f"Product catalog file not found at {str(PRODUCT_CATALOG_FILE)}.")
        _products_cache = []
        _products_cache_mtime = None
        raise HTTPException(status_code=500, detail=f"Product catalog file not found at {str(PRODUCT_CATALOG_FILE)}. Please ensure it exists.")

    if not _products_cache or _products_cache_mtime is None or current_mtime > _products_cache_mtime:
        logger.info(f"Product catalog cache stale or empty. Reloading from {str(PRODUCT_CATALOG_FILE)}.")
        try:
            loaded_products = load_products_from_csv(str(PRODUCT_CATALOG_FILE))
            if not loaded_products:
                 logger.warning(f"No products found in the catalog file {str(PRODUCT_CATALOG_FILE)} or failed to parse. Cache will be empty.")
                 _products_cache = [] 
            else:
                _products_cache = loaded_products
            _products_cache_mtime = current_mtime
            logger.info(f"Successfully reloaded {len(_products_cache)} products into cache. New mtime: {_products_cache_mtime}")

        except Exception as e:
            logger.error(f"Error loading product catalog from {str(PRODUCT_CATALOG_FILE)}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error loading product catalog: {str(e)}")

    return _products_cache

@router.get("/", response_model=List[Product])
async def list_products():
    try:
        products = get_products_from_file()
        if len(products) < 30:
            logger.warning(f"Loaded {len(products)} products, which is less than the target of 30 SKUs.")
        return products
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving products: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while retrieving products: {str(e)}")

@router.post("/clear-cache", status_code=204)
async def clear_product_cache():
    global _products_cache, _products_cache_mtime
    _products_cache = []
    _products_cache_mtime = None
    logger.info("Product cache cleared manually via API endpoint.")
    return None
