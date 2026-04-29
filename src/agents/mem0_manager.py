"""
Mem0 AI Memory Manager
Manages conversation memory across all agents using mem0ai
Stores user preferences, conversation history, and agent context
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from mem0 import Memory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Mem0Manager:
    """
    Centralized memory manager for all agents using mem0ai.
    Handles conversation memory, user preferences, and context tracking.
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize mem0 manager with API key from environment
        
        Args:
            user_id: Optional user identifier for personalized memory
        """
        self.api_key = os.getenv("mem0_key")
        if not self.api_key:
            raise ValueError("mem0_key not found in environment variables")
        
        # Set the API key as environment variable (mem0 reads from MEM0_API_KEY)
        os.environ["MEM0_API_KEY"] = self.api_key
        
        # Get mem0 API key
        self.api_key = os.getenv("mem0_key")
        if not self.api_key:
            raise ValueError("mem0_key not found in environment variables")
        
        # Initialize mem0 using the hosted platform
        # According to mem0 docs, for hosted service use MemoryClient
        try:
            from mem0 import MemoryClient
            # MemoryClient is for mem0's hosted platform
            self.memory = MemoryClient(api_key=self.api_key)
            logger.info("Mem0Manager initialized using MemoryClient (hosted platform)")
        except ImportError:
            # Fallback: Try Memory class with API key in environment
            os.environ["MEM0_API_KEY"] = self.api_key
            self.memory = Memory()
            logger.info("Mem0Manager initialized using Memory class")
        
        self.user_id = user_id or "default_user"
        self.session_id = None
        
        logger.info(f"Mem0Manager initialized for user: {self.user_id}")
    
    def set_session(self, session_id: str):
        """Set the current session ID for memory tracking"""
        self.session_id = session_id
        logger.info(f"Session set: {session_id}")
    
    def add_conversation(
        self,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a conversation message to memory
        
        Args:
            role: Role of the speaker (user, assistant, agent)
            content: Message content
            agent_name: Name of the agent (if applicable)
            metadata: Additional metadata to store
            
        Returns:
            Dictionary with memory ID and success status
        """
        try:
            # Prepare the message with context
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name or "unknown",
                "session_id": self.session_id
            }
            
            # Add custom metadata
            if metadata:
                message.update(metadata)
            
            # Store in mem0
            result = self.memory.add(
                messages=[{
                    "role": role,
                    "content": content
                }],
                user_id=self.user_id,
                metadata={
                    "agent": agent_name,
                    "session_id": self.session_id,
                    "timestamp": message["timestamp"],
                    **(metadata or {})
                }
            )
            
            logger.info(f"Memory added: {role} - {agent_name}")
            return {
                "success": True,
                "memory_id": result.get("id") if isinstance(result, dict) else str(result),
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_relevant_memories(
        self,
        query: str,
        limit: int = 5,
        agent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories based on a query
        
        Args:
            query: Search query for semantic memory retrieval
            limit: Maximum number of memories to retrieve
            agent_filter: Filter memories by specific agent name
            
        Returns:
            List of relevant memory items
        """
        try:
            # Only use supported filters: user_id is the main one
            # Other filters like agent_filter and session_id will be applied post-retrieval
            filters = {
                "user_id": self.user_id
            }
            
            # Search memories using MemoryClient API
            # Retrieve more than needed to account for post-filtering
            search_limit = limit * 3 if (agent_filter or self.session_id) else limit
            
            memories = self.memory.search(
                query=query,
                filters=filters,
                limit=search_limit
            )
            
            # Extract and filter memory content
            results = []
            if isinstance(memories, list):
                for mem in memories:
                    if isinstance(mem, dict):
                        metadata = mem.get("metadata", {})
                        
                        # Apply custom filters (post-retrieval)
                        if agent_filter and metadata.get("agent") != agent_filter:
                            continue
                        if self.session_id and metadata.get("session_id") != self.session_id:
                            continue
                        
                        results.append({
                            "id": mem.get("id"),
                            "content": mem.get("memory", mem.get("content", "")),
                            "metadata": metadata,
                            "score": mem.get("score", 0.0)
                        })
                        
                        # Stop when we have enough results
                        if len(results) >= limit:
                            break
            
            logger.info(f"Retrieved {len(results)} relevant memories for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []
    
    def get_all_memories(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all memories for the current user
        
        Args:
            limit: Maximum number of memories to retrieve
            
        Returns:
            List of all memory items
        """
        try:
            # Use filters for MemoryClient API
            memories = self.memory.get_all(filters={"user_id": self.user_id})
            
            results = []
            if isinstance(memories, list):
                for mem in memories[:limit]:
                    if isinstance(mem, dict):
                        results.append({
                            "id": mem.get("id"),
                            "content": mem.get("memory", mem.get("content", "")),
                            "metadata": mem.get("metadata", {}),
                            "created_at": mem.get("created_at", "")
                        })
            
            logger.info(f"Retrieved {len(results)} total memories")
            return results
            
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            return []
    
    def store_user_preference(
        self,
        preference_key: str,
        preference_value: Any
    ) -> Dict[str, Any]:
        """
        Store a user preference in memory
        
        Args:
            preference_key: Key for the preference
            preference_value: Value of the preference
            
        Returns:
            Dictionary with success status
        """
        preference_text = f"User preference: {preference_key} = {preference_value}"
        
        return self.add_conversation(
            role="system",
            content=preference_text,
            agent_name="preference_manager",
            metadata={
                "type": "user_preference",
                "key": preference_key,
                "value": str(preference_value)
            }
        )
    
    def store_agent_output(
        self,
        agent_name: str,
        input_data: str,
        output_data: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store agent input/output for future reference
        
        Args:
            agent_name: Name of the agent
            input_data: Input provided to the agent
            output_data: Output generated by the agent
            metadata: Additional metadata
            
        Returns:
            Dictionary with success status
        """
        content = f"""Agent: {agent_name}
Input: {input_data[:500]}...
Output: {output_data[:500]}..."""
        
        return self.add_conversation(
            role="assistant",
            content=content,
            agent_name=agent_name,
            metadata={
                "type": "agent_output",
                "input_length": len(input_data),
                "output_length": len(output_data),
                **(metadata or {})
            }
        )
    
    def get_conversation_history(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history
        
        Args:
            limit: Number of recent messages to retrieve
            
        Returns:
            List of conversation messages
        """
        try:
            # Use filters for MemoryClient API
            memories = self.memory.get_all(filters={"user_id": self.user_id})
            
            # Filter to conversation messages only
            conversations = []
            if isinstance(memories, list):
                for mem in memories:
                    if isinstance(mem, dict):
                        metadata = mem.get("metadata", {})
                        if metadata.get("session_id") == self.session_id:
                            conversations.append({
                                "content": mem.get("memory", mem.get("content", "")),
                                "metadata": metadata,
                                "timestamp": metadata.get("timestamp", "")
                            })
            
            # Sort by timestamp and limit
            conversations.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            
            return conversations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def clear_session_memory(self) -> Dict[str, Any]:
        """
        Clear memories for the current session
        Note: mem0 doesn't support selective deletion by metadata,
        so this method logs the intent but may require manual cleanup
        
        Returns:
            Dictionary with status
        """
        logger.warning(f"Session memory clear requested for: {self.session_id}")
        logger.warning("Note: Mem0 may not support selective deletion. Consider using new user_id for new sessions.")
        
        return {
            "success": True,
            "message": "Session memory clear logged. Use new user_id for complete isolation."
        }
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete a specific memory by ID
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            Dictionary with success status
        """
        try:
            self.memory.delete(memory_id=memory_id)
            logger.info(f"Memory deleted: {memory_id}")
            
            return {
                "success": True,
                "memory_id": memory_id
            }
            
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def build_context_prompt(
        self,
        current_input: str,
        memory_limit: int = 5
    ) -> str:
        """
        Build an enhanced prompt with relevant memory context
        
        Args:
            current_input: The current user input/query
            memory_limit: Number of relevant memories to include
            
        Returns:
            Enhanced prompt with memory context
        """
        # Get relevant memories
        relevant_memories = self.get_relevant_memories(
            query=current_input,
            limit=memory_limit
        )
        
        if not relevant_memories:
            return current_input
        
        # Build context section
        context_parts = ["### Relevant Context from Previous Conversations:"]
        
        for i, mem in enumerate(relevant_memories, 1):
            content = mem.get("content", "")
            score = mem.get("score", 0.0)
            context_parts.append(f"{i}. {content} (relevance: {score:.2f})")
        
        context_parts.append("\n### Current Request:")
        context_parts.append(current_input)
        
        return "\n".join(context_parts)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored memories
        
        Returns:
            Dictionary with memory statistics
        """
        try:
            all_memories = self.get_all_memories()
            
            stats = {
                "total_memories": len(all_memories),
                "user_id": self.user_id,
                "session_id": self.session_id,
                "agents": set(),
                "memory_types": {}
            }
            
            for mem in all_memories:
                metadata = mem.get("metadata", {})
                agent = metadata.get("agent")
                mem_type = metadata.get("type", "conversation")
                
                if agent:
                    stats["agents"].add(agent)
                
                stats["memory_types"][mem_type] = stats["memory_types"].get(mem_type, 0) + 1
            
            stats["agents"] = list(stats["agents"])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {
                "total_memories": 0,
                "error": str(e)
            }
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """
        Get user preferences from stored memories
        
        Returns:
            Dictionary of user preferences
        """
        try:
            # Search for preference-related memories
            preference_memories = self.get_relevant_memories(
                query="user preference programming language framework style",
                limit=20
            )
            
            preferences = {}
            
            for mem in preference_memories:
                metadata = mem.get("metadata", {})
                if metadata.get("type") == "user_preference":
                    pref_key = metadata.get("preference_key")
                    pref_value = metadata.get("preference_value")
                    if pref_key and pref_value:
                        preferences[pref_key] = pref_value
                        
                # Extract preferences from conversation content
                content = mem.get("content", "")
                if "prefer" in content.lower():
                    # Simple preference extraction (can be enhanced with NLP)
                    if "python" in content.lower():
                        preferences["language"] = "Python"
                    elif "javascript" in content.lower():
                        preferences["language"] = "JavaScript"
                    elif "react" in content.lower():
                        preferences["framework"] = "React"
                    elif "flask" in content.lower():
                        preferences["framework"] = "Flask"
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}


# Utility functions for quick access

def create_memory_manager(user_id: Optional[str] = None, session_id: Optional[str] = None) -> Mem0Manager:
    """
    Factory function to create a configured Mem0Manager instance
    
    Args:
        user_id: Optional user identifier
        session_id: Optional session identifier
        
    Returns:
        Configured Mem0Manager instance
    """
    manager = Mem0Manager(user_id=user_id)
    if session_id:
        manager.set_session(session_id)
    return manager


if __name__ == "__main__":
    # Example usage and testing
    print("=== Mem0 Manager Test ===\n")
    
    # Create manager
    manager = create_memory_manager(
        user_id="test_user",
        session_id="test_session_001"
    )
    
    # Add some test conversations
    print("1. Adding conversations...")
    manager.add_conversation(
        role="user",
        content="I want to create a todo list application",
        agent_name="brd_generator"
    )
    
    manager.add_conversation(
        role="assistant",
        content="I'll help you create a BRD for a todo list application with CRUD operations",
        agent_name="brd_generator"
    )
    
    # Store a preference
    print("\n2. Storing user preference...")
    manager.store_user_preference("preferred_language", "python")
    
    # Search for relevant memories
    print("\n3. Searching for relevant memories...")
    memories = manager.get_relevant_memories(
        query="todo application requirements",
        limit=3
    )
    
    for mem in memories:
        print(f"  - {mem['content'][:100]}...")
    
    # Get statistics
    print("\n4. Memory statistics:")
    stats = manager.get_memory_stats()
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Agents involved: {stats['agents']}")
    print(f"  Memory types: {stats['memory_types']}")
    
    print("\n=== Test Complete ===")
