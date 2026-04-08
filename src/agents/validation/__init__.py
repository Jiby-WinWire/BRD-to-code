"""Validation Agent Package

Enterprise-grade Document/Requirements validation with:
- LangGraph/LangChain agent framework
- Redis-based state management
- Azure Search semantic analysis
- Policy-based access control
- A2A protocol support
"""

from .validation_agent import ValidationAgent, ValidationTaskManager
from .memory_manager import ValidationMemoryManager, ValidationAgentStatus
from .policy_manager import PolicyManager
from .validation_tool import create_validation_tool

__all__ = [
    'ValidationAgent',
    'ValidationTaskManager',
    'ValidationMemoryManager',
    'ValidationAgentStatus',
    'PolicyManager',
    'create_validation_tool'
]

__version__ = '1.0.0'
