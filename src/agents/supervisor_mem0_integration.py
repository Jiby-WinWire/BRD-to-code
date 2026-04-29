"""
Supervisor Mem0 Integration Module
Extends the Supervisor class with memory management capabilities
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add src/agents to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mem0_manager import Mem0Manager, create_memory_manager

logger = logging.getLogger(__name__)


class SupervisorWithMemory:
    """
    Mixin class to add Mem0 memory management to Supervisor.
    This tracks all agent interactions and user conversations.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize memory management for supervisor
        
        Args:
            user_id: Optional user identifier for personalized memory
        """
        self.memory_manager = create_memory_manager(user_id=user_id)
        logger.info("SupervisorWithMemory initialized")
    
    def set_memory_session(self, session_id: str):
        """Set the current session ID for memory tracking"""
        self.memory_manager.set_session(session_id)
        logger.info(f"Memory session set: {session_id}")
    
    def remember_user_requirement(self, requirement: str, language: str, template_id: Optional[str] = None):
        """
        Store the initial user requirement in memory
        
        Args:
            requirement: User's requirement text
            language: Selected programming language
            template_id: Optional template identifier
        """
        content = f"User requested: {requirement}"
        
        from datetime import datetime
        
        metadata = {
            "type": "user_requirement",
            "language": language,
            "timestamp": datetime.now().isoformat()
        }
        
        if template_id:
            metadata["template_id"] = template_id
        
        result = self.memory_manager.add_conversation(
            role="user",
            content=content,
            agent_name="supervisor",
            metadata=metadata
        )
        
        return result
    
    def remember_agent_interaction(
        self,
        agent_name: str,
        input_data: Any,
        output_data: Any,
        success: bool,
        metadata: Optional[Dict] = None
    ):
        """
        Store agent interaction in memory
        
        Args:
            agent_name: Name of the agent (e.g., 'brd_generator', 'jira_to_code')
            input_data: Input sent to the agent
            output_data: Output received from the agent
            success: Whether the agent execution was successful
            metadata: Additional metadata
        """
        # Convert data to strings if they're dicts
        input_str = str(input_data)[:500] if isinstance(input_data, dict) else str(input_data)[:500]
        output_str = str(output_data)[:500] if isinstance(output_data, dict) else str(output_data)[:500]
        
        content = f"""Agent: {agent_name}
Status: {'Success' if success else 'Failed'}
Input: {input_str}
Output: {output_str}"""
        
        interaction_metadata = {
            "type": "agent_interaction",
            "agent": agent_name,
            "success": success,
            **(metadata or {})
        }
        
        result = self.memory_manager.add_conversation(
            role="assistant",
            content=content,
            agent_name=agent_name,
            metadata=interaction_metadata
        )
        
        return result
    
    def remember_workflow_step(
        self,
        step_number: int,
        step_name: str,
        result: Dict[str, Any]
    ):
        """
        Store workflow step completion in memory
        
        Args:
            step_number: Step number in the workflow
            step_name: Name of the step
            result: Result dictionary from the step
        """
        success = result.get("success", False)
        content = f"Step {step_number}: {step_name} - {'Completed' if success else 'Failed'}"
        
        metadata = {
            "type": "workflow_step",
            "step_number": step_number,
            "step_name": step_name,
            "success": success
        }
        
        result_data = self.memory_manager.add_conversation(
            role="system",
            content=content,
            agent_name="supervisor",
            metadata=metadata
        )
        
        return result_data
    
    def remember_generated_files(self, file_paths: list):
        """
        Store information about generated files
        
        Args:
            file_paths: List of generated file paths
        """
        content = f"Generated {len(file_paths)} files: {', '.join(file_paths[:10])}"
        if len(file_paths) > 10:
            content += f" and {len(file_paths) - 10} more..."
        
        metadata = {
            "type": "generated_files",
            "file_count": len(file_paths),
            "files": file_paths
        }
        
        result = self.memory_manager.add_conversation(
            role="system",
            content=content,
            agent_name="supervisor",
            metadata=metadata
        )
        
        return result
    
    def remember_user_feedback(self, feedback: str, rating: Optional[int] = None):
        """
        Store user feedback about the generated code
        
        Args:
            feedback: User's feedback text
            rating: Optional rating (1-5)
        """
        content = f"User feedback: {feedback}"
        
        metadata = {
            "type": "user_feedback",
        }
        
        if rating:
            metadata["rating"] = rating
            content += f" (Rating: {rating}/5)"
        
        result = self.memory_manager.add_conversation(
            role="user",
            content=content,
            agent_name="supervisor",
            metadata=metadata
        )
        
        return result
    
    def get_relevant_context(self, query: str, limit: int = 5) -> str:
        """
        Get relevant context from previous conversations
        
        Args:
            query: Query to search for relevant memories
            limit: Maximum number of memories to retrieve
            
        Returns:
            Formatted context string
        """
        memories = self.memory_manager.get_relevant_memories(
            query=query,
            limit=limit
        )
        
        if not memories:
            return ""
        
        context_parts = ["### Relevant Context from Previous Sessions:"]
        for i, mem in enumerate(memories, 1):
            content = mem.get("content", "")
            score = mem.get("score", 0.0)
            context_parts.append(f"{i}. {content[:200]}... (relevance: {score:.2f})")
        
        return "\n".join(context_parts)
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """
        Extract user preferences from memory
        
        Returns:
            Dictionary of user preferences
        """
        preferences = {}
        
        # Search for preference-related memories
        pref_memories = self.memory_manager.get_relevant_memories(
            query="user preference language framework template",
            limit=20
        )
        
        for mem in pref_memories:
            metadata = mem.get("metadata", {})
            if metadata.get("type") == "user_preference":
                key = metadata.get("key")
                value = metadata.get("value")
                if key and value:
                    preferences[key] = value
        
        return preferences
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored memories
        
        Returns:
            Dictionary with memory statistics
        """
        return self.memory_manager.get_memory_stats()
    
    def enhance_requirement_with_memory(self, requirement: str) -> str:
        """
        Enhance user requirement with relevant context from memory
        
        Args:
            requirement: Original user requirement
            
        Returns:
            Enhanced requirement with memory context
        """
        # Get relevant context
        context = self.get_relevant_context(requirement, limit=5)
        
        # Get user preferences
        preferences = self.memory_manager.get_user_preferences()
        
        # Build enhanced prompt
        enhanced = []
        
        if context:
            enhanced.append(context)
            enhanced.append("")
        
        if preferences:
            enhanced.append("### User Preferences:")
            for key, value in preferences.items():
                enhanced.append(f"- {key}: {value}")
            enhanced.append("")
        
        enhanced.append("### Current Requirement:")
        enhanced.append(requirement)
        
        return "\n".join(enhanced)


