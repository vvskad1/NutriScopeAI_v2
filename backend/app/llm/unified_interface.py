"""
Unified LLM interface for NutriScope AI
Allows switching between local pretrained model and API-based models
"""

from typing import Dict, Any, List
from app.llm.pretrained_llm.config import USE_LOCAL_MODEL
import logging

logger = logging.getLogger(__name__)

def get_structured_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get structured summary using either local or API model based on configuration
    
    Args:
        context: User context (age, sex, etc.)
        results: List of lab test results with status
        
    Returns:
        Structured summary in consistent format
    """
    try:
        if USE_LOCAL_MODEL:
            logger.info("Using local pretrained model for summary generation")
            return _get_local_summary(context, results)
        else:
            logger.info("Using API-based model for summary generation")
            return _get_api_summary(context, results)
    except Exception as e:
        logger.error(f"Error generating structured summary: {e}")
        # Fallback to API if local model fails
        if USE_LOCAL_MODEL:
            logger.info("Local model failed, falling back to API")
            return _get_api_summary(context, results)
        return {"error": "Failed to generate summary"}

def _get_local_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get summary using local pretrained model"""
    from app.llm.pretrained_llm import generate_structured_summary_local
    return generate_structured_summary_local(context, results)

def _get_api_summary(context: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get summary using API-based model"""
    from app.summarize.llm import summarize_results_structured
    return summarize_results_structured(context, results) or {}

def get_model_info() -> Dict[str, Any]:
    """Get information about the currently configured model"""
    return {
        "using_local_model": USE_LOCAL_MODEL,
        "model_type": "Local FLAN-T5" if USE_LOCAL_MODEL else "Groq API",
        "privacy_mode": USE_LOCAL_MODEL,
        "requires_internet": not USE_LOCAL_MODEL
    }