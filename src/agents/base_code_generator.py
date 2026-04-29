from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseCodeGenerator(ABC):
    """
    Abstract base class for all language code generators.
    """
    
    @staticmethod
    @abstractmethod
    def generate_from_stories(stories: List[Dict], llm_client, deployment_name: str) -> Dict[str, str]:
        """
        Generate application files from stories.
        Returns dict with file paths as keys and code content as values.
        """
        pass

    @staticmethod
    @abstractmethod
    def _generate_with_llm(stories: List[Dict], llm_client, deployment_name: str) -> Dict[str, str]:
        """
        Generate using LLM (e.g., Azure OpenAI).
        """
        pass

    @staticmethod
    @abstractmethod
    def _generate_from_templates(stories: List[Dict]) -> Dict[str, str]:
        """
        Fallback to template-based generation.
        """
        pass
