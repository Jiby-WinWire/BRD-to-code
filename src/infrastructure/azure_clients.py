"""Centralized initialization and management of Azure service clients."""

import os
import logging
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

_llm_client = None

def get_llm_client():
    """
    Get or initialize Azure OpenAI client for LLM-based reasoning.
    """
    global _llm_client
    
    if _llm_client is not None:
        return _llm_client
    
    try:
        api_key = os.environ.get('AZURE_OPENAI_API_KEY')
        api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
        azure_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        deployment_name = os.environ.get('AZURE_OPENAI_MODEL_DEPLOYMENT', os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4'))
        
        if not api_key:
            logger.warning("AZURE_OPENAI_API_KEY not configured")
            return None
        
        if not azure_endpoint:
            logger.warning("AZURE_OPENAI_ENDPOINT not configured")
            return None
        
        _llm_client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            timeout=30.0,
            max_retries=3
        )
        
        logger.debug(f"Azure OpenAI client initialized (deployment: {deployment_name})")
        return _llm_client
        
    except ImportError:
        logger.warning("OpenAI library not installed - install with: pip install openai")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Azure OpenAI client: {e}")
        return None

def get_llm_deployment_name() -> str:
    """Get the Azure OpenAI deployment name (model to use)."""
    return os.environ.get('AZURE_OPENAI_MODEL_DEPLOYMENT', os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4'))
