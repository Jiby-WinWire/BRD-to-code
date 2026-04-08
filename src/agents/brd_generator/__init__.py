"""BRD Generator Agent Package

Enterprise-grade Business Requirements Document generator with:
- LangGraph/LangChain agent framework
- Redis-based state management
- Azure Search semantic caching
- Policy-based access control
- A2A protocol support
"""

from .brd_generator_agent import BRDGeneratorAgent, BRDTaskManager
from .memory_manager import BRDMemoryManager, BRDAgentStatus
from .policy_manager import PolicyManager
from .brd_generator_tool import create_brd_generation_tool

__all__ = [
    'BRDGeneratorAgent',
    'BRDTaskManager',
    'BRDMemoryManager',
    'BRDAgentStatus',
    'PolicyManager',
    'create_brd_generation_tool'
]

__version__ = '1.0.0'
