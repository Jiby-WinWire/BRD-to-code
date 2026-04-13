"""BRD to JIRA Agent - Simplified Standalone Version

Converts Business Requirements Documents to JIRA tickets without external agent base dependencies.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

try:
    from redis import StrictRedis
except ImportError:
    raise ImportError("redis package required - install with: pip install redis")

from langchain_openai import AzureChatOpenAI
from src.agents.brd_to_jira.jira_memory_manager import JiraAgentStatus, JiraMemoryManager
from src.agents.brd_to_jira.brd_to_jira_tool import create_brd_to_jira_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BRDToJiraAgent:
    """Simplified BRD to JIRA Agent
    
    Converts Business Requirements Documents to structured JIRA tickets
    without depending on external AgentClass framework.
    """
    
    def __init__(
        self,
        session_id: str,
        redis_url: str,
        azure_openai_endpoint: str,
        azure_openai_key: str,
        azure_openai_deployment: str,
        azure_openai_api_version: str = "2023-05-15",
        jira_server_url: str = "http://localhost:8080",
        jira_username: Optional[str] = None,
        jira_api_token: Optional[str] = None,
        jira_project_key: str = "PROJ",
        agent_url: str = "http://localhost:8002",
        enable_caching: bool = True
    ):
        """Initialize BRD to JIRA Agent
        
        Args:
            session_id: User session identifier
            redis_url: Redis connection URL
            azure_openai_endpoint: Azure OpenAI endpoint
            azure_openai_key: Azure OpenAI API key
            azure_openai_deployment: Model deployment name
            azure_openai_api_version: API version
            jira_server_url: JIRA server URL
            jira_username: JIRA username (optional)
            jira_api_token: JIRA API token (optional)
            jira_project_key: JIRA project key
            agent_url: This agent's URL
            enable_caching: Enable caching
        """
        self.session_id = session_id
        self.agent_name = "brd-to-jira"
        self.deployment_name = azure_openai_deployment
        self.agent_url = agent_url
        self.jira_config = {
            'server_url': jira_server_url,
            'username': jira_username,
            'api_token': jira_api_token,
            'project_key': jira_project_key
        }
        
        logger.info(f"Initializing BRD to JIRA Agent for session: {session_id}")
        
        # 1. Initialize Redis
        self.redis_client = self._init_redis(redis_url)
        
        # 2. Initialize Azure OpenAI LLM
        self.llm = AzureChatOpenAI(
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            api_version=azure_openai_api_version,
            azure_deployment=azure_openai_deployment,
            temperature=0.2
        )
        
        # 3. Initialize Memory Manager
        self.memory_manager = JiraMemoryManager(
            redis_client=self.redis_client,
            enable_caching=enable_caching
        )
        logger.info("Memory Manager initialized")
        
        # 4. Create BRD to JIRA conversion tool
        self.jira_tool = create_brd_to_jira_tool(
            llm=self.llm,
            deployment_name=self.deployment_name,
            memory_manager=self.memory_manager,
            jira_config=self.jira_config
        )
        
        logger.info("BRD to JIRA Agent fully initialized")
    
    def _init_redis(self, redis_url: str) -> Optional[StrictRedis]:
        """Initialize Redis client - uses real Redis, no FakeRedis fallback"""
        if StrictRedis is None:
            logger.error("redis module not available - please install redis")
            raise ImportError("redis package required")
        
        try:
            client = StrictRedis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info(f"✅ Connected to Redis server at: {redis_url}")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis at {redis_url}: {str(e)}")
            raise ConnectionError(f"Cannot connect to Redis: {str(e)}")
    
    async def convert_brd_to_jira(
        self,
        brd_json: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert BRD to JIRA tickets
        
        Args:
            brd_json: BRD in JSON format
            task_id: Task identifier for tracking
            
        Returns:
            Dict with converted JIRA tickets
        """
        task_id = task_id or str(uuid4())
        logger.info(f"Converting BRD to JIRA (task: {task_id})")
        
        try:
            # Initialize task status
            status = JiraAgentStatus(
                status="processing",
                task_id=task_id,
                session_id=self.session_id,
                start_time=datetime.utcnow().isoformat()
            )
            await self.memory_manager.push_jira_status(task_id, status)
            
            # Call the tool (which handles LLM invocation)
            # LangChain StructuredTool requires .ainvoke() for async functions
            result = await self.jira_tool.ainvoke({
                "brd_json": brd_json,
                "project_key": self.jira_config['project_key']
            })
            
            # Update status
            status.status = "completed"
            status.jira_tickets = result.get("jira_tickets", [])
            status.conversion_metadata = result.get("metadata")
            status.end_time = datetime.utcnow().isoformat()
            await self.memory_manager.push_jira_status(task_id, status)
            
            logger.info(f"✅ BRD conversion completed for task: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Conversion failed: {str(e)}", exc_info=True)
            
            # Update error status
            status = await self.memory_manager.pull_jira_status(task_id)
            if status:
                status.status = "failed"
                status.error_message = str(e)
                status.end_time = datetime.utcnow().isoformat()
                await self.memory_manager.push_jira_status(task_id, status)
            
            raise
