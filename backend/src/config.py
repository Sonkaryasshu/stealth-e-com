import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not found in environment variables. LLM functionality will be disabled.")

# Attempt to get the Gemini model name from environment variable, otherwise use default
DEFAULT_GEMINI_MODEL_NAME = "gemini-2.5-pro-preview-05-06"
GEMINI_MODEL_NAME_E_COM = os.getenv("GEMINI_MODEL_NAME_E_COM", DEFAULT_GEMINI_MODEL_NAME)

if GEMINI_MODEL_NAME_E_COM == DEFAULT_GEMINI_MODEL_NAME and not os.getenv("GEMINI_MODEL_NAME_E_COM"):
    logger.info(f"GEMINI_MODEL_NAME_E_COM not found in environment variables. Using default: {DEFAULT_GEMINI_MODEL_NAME}")
else:
    logger.info(f"Using GEMINI_MODEL_NAME_E_COM from environment: {GEMINI_MODEL_NAME_E_COM}")
