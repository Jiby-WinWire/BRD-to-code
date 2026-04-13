"""BRD Generator Agent

Enterprise-grade agent for generating Business Requirements Documents.
Extends AgentClass from agent_base with memory management, policy controls,
and A2A protocol support.
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

# Import agent base components and compatibility layer
from agent_base.agent import AgentClass
from agent_base import InMemoryTaskManager, SendTaskRequest, SendTaskResponse
from src.agents.brd_generator.memory_manager import BRDMemoryManager, BRDAgentStatus
from src.agents.brd_generator.policy_manager import PolicyManager
from src.agents.brd_generator.brd_generator_tool import create_brd_generation_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BRDTaskManager(InMemoryTaskManager):
    """Custom task manager for BRD Generator agent
    
    Handles A2A protocol SendTaskRequest and manages task lifecycle
    """
    
    def __init__(self, agent: 'BRDGeneratorAgent'):
        super().__init__()
        self.agent = agent
        logger.info("BRDTaskManager initialized")
    
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handle incoming A2A task request
        
        Args:
            request: SendTaskRequest with user query
            
        Returns:
            SendTaskResponse with generated BRD
        """
        logger.info(f"Received SendTaskRequest: {request.id}")
        task_id = request.id or str(uuid4())
        # Safely get context_id from params, generate if not present
        context_id = getattr(request.params, 'context_id', None) or str(uuid4())
        
        try:
            # Extract user query from message - handle dict and object formats
            user_query = None
            if request.params and request.params.message:
                parts = request.params.message.parts if hasattr(request.params.message, 'parts') else []
                
                if parts:
                    first_part = parts[0]
                    if isinstance(first_part, dict):
                        # Dictionary format: {'kind': 'text', 'text': '...'}
                        user_query = first_part.get('text', '')
                    elif hasattr(first_part, 'root'):
                        # A2A SDK Part object with root.text structure
                        if hasattr(first_part.root, 'text'):
                            user_query = first_part.root.text
                    elif hasattr(first_part, 'text'):
                        # Direct object format with .text attribute
                        user_query = first_part.text
            
            if not user_query:
                raise ValueError("No text content found in request")
            
            logger.info(f"Processing BRD generation for: {user_query[:100]}...")
            
            # Initialize task status
            status = BRDAgentStatus(
                status="processing",
                user_prompt=user_query,
                task_id=task_id,
                session_id=self.agent.session_id,
                start_time=datetime.utcnow().isoformat()
            )
            await self.agent.memory_manager.push_brd_status(task_id, status)
            
            # Policy validation
            if self.agent.policy_manager:
                logger.info("Validating policies...")
                policy_result = self.agent.policy_manager.validate_all_policies(
                    session_id=self.agent.session_id,
                    task_data={"query": user_query},
                    resources=["azure_openai", "redis_cache"],
                    task_type="brd_generation"
                )
                
                if not policy_result.all_passed:
                    error_msg = (
                        f"Policy validation failed: "
                        f"agent={policy_result.agent_policy}, "
                        f"resource={policy_result.resource_policy}, "
                        f"task={policy_result.task_policy}"
                    )
                    logger.error(error_msg)
                    status.status = "failed"
                    status.error_message = error_msg
                    await self.agent.memory_manager.push_brd_status(task_id, status)
                    
                    # Return failed task
                    task = Task(
                        id=task_id,
                        context_id=context_id,
                        status=TaskStatus(
                            state="failed",
                            message=Message(
                                message_id=str(uuid4()),
                                role="agent",
                                parts=[TextPart(text=error_msg)]
                            )
                        )
                    )
                    return SendTaskResponse(id=request.id, result=task)
            
            # Generate BRD using agent
            result = await self.agent.generate_brd(
                user_prompt=user_query,
                task_id=task_id
            )
            
            # Update status
            status.status = "completed"
            status.brd_json = result["brd_json"]
            status.brd_markdown = result.get("brd_markdown")
            status.cache_hit = result.get("from_cache", False)
            status.end_time = datetime.utcnow().isoformat()
            await self.agent.memory_manager.push_brd_status(task_id, status)
            
            logger.info(f"BRD generation completed for task: {task_id}")
            
            # Create response message
            response_text = (
                f"BRD Generated Successfully!\n\n"
                f"Title: {result['brd_json'].get('title', 'N/A')}\n"
                f"From Cache: {result.get('from_cache', False)}\n\n"
                f"{result.get('brd_markdown', json.dumps(result['brd_json'], indent=2))}"
            )
            
            task = Task(
         id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state="completed",
                    message=Message(
                        message_id=str(uuid4()),
                        role="agent",
                        parts=[TextPart(text=response_text)]
                    )
                )
            )
            
            return SendTaskResponse(id=request.id, result=task)
            
        except Exception as e:
            logger.error(f"Task processing failed: {str(e)}", exc_info=True)
            
            # Update error status
            status = await self.agent.memory_manager.pull_brd_status(task_id)
            if status:
                status.status = "failed"
                status.error_message = str(e)
                status.end_time = datetime.utcnow().isoformat()
                await self.agent.memory_manager.push_brd_status(task_id, status)
            
            # Return failed task
            task = Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state="failed",
                    message=Message(
                        message_id=str(uuid4()),
                        role="agent",
                        parts=[TextPart(text=f"Error: {str(e)}")]
                    )
                )
            )
            
            return SendTaskResponse(id=request.id, result=task)


