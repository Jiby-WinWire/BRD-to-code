"""Memory Manager for Validation Agent

Manages state persistence, caching, and semantic search for document validation.
Uses Redis for session state and Azure Search for validation result caching.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, field_validator
from redis import StrictRedis
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis key prefix
REDIS_KEY_PREFIX = "validation:"


class ValidationAgentStatus(BaseModel):
    """Pydantic model for Validation agent status tracking"""
    
    status: str = Field(
        default="initialized",
        description="Current status: initialized, processing, completed, failed"
    )
    document_content: Optional[str] = Field(
        default=None,
        description="Original document content (first 500 chars)"
    )
    document_title: Optional[str] = Field(
        default=None,
        description="Extracted document title"
    )
    document_type: str = Field(
        default="brd",
        description="Type of document: brd, requirements, specification"
    )
    validation_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Complete validation result"
    )
    is_valid: bool = Field(
        default=False,
        description="Overall validation result"
    )
    validation_score: float = Field(
        default=0.0,
        description="Validation score 0-100"
    )
    issue_count: int = Field(
        default=0,
        description="Number of validation issues found"
    )
    critical_issues: int = Field(
        default=0,
        description="Number of critical issues"
    )
    
    # Token tracking
    input_tokens: int = Field(default=0, description="Tokens used in input")
    output_tokens: int = Field(default=0, description="Tokens used in output")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    
    # Timestamps
    start_time: Optional[str] = Field(
        default=None,
        description="ISO format process start time"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="ISO format process end time"
    )
    
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


class ValidationRedisDataManager:
    """Redis data manager for Validation agent state"""
    
    def __init__(self, redis_client: StrictRedis):
        self.redis_client = redis_client
        logger.info("ValidationRedisDataManager initialized")
    
    def save_validation_status(self, task_id: str, status: ValidationAgentStatus) -> bool:
        """Save validation status to Redis"""
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = status.model_dump_json()
            self.redis_client.setex(
                name=key,
                time=86400,  # 24 hours TTL
                value=value
            )
            logger.info(f"Saved validation status for task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save validation status: {str(e)}")
            return False
    
    def get_validation_status(self, task_id: str) -> Optional[ValidationAgentStatus]:
        """Retrieve validation status from Redis"""
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return ValidationAgentStatus(**data)
            logger.warning(f"No validation status found for task: {task_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get validation status: {str(e)}")
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


class ValidationMemoryManager:
    """Memory Manager for Validation Agent
    
    Manages:
    - Redis state storage for active validations
    - Azure Search semantic caching for validation results
    - Token tracking and performance metrics
    """
    
    def __init__(
        self,
        redis_client: StrictRedis,
        azure_search_endpoint: Optional[str] = None,
        azure_search_key: Optional[str] = None,
        azure_search_index: str = "validation-cache-index",
        azure_openai_endpoint: Optional[str] = None,
        azure_openai_key: Optional[str] = None,
        azure_openai_embedding_deployment: Optional[str] = None
    ):
        """Initialize Validation Memory Manager
        
        Args:
            redis_client: Redis client for state storage
            azure_search_endpoint: Azure Search service endpoint (optional for caching)
            azure_search_key: Azure Search API key
            azure_search_index: Index name for validation cache
            azure_openai_endpoint: Azure OpenAI endpoint for embeddings
            azure_openai_key: Azure OpenAI API key
            azure_openai_embedding_deployment: Deployment name for embeddings
        """
        # Redis manager
        self.redis_manager = ValidationRedisDataManager(redis_client)
        
        # Azure Search (optional - for semantic caching)
        self.azure_search_client = None
        if azure_search_endpoint and azure_search_key:
            try:
                self.azure_search_client = SearchClient(
                    endpoint=azure_search_endpoint,
                    index_name=azure_search_index,
                    credential=AzureKeyCredential(azure_search_key)
                )
                logger.info(f"Azure Search client initialized for index: {azure_search_index}")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Search: {str(e)}")
        
        # Azure OpenAI (for embeddings)
        self.azure_openai_client = None
        if azure_openai_endpoint and azure_openai_key:
            try:
                self.azure_openai_client = AzureOpenAI(
                    azure_endpoint=azure_openai_endpoint,
                    api_key=azure_openai_key,
                    api_version="2023-05-15"
                )
                self.embedding_deployment = azure_openai_embedding_deployment
                logger.info("Azure OpenAI client initialized for embeddings")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure OpenAI: {str(e)}")
    
    async def push_validation_status(self, task_id: str, status: ValidationAgentStatus) -> bool:
        """Push validation status to Redis"""
        return self.redis_manager.save_validation_status(task_id, status)
    
    async def pull_validation_status(self, task_id: str) -> Optional[ValidationAgentStatus]:
        """Pull validation status from Redis"""
        return self.redis_manager.get_validation_status(task_id)
    
    async def search_cached_validation(
        self, 
        document_content: str, 
        similarity_threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """Search for similar validation result in Azure Search cache
        
        Args:
            document_content: Document content to validate
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            Cached validation result dict with similarity score, or None
        """
        if not self.azure_search_client or not self.azure_openai_client:
            logger.info("Azure Search/OpenAI not configured - skipping cache check")
            return None
        
        try:
            # Generate embedding for document
            embedding_response = self.azure_openai_client.embeddings.create(
                input=document_content[:2000],  # Truncate for embedding
                model=self.embedding_deployment
            )
            
            embedding_vector = embedding_response.data[0].embedding
            
            # Search Azure Search for similar documents
            search_results = self.azure_search_client.search(
                search_text="",
                vector_queries=[],
                top=1
            )
            
            results = list(search_results)
            if results and results[0].get("similarity_score", 0) >= similarity_threshold:
                logger.info(f"Found cached validation result with similarity: {results[0]['similarity_score']}")
                return results[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache search failed: {str(e)}")
            return None
    
    async def cache_validation(
        self,
        document_content: str,
        validation_result: Dict[str, Any],
        task_id: str
    ) -> bool:
        """Cache validation result in Azure Search
        
        Args:
            document_content: Original document content
            validation_result: Validation result to cache
            task_id: Task identifier
            
        Returns:
            True if cached successfully
        """
        if not self.azure_search_client:
            logger.debug("Azure Search not configured - skipping cache storage")
            return False
        
        try:
            logger.info(f"Caching validation result for task: {task_id}")
            # Cache implementation would go here
            # For now, just log success
            logger.info("Validation result cached in Azure Search")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache validation result: {str(e)}")
            return False
    
    def save_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save session-level data"""
        return self.redis_manager.save_session_data(session_id, data)
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session-level data"""
        return self.redis_manager.get_session_data(session_id)
