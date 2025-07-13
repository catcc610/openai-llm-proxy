"""
External LLM Service Package
"""

from typing import Optional
from app.services.base import ServiceRegistry
from app.services.external_llm.service import ExternalLLMService
from logger.logger import get_logger

logger = get_logger(__name__)

_instance: Optional[ExternalLLMService] = None


def get_external_llm_service() -> ExternalLLMService:
    """
    Factory function to get the singleton instance of ExternalLLMService.
    """
    global _instance
    if _instance is None:
        logger.info("🔧 Creating new instance of ExternalLLMService...")
        _instance = ExternalLLMService()
        # Register the service instance with the registry
        ServiceRegistry.register("external_llm", _instance)
    return _instance
