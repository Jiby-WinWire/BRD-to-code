"""Jira To Code Agent

Enterprise-grade agent for converting Jira issue descriptions into starter code.
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
from src.agents.jira_to_code.memory_manager import JiraMemoryManager
from src.agents.jira_to_code.policy_manager import PolicyManager
from src.agents.jira_to_code.jira_to_code_tool import create_jira_to_code_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JiraTaskManager(InMemoryTaskManager):
    """Custom task manager for Jira To Code agent
    
    Handles A2A protocol SendTaskRequest and manages task lifecycle
    """
    
    def __init__(self, agent: 'JiraToCodeAgent'):
        super().__init__()
        self.agent = agent
        logger.info("JiraTaskManager initialized")
    
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handle incoming A2A task request
        
        Args:
            request: SendTaskRequest with user query
            
        Returns:
            SendTaskResponse with generated code
        """
        logger.info(f"Received SendTaskRequest: {request.id}")
        task_id = request.id or str(uuid4())
        
        try:
            # Extract user query from message
            user_query = None
            
            logger.debug(f"Request params type: {type(request.params)}")
            logger.debug(f"Request params: {request.params}")
            
            if request.params:
                # Handle params as dict or object
                params_dict = request.params
                if hasattr(params_dict, '__dict__'):
                    params_dict = params_dict.__dict__
                elif not isinstance(params_dict, dict):
                    params_dict = {}
                
                logger.debug(f"Params dict keys: {params_dict.keys() if isinstance(params_dict, dict) else 'N/A'}")
                
                message = params_dict.get('message') if isinstance(params_dict, dict) else getattr(request.params, 'message', None)
                
                if message:
                    logger.debug(f"Message type: {type(message)}")
                    logger.debug(f"Message: {message}")
                    
                    # Extract parts from message
                    parts = message.parts if hasattr(message, 'parts') else []
                    logger.debug(f"Message parts: {parts}")
                    
                    for part in parts:
                        logger.debug(f"Part type: {type(part)}, content: {part}")
                        # Handle nested Part(root=TextPart(...)) structure
                        if hasattr(part, 'root'):
                            text_part = part.root
                            if hasattr(text_part, 'text'):
                                user_query = text_part.text
                                logger.info(f"Extracted text from nested part: {user_query[:50]}...")
                                break
                        elif isinstance(part, TextPart):
                            user_query = part.text
                            logger.info(f"Extracted text from TextPart: {user_query[:50]}...")
                            break
                        elif hasattr(part, 'text'):
                            user_query = part.text
                            logger.info(f"Extracted text from part (fallback): {user_query[:50]}...")
                            break
            
            if not user_query:
                logger.error(f"No text content found in request. Params: {request.params}")
                raise ValueError("No text content found in request")
            
            logger.info(f"Processing code generation for: {user_query[:100]}...")
            
            # Generate code using agent
            result = await self.agent.convert_issue(
                issue_text=user_query,
                task_id=task_id
            )
            
            logger.info(f"Code generation completed for task: {task_id}")
            
            # Extract context_id from request
            context_id = getattr(request.params, 'context_id', None) or str(uuid4())
            
            # Create response message
            response_text = (
                f"Code Generated Successfully!\n\n"
                f"```\n{result['code_snippet']}\n```\n\n"
                f"Explanation:\n{result.get('explanation', 'N/A')}"
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
            
            # Extract context_id from request
            context_id = getattr(request.params, 'context_id', None) or str(uuid4())
            
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


class JiraToCodeAgent(AgentClass):
    """Jira To Code Agent extending AgentClass
    
    Converts Jira issue descriptions into starter code snippets,
    test stubs, and implementation notes.
    """
    
    def __init__(
        self,
        session_id: str,
        redis_url: str,
        azure_openai_endpoint: str,
        azure_openai_key: str,
        azure_openai_deployment: str,
        azure_openai_api_version: str = "2023-05-15",
        discovery_url: Optional[str] = None,
        client_id: str = "jira-to-code-client",
        agent_url: str = "http://localhost:8005",
        enable_policy: bool = False
    ):
        """Initialize Jira To Code Agent
        
        Args:
            session_id: User session identifier
            redis_url: Redis connection URL
            azure_openai_endpoint: Azure OpenAI endpoint
            azure_openai_key: Azure OpenAI API key
            azure_openai_deployment: Model deployment name
            azure_openai_api_version: API version
            discovery_url: Discovery Service URL (for policy)
            client_id: Client identifier for policy
            agent_url: This agent's URL
            enable_policy: Enable policy validation
        """
        self.session_id = session_id
        self.deployment_name = azure_openai_deployment
        self.agent_url = agent_url  # Store agent URL for A2A server
        
        logger.info(f"Initializing Jira To Code Agent for session: {session_id}")
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
        self.memory_manager = JiraMemoryManager(redis_client=self.redis_client)
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
        
        # 5. Create Jira to Code generation tool
        jira_tool = create_jira_to_code_tool(
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
                "checkpoint_ns": "jira_to_code"
            }
        }
        
        super().__init__(
            agent_name="jira-to-code",
            tools=[jira_tool],
            config=config,
            memory_backend=None,  # Using custom memory manager
            prompt=(
                "You are a developer assistant that converts Jira issue descriptions into starter code, "
                "test stubs, and implementation hints. Your role is to analyze issue descriptions and "
                "generate relevant code snippets that developers can use as a starting point. "
                "Always use the generate_code_from_jira tool to process user requests."
            )
        )
        
        # 7. Initialize custom task manager
        self.task_manager = JiraTaskManager(self)
        logger.info("Jira To Code Agent fully initialized")

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
    
    async def convert_issue(
        self,
        issue_text: str,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert Jira issue to code
        
        Args:
            issue_text: Jira issue description
            task_id: Task identifier for tracking
            
        Returns:
            Dict with code_snippet, explanation, from_cache
        """
        logger.info("Invoking code generation tool...")
        
        # Use the LangGraph agent to process
        from src.agents.jira_to_code.jira_to_code_tool import generate_code_from_jira_function
        
        result = await generate_code_from_jira_function(
            issue_text=issue_text,
            llm=self.llm,
            deployment_name=self.deployment_name,
            memory_manager=self.memory_manager,
            task_id=task_id or str(uuid4())
        )
        
        return {
            "code_snippet": result.code_snippet,
            "explanation": result.explanation,
            "from_cache": result.from_cache
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
            id="generate_code_from_jira",
            name="Jira Issue to Code Generator",
            description="Convert Jira issue descriptions into starter code snippets, test stubs, and implementation notes. Helps developers jumpstart implementation from issue descriptions.",
            tags=["jira", "code-generation", "development"],
            examples=[
                "Convert signup form validation task to Python code",
                "Generate test stubs for API endpoint implementation",
                "Create code skeleton for database migration task"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "issue_text": {
                        "type": "string",
                        "description": "Jira issue description or task to convert to code"
                    }
                },
                "required": ["issue_text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "code_snippet": {
                        "type": "string",
                        "description": "Generated code snippet"
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the generated code"
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
            name="Jira To Code Agent",
            description="Converts Jira issue descriptions into starter code snippets and implementation notes",
            url=getattr(self, 'agent_url', "http://localhost:8005"),
            version="1.0.0",
            skills=[skill],
            capabilities=capabilities,
            authentication=authentication,
            visibility=AgentAccess(
                accessGroup="",
                vnet="",
                authentication_required=False
            ),
            owner_email="jira-to-code@winwire.com"
        )
    
    def start(self, host: str = "0.0.0.0", port: int = 8005):
        """Start A2A server
        
        Args:
            host: Server host address (bind address)
            port: Server port number
        """
        logger.info(f"Starting Jira To Code A2A Server on {host}:{port}")
        
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
