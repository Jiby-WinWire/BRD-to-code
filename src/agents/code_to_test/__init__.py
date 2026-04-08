"""Code-to-Test Agent Package

Enterprise-grade code and test generation agent packaged with A2A support.
"""

from .code_to_test_agent import CodeToTestAgent, CodeToTestTaskManager
from .memory_manager import CodeToTestMemoryManager, CodeToTestAgentStatus
from .policy_manager import PolicyManager
from .code_to_test_tool import create_code_to_test_tool, generate_code_and_tests_function

__all__ = [
    'CodeToTestAgent',
    'CodeToTestTaskManager',
    'CodeToTestMemoryManager',
    'CodeToTestAgentStatus',
    'PolicyManager',
    'create_code_to_test_tool',
    'generate_code_and_tests_function'
]

__version__ = '1.0.0'