def add_memory_to_supervisor(supervisor_instance, user_id: Optional[str] = None):
    """
    Decorator-like function to add memory capabilities to an existing Supervisor instance
    
    Args:
        supervisor_instance: Existing Supervisor instance
        user_id: Optional user identifier
        
    Returns:
        Enhanced supervisor with memory capabilities
    """
    # Create memory manager
    memory_manager = create_memory_manager(user_id=user_id)
    
    # Attach memory manager to supervisor
    supervisor_instance.memory_manager = memory_manager
    
    # Set memory session to match supervisor session
    if hasattr(supervisor_instance, 'session_id'):
        memory_manager.set_session(supervisor_instance.session_id)
    
    # Add memory methods to the instance
    supervisor_instance.remember_user_requirement = lambda requirement, language, template_id=None: SupervisorWithMemory.remember_user_requirement(
        supervisor_instance, requirement, language, template_id
    )
    supervisor_instance.remember_agent_interaction = lambda agent_name, input_data, output_data, success, metadata=None: SupervisorWithMemory.remember_agent_interaction(
        supervisor_instance, agent_name, input_data, output_data, success, metadata
    )
    supervisor_instance.remember_workflow_step = lambda step_number, step_name, result: SupervisorWithMemory.remember_workflow_step(
        supervisor_instance, step_number, step_name, result
    )
    supervisor_instance.remember_generated_files = lambda files: SupervisorWithMemory.remember_generated_files(
        supervisor_instance, files
    )
    supervisor_instance.get_relevant_context = lambda query, limit=5: SupervisorWithMemory.get_relevant_context(
        supervisor_instance, query, limit
    )
    supervisor_instance.enhance_requirement_with_memory = lambda requirement: SupervisorWithMemory.enhance_requirement_with_memory(
        supervisor_instance, requirement
    )
    supervisor_instance.get_memory_stats = lambda: SupervisorWithMemory.get_memory_stats(
        supervisor_instance
    )
    supervisor_instance.get_user_preferences = lambda: supervisor_instance.memory_manager.get_user_preferences()
    
    logger.info(f"Memory capabilities added to Supervisor instance: {supervisor_instance.session_id}")
    
    return supervisor_instance


# Example usage functions for testing
async def test_memory_integration():
    """Test the memory integration with a mock supervisor"""
    print("\n=== Testing Supervisor Memory Integration ===\n")
    
    # Create a mock supervisor-like object
    class MockSupervisor:
        def __init__(self):
            self.session_id = "test-session-001"
            self.context_id = "test-context-001"
    
    # Create mock supervisor
    supervisor = MockSupervisor()
    
    # Add memory capabilities
    supervisor = add_memory_to_supervisor(supervisor, user_id="test_user")
    
    # Test 1: Remember user requirement
    print("1. Storing user requirement...")
    supervisor.remember_user_requirement(
        requirement="Create a todo list application with user authentication",
        language="python",
        template_id="web_app"
    )
    
    # Test 2: Remember agent interaction
    print("2. Storing agent interaction...")
    supervisor.remember_agent_interaction(
        agent_name="brd_generator",
        input_data="Create a todo list application",
        output_data="Generated BRD with 5 functional requirements",
        success=True,
        metadata={"tokens": 1500}
    )
    
    # Test 3: Get relevant context
    print("\n3. Retrieving relevant context...")
    context = supervisor.get_relevant_context("todo application")
    print(context)
    
    # Test 4: Get memory stats
    print("\n4. Memory statistics:")
    stats = supervisor.get_memory_stats()
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   Agents: {stats['agents']}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_memory_integration())
