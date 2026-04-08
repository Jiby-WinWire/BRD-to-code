"""Memory Manager for BRD Generator Agent

Manages state persistence, caching, and semantic search for BRD generation.
Uses Redis for session state and Azure Search for BRD template caching.
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
REDIS_KEY_PREFIX = "brd:"


class BRDAgentStatus(BaseModel):
    """Pydantic model for BRD Generator agent status tracking"""
    
    status: str = Field(
        default="initialized",
        description="Current status: initialized, processing, completed, failed"
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="Original user prompt/requirement"
    )
    brd_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Generated BRD in JSON format"
    )
    brd_markdown: Optional[str] = Field(
        default=None,
        description="Generated BRD in markdown format"
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


class BRDRedisDataManager:
    """Redis data manager for BRD agent state"""
    
    def __init__(self, redis_client: StrictRedis):
        self.redis_client = redis_client
        logger.info("BRDRedisDataManager initialized")
    
    def save_brd_status(self, task_id: str, status: BRDAgentStatus) -> bool:
        """Save BRD status to Redis"""
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = status.model_dump_json()
            self.redis_client.setex(
                name=key,
                time=86400,  # 24 hours TTL
                value=value
            )
            logger.info(f"Saved BRD status for task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save BRD status: {str(e)}")
            return False
    
    def get_brd_status(self, task_id: str) -> Optional[BRDAgentStatus]:
        """Retrieve BRD status from Redis"""
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return BRDAgentStatus(**data)
            logger.warning(f"No BRD status found for task: {task_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get BRD status: {str(e)}")
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


class BRDMemoryManager:
    """Memory Manager for BRD Generator Agent
    
    Manages:
    - Redis state storage for active tasks
    - Azure Search semantic caching for BRD templates
    - Token tracking and performance metrics
    """
    
    def __init__(
        self,
        redis_client: StrictRedis,
        azure_search_endpoint: Optional[str] = None,
        azure_search_key: Optional[str] = None,
        azure_search_index: str = "brd-cache-index",
        azure_openai_endpoint: Optional[str] = None,
        azure_openai_key: Optional[str] = None,
        azure_openai_embedding_deployment: Optional[str] = None
    ):
        """Initialize BRD Memory Manager
        
        Args:
            redis_client: Redis client for state storage
            azure_search_endpoint: Azure Search service endpoint (optional for caching)
            azure_search_key: Azure Search API key
            azure_search_index: Index name for BRD cache
            azure_openai_endpoint: Azure OpenAI endpoint for embeddings
            azure_openai_key: Azure OpenAI API key
            azure_openai_embedding_deployment: Deployment name for embeddings
        """
        # Redis manager
        self.redis_manager = BRDRedisDataManager(redis_client)
        
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
    
    async def push_brd_status(self, task_id: str, status: BRDAgentStatus) -> bool:
        """Push BRD status to Redis"""
        return self.redis_manager.save_brd_status(task_id, status)
    
    async def pull_brd_status(self, task_id: str) -> Optional[BRDAgentStatus]:
        """Pull BRD status from Redis"""
        return self.redis_manager.get_brd_status(task_id)
    
    async def search_cached_brd(
        self, 
        user_prompt: str, 
        similarity_threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """Search for similar BRD in Azure Search cache
        
        Args:
            user_prompt: User's requirement prompt
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            Cached BRD dict with similarity score, or None
        """
        if not self.azure_search_client or not self.azure_openai_client:
            logger.info("Azure Search/OpenAI not configured - skipping cache check")
            return None
        
        try:
            # Generate embedding for user prompt
            embedding_response = self.azure_openai_client.embeddings.create(
                input=user_prompt,
                model=self.embedding_deployment
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Search Azure Search with vector similarity
            results = self.azure_search_client.search(
                search_text=None,
                vector_queries=[{
                    "kind": "vector",
                    "vector": query_embedding,
                    "fields": "prompt_embedding",
                    "k": 1
                }],
                select=["user_prompt", "brd_json", "brd_markdown"]
            )
            
            # Get top result
            for result in results:
                score = result.get("@search.score", 0.0)
                if score >= similarity_threshold:
                    logger.info(f"Cache hit with similarity: {score:.3f}")
                    return {
                        "brd_json": result.get("brd_json"),
                        "brd_markdown": result.get("brd_markdown"),
                        "similarity_score": score,
                        "cached_prompt": result.get("user_prompt")
                    }
            
            logger.info(f"No cache hit above threshold {similarity_threshold}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to search cache: {str(e)}")
            return None
    
    async def cache_brd(
        self, 
        user_prompt: str, 
        brd_json: Dict[str, Any],
        brd_markdown: str,
        task_id: str
    ) -> bool:
        """Cache BRD in Azure Search for future reuse
        
        Args:
            user_prompt: Original user prompt
            brd_json: Generated BRD JSON
            brd_markdown: Generated BRD markdown
            task_id: Task identifier
            
        Returns:
            True if cached successfully
        """
        if not self.azure_search_client or not self.azure_openai_client:
            logger.info("Azure Search/OpenAI not configured - skipping cache")
            return False
        
        try:
            # Generate embedding
            embedding_response = self.azure_openai_client.embeddings.create(
                input=user_prompt,
                model=self.embedding_deployment
            )
            prompt_embedding = embedding_response.data[0].embedding
            
            # Upload document to Azure Search
            document = {
                "id": task_id,
                "user_prompt": user_prompt,
                "brd_json": json.dumps(brd_json),
                "brd_markdown": brd_markdown,
                "prompt_embedding": prompt_embedding,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.azure_search_client.upload_documents(documents=[document])
            logger.info(f"Cached BRD for task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache BRD: {str(e)}")
            return False
    
    async def update_token_usage(
        self, 
        task_id: str, 
        input_tokens: int,
        output_tokens: int
    ) -> bool:
        """Update token usage for a task"""
        try:
            status = await self.pull_brd_status(task_id)
            if status:
                status.input_tokens += input_tokens
                status.output_tokens += output_tokens
                status.total_tokens = status.input_tokens + status.output_tokens
                return await self.push_brd_status(task_id, status)
            return False
        except Exception as e:
            logger.error(f"Failed to update token usage: {str(e)}")
            return False
