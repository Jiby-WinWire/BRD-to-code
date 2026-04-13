"""Memory Manager for Jira To Code Agent

Manages state persistence, caching, and semantic search for code generation.
Uses Redis for session state.
"""

import json
import logging
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator
from redis import StrictRedis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis key prefix
REDIS_KEY_PREFIX = "jira:"


class JiraToCodeStatus(BaseModel):
    """Pydantic model for Jira To Code agent status tracking"""
    
    status: str = Field(
        default="initialized",
        description="Current status: initialized, processing, completed, failed"
    )
    issue_text: Optional[str] = Field(
        default=None,
        description="Original Jira issue text"
    )
    code_snippet: Optional[str] = Field(
        default=None,
        description="Generated code snippet"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation of generated code"
    )
    
    # Token tracking
    input_tokens: int = Field(default=0, description="Tokens used in input")
    output_tokens: int = Field(default=0, description="Tokens used in output")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    
    # Metadata
    task_id: Optional[str] = Field(
        default=None,
        description="A2A task identifier"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="User session identifier"
    )
    cache_hit: bool = Field(
        default=False,
        description="Whether result was retrieved from cache"
    )
    similarity_score: float = Field(
        default=0.0,
        description="Semantic similarity score if cached"
    )
    
    # Error tracking
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is failed"
    )
    
    @field_validator('status')
    def validate_status(cls, v):
        """Validate status values"""
        allowed_statuses = ['initialized', 'processing', 'completed', 'failed']
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return v


class JiraRedisDataManager:
    """Redis data manager for Jira To Code agent state"""
    
    def __init__(self, redis_client: StrictRedis):
        self.redis_client = redis_client
        logger.info("JiraRedisDataManager initialized")
    
    def save_jira_status(self, task_id: str, status: JiraToCodeStatus) -> bool:
        """Save Jira status to Redis"""
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = status.model_dump_json()
            self.redis_client.setex(
                name=key,
                time=86400,  # 24 hours TTL
                value=value
            )
            logger.info(f"Saved Jira status for task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save Jira status: {str(e)}")
            return False
    
    def get_jira_status(self, task_id: str) -> Optional[JiraToCodeStatus]:
        """Retrieve Jira status from Redis"""
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return JiraToCodeStatus(**data)
            logger.warning(f"No Jira status found for task: {task_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get Jira status: {str(e)}")
            return None
    
    def save_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save session-level data"""
        try:
            key = f"{REDIS_KEY_PREFIX}session:{session_id}"
            value = json.dumps(data)
            self.redis_client.setex(
                name=key,
                time=3600,  # 1 hour TTL
                value=value
            )
            logger.info(f"Saved session data for: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session data: {str(e)}")
            return False
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session-level data"""
        try:
            key = f"{REDIS_KEY_PREFIX}session:{session_id}"
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get session data: {str(e)}")
            return None


class JiraMemoryManager:
    """Memory Manager for Jira To Code Agent
    
    Manages:
    - Redis state storage for active tasks
    - Simple in-memory caching for recently generated code
    """
    
    def __init__(self, redis_client: StrictRedis):
        """Initialize Jira Memory Manager
        
        Args:
            redis_client: Redis client for state storage
        """
        # Redis manager
        self.redis_manager = JiraRedisDataManager(redis_client)
        
        # Simple in-memory cache for recent generations
        self._code_cache = {}
        logger.info("Jira Memory Manager initialized")
    
    async def push_jira_status(self, task_id: str, status: JiraToCodeStatus) -> bool:
        """Push Jira status to Redis"""
        return self.redis_manager.save_jira_status(task_id, status)
    
    async def pull_jira_status(self, task_id: str) -> Optional[JiraToCodeStatus]:
        """Pull Jira status from Redis"""
        return self.redis_manager.get_jira_status(task_id)
    
    async def search_cached_code(
        self, 
        issue_text: str, 
        similarity_threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """Search for similar code in cache
        
        Args:
            issue_text: Issue text to search for
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            Cached code dict with similarity score, or None
        """
        logger.info(f"Searching cache for similar issue (threshold: {similarity_threshold})")
        
        # Simple substring matching fallback
        # In production, this would use semantic search via embeddings
        for cached_issue, cached_code in self._code_cache.items():
            # Very basic similarity check
            if issue_text.lower() in cached_issue.lower() or cached_issue.lower() in issue_text.lower():
                logger.info("Found similar cached code")
                return {
                    "code_snippet": cached_code.get("code_snippet"),
                    "explanation": cached_code.get("explanation", ""),
                    "similarity_score": 0.9
                }
        
        logger.info(f"No cache hit above threshold {similarity_threshold}")
        return None
    
    async def cache_code(
        self, 
        issue_text: str, 
        code_snippet: str,
        explanation: str,
        task_id: str
    ) -> bool:
        """Cache generated code for future reuse
        
        Args:
            issue_text: Original issue text
            code_snippet: Generated code
            explanation: Code explanation
            task_id: Task identifier
            
        Returns:
            True if cached successfully
        """
        try:
            # Keep last 100 entries in memory
            if len(self._code_cache) >= 100:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self._code_cache))
                del self._code_cache[oldest_key]
            
            self._code_cache[issue_text[:200]] = {
                "code_snippet": code_snippet,
                "explanation": explanation,
                "task_id": task_id
            }
            
            logger.info(f"Cached code for task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache code: {str(e)}")
            return False
    
    async def update_token_usage(
        self, 
        task_id: str, 
        input_tokens: int,
        output_tokens: int
    ) -> bool:
        """Update token usage for a task"""
        try:
            status = await self.pull_jira_status(task_id)
            if status:
                status.input_tokens += input_tokens
                status.output_tokens += output_tokens
                status.total_tokens = status.input_tokens + status.output_tokens
                return await self.push_jira_status(task_id, status)
            return False
        except Exception as e:
            logger.error(f"Failed to update token usage: {str(e)}")
            return False

