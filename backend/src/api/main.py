import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import products, search
from ingest_data import main as ingest_data_main # Changed import path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Running data ingestion...")
    try:
        ingest_data_main()
        logger.info("Data ingestion completed successfully.")
    except Exception as e:
        logger.error(f"CRITICAL: Data ingestion failed during startup: {e}. Application will exit.", exc_info=True)
        raise
    yield
    logger.info("Application shutdown.")

app = FastAPI(
    title="Conversational Store API",
    description="API for the Conversational Store mini-POC",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(search.router, prefix="/search", tags=["search"])

@app.get("/", tags=["root"])
async def read_root():
    return {"message": "Welcome to the Conversational Store API!"}
