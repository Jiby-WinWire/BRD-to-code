"""Memory Manager for BRD to JIRA Agent

Manages state persistence and caching for JIRA ticket generation.
Uses Redis for session state and caching of conversions.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field
from redis import StrictRedis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis key prefix
REDIS_KEY_PREFIX = "jira_conversion:"


class JiraAgentStatus(BaseModel):
    """Pydantic model for JIRA conversion agent status tracking"""
    
    status: str = Field(
        default="initialized",
        description="Current status: initialized, processing, completed, failed"
    )
    task_id: str = Field(
        description="Unique task identifier"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="User session identifier"
    )
    brd_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Input BRD in JSON format"
    )
    jira_tickets: Optional[list[Dict[str, Any]]] = Field(
        default=None,
        description="Generated JIRA tickets"
    )
    conversion_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conversion metadata"
    )
    
    # Timing
    start_time: Optional[str] = Field(
        default=None,
        description="When the task started (ISO format)"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="When the task ended (ISO format)"
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duration in seconds"
    )
    
    # Token tracking
    input_tokens: int = Field(default=0, description="Tokens used in input")
    output_tokens: int = Field(default=0, description="Tokens used in output")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    
    # Error tracking
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if conversion failed"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JiraMemoryManager:
    """Memory Manager for BRD to JIRA Agent
    
    Manages:
    - Task status persistence in Redis
    - Conversion result caching
    - Session state management
    """
    
    def __init__(
        self,
        redis_client: StrictRedis,
        enable_caching: bool = True,
        ttl_seconds: int = 86400  # 24 hours
    ):
        """Initialize JIRA Memory Manager
        
        Args:
            redis_client: Redis client instance
            enable_caching: Enable conversion result caching
            ttl_seconds: Time-to-live for cached items (default: 24 hours)
        """
        self.redis_client = redis_client
        self.enable_caching = enable_caching
        self.ttl_seconds = ttl_seconds
        logger.info(f"JIRA Memory Manager initialized (caching: {enable_caching})")
    
    async def push_jira_status(self, task_id: str, status: JiraAgentStatus) -> bool:
        """Store task status in Redis
        
        Args:
            task_id: Unique task identifier
            status: JiraAgentStatus to persist
            
        Returns:
            True if succeeded
        """
        try:
            key = f"{REDIS_KEY_PREFIX}status:{task_id}"
            value = status.json()
            self.redis_client.setex(key, self.ttl_seconds, value)
            logger.info(f"Stored status for task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to push status: {str(e)}")
            return False
    
    async def pull_jira_status(self, task_id: str) -> Optional[JiraAgentStatus]:
        """Retrieve task status from Redis
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            JiraAgentStatus if found, None otherwise
        """
        try:
            key = f"{REDIS_KEY_PREFIX}status:{task_id}"
            value = self.redis_client.get(key)
            if value:
                return JiraAgentStatus.parse_raw(value)
            return None
        except Exception as e:
            logger.error(f"Failed to pull status: {str(e)}")
            return None
    
    async def cache_conversion(self, cache_key: str, conversion_data: Dict[str, Any]) -> bool:
        """Cache conversion result
        
        Args:
            cache_key: Cache key (e.g., "brd_to_jira:task-123")
            conversion_data: Conversion result to cache
            
        Returns:
            True if succeeded
        """
        if not self.enable_caching:
            return False
        
        try:
            key = f"{REDIS_KEY_PREFIX}cache:{cache_key}"
            value = json.dumps(conversion_data)
            self.redis_client.setex(key, self.ttl_seconds, value)
            logger.info(f"Cached conversion: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache conversion: {str(e)}")
            return False
    
    async def get_cached_conversion(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached conversion result
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached conversion data if found, None otherwise
        """
        if not self.enable_caching:
            return None
        
        try:
            key = f"{REDIS_KEY_PREFIX}cache:{cache_key}"
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached conversion: {str(e)}")
            return None
    
    async def clear_task_data(self, task_id: str) -> bool:
        """Clear all data for a task
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            True if succeeded
        """
        try:
            status_key = f"{REDIS_KEY_PREFIX}status:{task_id}"
            self.redis_client.delete(status_key)
            logger.info(f"Cleared task data: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear task data: {str(e)}")
            return False
    
    async def get_session_tasks(self, session_id: str) -> list[str]:
        """Get all task IDs for a session
        
        Args:
            session_id: User session identifier
            
        Returns:
            List of task IDs
        """
        try:
            pattern = f"{REDIS_KEY_PREFIX}status:*"
            keys = self.redis_client.keys(pattern)
            task_ids = []
            
            for key in keys:
                value = self.redis_client.get(key)
                if value:
                    status = JiraAgentStatus.parse_raw(value)
                    if status.session_id == session_id:
                        task_ids.append(status.task_id)
            
            return task_ids
        except Exception as e:
            logger.error(f"Failed to get session tasks: {str(e)}")
            return []
