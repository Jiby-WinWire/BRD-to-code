"""BRD to JIRA Agent

Enterprise-grade agent for converting Business Requirements Documents to JIRA tickets.
Extends AgentClass from agent_base with memory management and A2A protocol support.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from redis import StrictRedis
from langchain_openai import AzureChatOpenAI

# Import from official a2a SDK
from a2a.types import Task, TaskStatus, Message, TextPart

# Import agent base components
from agent_base.agent import AgentClass
from agent_base import InMemoryTaskManager, SendTaskRequest, SendTaskResponse
from src.agents.brd_to_jira.jira_memory_manager import JiraAgentStatus, JiraMemoryManager
from src.agents.brd_to_jira.brd_to_jira_tool import create_brd_to_jira_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JiraTaskManager(InMemoryTaskManager):
    """Custom task manager for BRD to JIRA agent
    
    Handles A2A protocol SendTaskRequest and manages task lifecycle
    """
    
    def __init__(self, agent: 'BRDToJiraAgent'):
        super().__init__()
        self.agent = agent
        logger.info("JiraTaskManager initialized")
    
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handle incoming A2A task request
        
        Args:
            request: SendTaskRequest with BRD data
            
        Returns:
            SendTaskResponse with JIRA conversion result
        """
        logger.info(f"Received SendTaskRequest: {request.id}")
        task_id = request.id or str(uuid4())
        
        try:
            # Extract BRD data from message
            brd_json = None
            if request.params and request.params.message:
                for part in request.params.message.parts:
                    if isinstance(part, TextPart):
                        # Try to parse as JSON
                        try:
                            brd_json = json.loads(part.text)
                        except json.JSONDecodeError:
                            # If not JSON, treat as raw text
                            brd_json = {"raw_text": part.text}
                        break
            
            if not brd_json:
                raise ValueError("No BRD content found in request")
            
            logger.info(f"Processing BRD to JIRA conversion for task: {task_id}")
            
            # Initialize task status
            status = JiraAgentStatus(
                status="processing",
                task_id=task_id,
                session_id=self.agent.session_id,
                start_time=datetime.utcnow().isoformat()
            )
            await self.agent.memory_manager.push_jira_status(task_id, status)
            
            # Convert BRD to JIRA using agent
            result = await self.agent.convert_brd_to_jira(
                brd_json=brd_json,
                task_id=task_id
            )
            
            # Update status
            status.status = "completed"
            status.jira_tickets = result.get("jira_tickets", [])
            status.conversion_metadata = result.get("metadata")
            status.end_time = datetime.utcnow().isoformat()
            await self.agent.memory_manager.push_jira_status(task_id, status)
            
            logger.info(f"JIRA conversion completed for task: {task_id}")
            
            # Create response message
            tickets_summary = f"Generated {len(result.get('jira_tickets', []))} JIRA tickets"
            response_text = (
                f"BRD to JIRA Conversion Successful!\n\n"
                f"{tickets_summary}\n\n"
                f"{json.dumps(result.get('jira_tickets', []), indent=2)}"
            )
            
            task = Task(
                id=task_id,
                status=TaskStatus.COMPLETED,
                message=Message(parts=[TextPart(text=response_text)])
            )
            
            return SendTaskResponse(id=request.id, result=task)
            
        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}", exc_info=True)
            
            # Update error status
            status = await self.agent.memory_manager.pull_jira_status(task_id)
            if status:
                status.status = "failed"
                status.error_message = str(e)
                status.end_time = datetime.utcnow().isoformat()
                await self.agent.memory_manager.push_jira_status(task_id, status)
            
            # Return failed task
            task = Task(
                id=task_id,
                status=TaskStatus.FAILED,
                message=Message(parts=[TextPart(text=f"Error: {str(e)}")])
            )
            
            return SendTaskResponse(id=request.id, result=task)


class BRDToJiraAgent(AgentClass):
    """BRD to JIRA Agent extending AgentClass
    
    Converts comprehensive Business Requirements Documents to
    structured JIRA tickets with support for multiple project types.
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
        client_id: str = "brd-to-jira-client",
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
            client_id: Client identifier
            agent_url: This agent's URL
            enable_caching: Enable caching
        """
        self.session_id = session_id
        self.deployment_name = azure_openai_deployment
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
        jira_tool = create_brd_to_jira_tool(
            llm=self.llm,
            deployment_name=self.deployment_name,
            memory_manager=self.memory_manager,
            jira_config=self.jira_config
        )
        
        # 5. Initialize parent AgentClass
        config = {
            "deployment_name": azure_openai_deployment,
            "model_name": azure_openai_deployment,
            "model_version": azure_openai_api_version,
            "api_key": azure_openai_key,
            "api_version": azure_openai_api_version,
            "azure_endpoint": azure_openai_endpoint,
            "temperature": 0.2,
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": "brd_to_jira"
            }
        }
        
        super().__init__(
            agent_name="brd-to-jira",
            tools=[jira_tool],
            config=config,
            memory_backend=None,  # Using custom memory manager
            prompt=(
                "You are a BRD to JIRA conversion agent. "
                "Your role is to transform Business Requirements Documents into "
                "well-structured JIRA tickets with appropriate issue types, "
                "descriptions, acceptance criteria, and story points. "
                "Always use the convert_brd_to_jira tool to process requests."
            )
        )
        
        # 6. Initialize custom task manager
        self.task_manager = JiraTaskManager(self)
        logger.info("BRD to JIRA Agent fully initialized")
    
    def _init_redis(self, redis_url: str) -> StrictRedis:
        """Initialize Redis client (supports both real Redis and FakeRedis)"""
        try:
            import fakeredis
            if redis_url.startswith("fakeredis://"):
                logger.info("Using FakeRedis for development")
                return fakeredis.FakeStrictRedis(decode_responses=True)
        except ImportError:
            pass
        
        try:
            client = StrictRedis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("✅ Connected to Redis server")
            return client
        except Exception as e:
            logger.warning(f"⚠️  Failed to connect to Redis: {str(e)}")
            try:
                import fakeredis
                logger.info("🔄 Falling back to FakeRedis")
                return fakeredis.FakeStrictRedis(decode_responses=True)
            except ImportError:
                logger.error("FakeRedis not available. Install with: pip install fakeredis")
                raise
    
    async def generate_jira_tickets(
        self,
        brd_json: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate JIRA tickets from BRD
        
        Args:
            brd_json: BRD in JSON format
            task_id: Task identifier for tracking
            
        Returns:
            Dict with jira_tickets and metadata
        """
        logger.info(f"Generating JIRA tickets from BRD (task: {task_id})")
        # Implementation will be in the tool
        pass
    
    async def convert_brd_to_jira(
        self,
        brd_json: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Main conversion method
        
        Args:
            brd_json: BRD in JSON format
            task_id: Task identifier for tracking
            
        Returns:
            Dict with converted JIRA tickets
        """
        return await self.generate_jira_tickets(brd_json=brd_json, task_id=task_id)
