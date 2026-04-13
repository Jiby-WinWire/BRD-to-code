"""Memory Manager for CodeToTest Agent

Manages task status persistence and optional Redis-backed state storage.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator
from redis import StrictRedis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "code_to_test:"


class CodeToTestAgentStatus(BaseModel):
    """Pydantic status model for CodeToTest tasks."""

    status: str = Field(
        default="initialized",
        description="Current status: initialized, processing, completed, failed"
    )
    stories: Optional[Any] = Field(
        default=None,
        description="Input stories payload for code generation"
    )
    code_files: Optional[Dict[str, str]] = Field(
        default=None,
        description="Generated code file contents indexed by path"
    )
    test_files: Optional[Dict[str, str]] = Field(
        default=None,
        description="Generated pytest test file contents indexed by path"
    )
    note: Optional[str] = Field(
        default=None,
        description="Optional result note"
    )
    input_tokens: int = Field(default=0, description="Tokens used in input")
    output_tokens: int = Field(default=0, description="Tokens used in output")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    start_time: Optional[str] = Field(
        default=None,
        description="ISO format process start time"
    )
    end_time: Optional[str] = Field(
        default=None,
        description="ISO format process end time"
    )
    task_id: Optional[str] = Field(
        default=None,
        description="A2A task identifier"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="User session identifier"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )

    @field_validator('status')
    def validate_status(cls, value):
        allowed_statuses = ['initialized', 'processing', 'completed', 'failed']
        if value not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return value


class CodeToTestRedisDataManager:
    """Redis data manager for CodeToTest task state."""

    def __init__(self, redis_client: StrictRedis):
        self.redis_client = redis_client
        logger.info("CodeToTestRedisDataManager initialized")

    def save_task_status(self, task_id: str, status: CodeToTestAgentStatus) -> bool:
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = status.model_dump_json()
            self.redis_client.setex(name=key, time=86400, value=value)
            logger.info(f"Saved CodeToTest task status for task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save CodeToTest task status: {str(e)}")
            return False

    def get_task_status(self, task_id: str) -> Optional[CodeToTestAgentStatus]:
        try:
            key = f"{REDIS_KEY_PREFIX}task:{task_id}"
            value = self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return CodeToTestAgentStatus(**data)
            logger.warning(f"No CodeToTest task status found for task: {task_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get CodeToTest task status: {str(e)}")
            return None


class CodeToTestMemoryManager:
    """Memory manager for CodeToTest Agent state and task tracking."""

    def __init__(self, redis_client: StrictRedis):
        self.redis_manager = CodeToTestRedisDataManager(redis_client)
        logger.info("CodeToTestMemoryManager initialized")

    async def push_task_status(self, task_id: str, status: CodeToTestAgentStatus) -> bool:
        return self.redis_manager.save_task_status(task_id, status)

    async def pull_task_status(self, task_id: str) -> Optional[CodeToTestAgentStatus]:
        return self.redis_manager.get_task_status(task_id)