class BRDGeneratorAgent(AgentClass):
    """BRD Generator Agent extending AgentClass
    
    Generates comprehensive Business Requirements Documents from
    natural language prompts using LLM, with caching and policy controls.
    """
    
    def __init__(
        self,
        session_id: str,
        redis_url: str,
        azure_openai_endpoint: str,
        azure_openai_key: str,
        azure_openai_deployment: str,
        azure_openai_api_version: str = "2023-05-15",
        azure_search_endpoint: Optional[str] = None,
        azure_search_key: Optional[str] = None,
        azure_search_index: str = "brd-cache-index",
        azure_openai_embedding_deployment: Optional[str] = None,
        discovery_url: Optional[str] = None,
        client_id: str = "brd-generator-client",
        agent_url: str = "http://localhost:8001",
        enable_policy: bool = False,
        enable_caching: bool = True
    ):
        """Initialize BRD Generator Agent
        
        Args:
            session_id: User session identifier
            redis_url: Redis connection URL
            azure_openai_endpoint: Azure OpenAI endpoint
            azure_openai_key: Azure OpenAI API key
            azure_openai_deployment: Model deployment name
            azure_openai_api_version: API version
            azure_search_endpoint: Azure Search endpoint (for caching)
            azure_search_key: Azure Search API key
            azure_search_index: Azure Search index name
            azure_openai_embedding_deployment: Embedding model deployment
            discovery_url: Discovery Service URL (for policy)
            client_id: Client identifier for policy
            agent_url: This agent's URL
            enable_policy: Enable policy validation
            enable_caching: Enable semantic caching
        """
        self.session_id = session_id
        self.deployment_name = azure_openai_deployment
        self.agent_url = agent_url  # Store agent URL for A2A server
        
        logger.info(f"Initializing BRD Generator Agent for session: {session_id}")
        logger.info(f"Agent URL: {agent_url}")
        
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
        self.memory_manager = BRDMemoryManager(
            redis_client=self.redis_client,
            azure_search_endpoint=azure_search_endpoint if enable_caching else None,
            azure_search_key=azure_search_key if enable_caching else None,
            azure_search_index=azure_search_index,
            azure_openai_endpoint=azure_openai_endpoint if enable_caching else None,
            azure_openai_key=azure_openai_key if enable_caching else None,
            azure_openai_embedding_deployment=azure_openai_embedding_deployment
        )
        logger.info("Memory Manager initialized")
        
        # 4. Initialize Policy Manager
        self.policy_manager = None
        if enable_policy and discovery_url:
            policy_types_path = os.path.join(
                os.path.dirname(__file__),
                "data/policy_types.json"
            )
            policy_types = {}
            if os.path.exists(policy_types_path):
                with open(policy_types_path, 'r') as f:
                    policy_types = json.load(f)
            
            self.policy_manager = PolicyManager(
                discovery_app_url=discovery_url,
                client_id=client_id,
                agent_url=agent_url,
                policy_types=policy_types
            )
            logger.info("Policy Manager initialized")
        else:
            logger.info("Policy validation disabled")
        
        # 5. Create BRD generation tool
        brd_tool = create_brd_generation_tool(
            llm=self.llm,
            deployment_name=self.deployment_name,
            memory_manager=self.memory_manager
        )
        
        # 6. Initialize parent AgentClass
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
                "checkpoint_ns": "brd_generator"
            }
        }
        
        super().__init__(
            agent_name="brd-generator",
            tools=[brd_tool],
            config=config,
            memory_backend=None,  # Using custom memory manager
            prompt=(
                "You are a Business Requirements Document (BRD) Generator agent. "
                "Your role is to transform natural language requirements into comprehensive, "
                "structured BRDs that include business goals, functional/non-functional "
                "requirements, stakeholders, acceptance criteria, and risk analysis. "
                "Always use the generate_brd tool to process user requests."
            )
        )
        
        # 7. Initialize custom task manager
        self.task_manager = BRDTaskManager(self)
        logger.info("BRD Generator Agent fully initialized")
    
    def _init_redis(self, redis_url: str) -> StrictRedis:
        """Initialize Redis client (supports both real Redis and FakeRedis)"""
        try:
            # Check if using fakeredis
            if redis_url.startswith('fakeredis://'):
                logger.info("Using FakeRedis (in-memory, no server needed)")
                import fakeredis
                client = fakeredis.FakeStrictRedis(decode_responses=True)
                logger.info("✅ FakeRedis initialized successfully")
                return client
            else:
                # Use real Redis
                client = StrictRedis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                client.ping()
                logger.info(f"✅ Redis connected: {redis_url}")
                return client
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            raise
    
    async def generate_brd(
        self,
        user_prompt: str,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate BRD from user prompt
        
        Args:
            user_prompt: Natural language requirements
            task_id: Task identifier for tracking
            
        Returns:
            Dict with brd_json, brd_markdown, from_cache
        """
        logger.info("Invoking BRD generation tool...")
        
        # Use the LangGraph agent to process
        from src.agents.brd_generator.brd_generator_tool import generate_brd_function
        
        result = await generate_brd_function(
            user_prompt=user_prompt,
            llm=self.llm,
            deployment_name=self.deployment_name,
            memory_manager=self.memory_manager,
            task_id=task_id or str(uuid4()),
            include_markdown=True
        )
        
        return {
            "brd_json": result.brd_json,
            "brd_markdown": result.brd_markdown,
            "from_cache": result.from_cache,
            "similarity_score": result.similarity_score
        }
    
    def get_task_manager(self):
        """Get the task manager for A2A server"""
        return self.task_manager
    
    def build_agent_card(self):
        """Build agent card for A2A protocol"""
        from agent_base.types import (
            BaseAgentcard,
            BaseAgentSkill,
            BaseAgentCapabilities,
            BaseAgentAuthentication,
            AgentAccess
        )
        
        skill = BaseAgentSkill(
            id="generate_brd",
            name="Business Requirements Document Generation",
            description="Generate comprehensive Business Requirements Documents from natural language descriptions. Includes business goals, functional/non-functional requirements, stakeholders, acceptance criteria, assumptions, constraints, and risk analysis.",
            tags=["brd", "requirements", "documentation", "business-analysis"],
            examples=[
                "Create a BRD for a customer relationship management system",
                "Generate requirements for an e-commerce platform with inventory management",
                "Build a BRD for a mobile app for food delivery with real-time tracking"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description of the system or feature to document"
                    },
                    "user_prompt": {
                        "type": "string",
                        "description": "Alternative field name for requirements description"
                    }
                },
                "required": []
            },
            output_schema={
                "type": "object",
                "properties": {
                    "brd_json": {
                        "type": "object",
                        "description": "Structured BRD in JSON format"
                    },
                    "brd_markdown": {
                        "type": "string",
                        "description": "Professional markdown-formatted BRD"
                    },
                    "from_cache": {
                        "type": "boolean",
                        "description": "Whether result was retrieved from cache"
                    }
                }
            }
        )
        
        capabilities = BaseAgentCapabilities(
            streaming=False,
            supportsEvents=False
        )
        
        authentication = BaseAgentAuthentication(
            schemes=["Bearer", "API_Key"],
            credentials="JWT_Token"
        )
        
        return BaseAgentcard(
            name="BRD Generator Agent",
            description="Enterprise agent for generating comprehensive Business Requirements Documents from natural language descriptions",
            url=self.agent_url,
            version="1.0.0",
            skills=[skill],
            capabilities=capabilities,
            authentication=authentication,
            visibility=AgentAccess(
                accessGroup="",
                vnet="",
                authentication_required=False
            ),
            owner_email="brd-generator@winwire.com"
        )
    
    def start(self, host: str = "0.0.0.0", port: int = 8001):
        """Start A2A server
        
        Args:
            host: Server host address (bind address)
            port: Server port number
        """
        logger.info(f"Starting BRD Generator A2A Server on {host}:{port}")
        
        # Use the agent_url from initialization (already set correctly)
        # DON'T override with bind address (0.0.0.0 is not client-accessible)
        logger.info(f"Agent URL for discovery: {self.agent_url}")
        
        agent_card = self.build_agent_card()
        self.server = self._launch_a2a_server(
            port=port,
            host=host,
            plugin_type="agent",
            include_query_handler=False,
            agent_card=agent_card,
            task_manager=self.task_manager,
            agent_url=self.agent_url
        )
        logger.info(f"✅ A2A Server ready at {self.agent_url}")
        self.server.start()
