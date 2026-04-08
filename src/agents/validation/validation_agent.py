"""Validation Agent

Enterprise-grade agent for validating Business Requirements Documents and requirements specifications.
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
from src.agents.validation.memory_manager import ValidationMemoryManager, ValidationAgentStatus
from src.agents.validation.policy_manager import PolicyManager
from src.agents.validation.validation_tool import create_validation_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationTaskManager(InMemoryTaskManager):
    """Custom task manager for Validation agent
    
    Handles A2A protocol SendTaskRequest and manages task lifecycle
    """
    
    def __init__(self, agent: 'ValidationAgent'):
        super().__init__()
        self.agent = agent
        logger.info("ValidationTaskManager initialized")
    
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handle incoming A2A task request
        
        Args:
            request: SendTaskRequest with document to validate
            
        Returns:
            SendTaskResponse with validation results
        """
        logger.info(f"Received SendTaskRequest: {request.id}")
        task_id = request.id or str(uuid4())
        
        try:
            # Extract document content from message
            document_content = None
            if request.params and request.params.message:
                for part in request.params.message.parts:
                    if isinstance(part, TextPart):
                        document_content = part.text
                        break
            
            if not document_content:
                raise ValueError("No document content found in request")
            
            logger.info(f"Processing validation for document (first 100 chars): {document_content[:100]}...")
            
            # Initialize task status
            status = ValidationAgentStatus(
                status="processing",
                document_content=document_content[:500],
                task_id=task_id,
                session_id=self.agent.session_id,
                start_time=datetime.utcnow().isoformat()
            )
            await self.agent.memory_manager.push_validation_status(task_id, status)
            
            # Policy validation
            if self.agent.policy_manager:
                logger.info("Validating policies...")
                policy_result = self.agent.policy_manager.validate_all_policies(
                    session_id=self.agent.session_id,
                    task_data={"document_length": len(document_content)},
                    resources=["azure_openai", "redis_cache"],
                    task_type="validation"
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
                    await self.agent.memory_manager.push_validation_status(task_id, status)
                    
                    # Return failed task
                    task = Task(
                        id=task_id,
                        status=TaskStatus.FAILED,
                        message=Message(parts=[TextPart(text=error_msg)])
                    )
                    return SendTaskResponse(id=request.id, result=task)
            
            # Validate document using agent
            result = await self.agent.validate_document(
                document_content=document_content,
                task_id=task_id
            )
            
            # Update status
            status.status = "completed"
            status.document_title = result.get("document_title")
            status.validation_result = result.get("validation_result")
            status.is_valid = result.get("is_valid", False)
            status.validation_score = result.get("validation_score", 0.0)
            status.issue_count = len(result.get("issues", []))
            status.critical_issues = len([i for i in result.get("issues", []) if i.get("severity") == "critical"])
            status.cache_hit = result.get("from_cache", False)
            status.end_time = datetime.utcnow().isoformat()
            await self.agent.memory_manager.push_validation_status(task_id, status)
            
            logger.info(f"Validation completed for task: {task_id}")
            
            # Create response message
            response_text = (
                f"Document Validation Completed!\n\n"
                f"Title: {result.get('document_title', 'N/A')}\n"
                f"Valid: {result.get('is_valid', False)}\n"
                f"Score: {result.get('validation_score', 0)}/100\n"
                f"Issues Found: {len(result.get('issues', []))}\n"
                f"From Cache: {result.get('from_cache', False)}\n\n"
                f"Summary: {result.get('summary', 'No summary available')}"
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
            try:
                status = await self.agent.memory_manager.pull_validation_status(task_id)
                if status:
                    status.status = "failed"
                    status.error_message = str(e)
                    status.end_time = datetime.utcnow().isoformat()
                    await self.agent.memory_manager.push_validation_status(task_id, status)
            except:
                pass
            
            # Return failed task
            task = Task(
                id=task_id,
                status=TaskStatus.FAILED,
                message=Message(parts=[TextPart(text=f"Error: {str(e)}")])
            )
            
            return SendTaskResponse(id=request.id, result=task)


class ValidationAgent(AgentClass):
    """Validation Agent extending AgentClass
    
    Validates Business Requirements Documents and requirements specifications for:
    - Completeness: All required sections present
    - Consistency: No contradictions or inconsistencies
    - Clarity: Language is clear and unambiguous
    - Measurability: Requirements are specific and measurable
    - Traceability: Requirements trace to business goals
    - Feasibility: Requirements are technically feasible
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
        azure_search_index: str = "validation-cache-index",
        azure_openai_embedding_deployment: Optional[str] = None,
        discovery_url: Optional[str] = None,
        client_id: str = "validation-client",
        agent_url: str = "http://localhost:8002",
        enable_policy: bool = False,
        enable_caching: bool = True
    ):
        """Initialize Validation Agent
        
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
        
        logger.info(f"Initializing Validation Agent for session: {session_id}")
        
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
        self.memory_manager = ValidationMemoryManager(
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
                "data/validation_types.json"
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
        
        # 5. Create validation tool
        validation_tool = create_validation_tool(
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
                "checkpoint_ns": "validation_agent"
            }
        }
        
        super().__init__(
            agent_name="validation-agent",
            tools=[validation_tool],
            config=config,
            memory_backend=None,  # Using custom memory manager
            prompt=(
                "You are a Document Validation Agent specialized in validating Business Requirements Documents (BRDs) "
                "and requirements specifications. Your role is to thoroughly analyze documents for completeness, "
                "consistency, clarity, measurability, traceability, and feasibility. Always use the validate_document "
                "tool to process user requests and provide detailed validation feedback."
            )
        )
        
        # 7. Initialize custom task manager
        self.task_manager = ValidationTaskManager(self)
        logger.info("Validation Agent fully initialized")
    
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
    
    async def validate_document(
        self,
        document_content: str,
        task_id: Optional[str] = None,
        document_type: str = "brd",
        validation_scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate document
        
        Args:
            document_content: Document content to validate
            task_id: Task identifier for tracking
            document_type: Type of document (brd, requirements, specification)
            validation_scope: Specific validation scope
            
        Returns:
            Dict with validation results
        """
        logger.info("Invoking validation tool...")
        
        # Use the LangGraph agent to process
        from src.agents.validation.validation_tool import validate_document_function
        
        result = await validate_document_function(
            document_content=document_content,
            llm=self.llm,
            deployment_name=self.deployment_name,
            memory_manager=self.memory_manager,
            task_id=task_id or str(uuid4()),
            document_type=document_type,
            validation_scope=validation_scope
        )
        
        return {
            "document_title": result.document_title,
            "is_valid": result.is_valid,
            "validation_score": result.validation_score,
            "validation_result": {
                "document_title": result.document_title,
                "is_valid": result.is_valid,
                "validation_score": result.validation_score,
                "issues": [issue.dict() for issue in result.issues],
                "summary": result.summary
            },
            "issues": [issue.dict() for issue in result.issues],
            "summary": result.summary,
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
            id="validate_document",
            name="Document Validation",
            description="Validate and analyze Business Requirements Documents and requirements specifications for completeness, consistency, clarity, measurability, traceability, and feasibility.",
            tags=["validation", "requirements", "brd", "quality-assurance", "document-analysis"],
            examples=[
                "Validate this BRD for completeness and consistency",
                "Check if this requirements document has clear acceptance criteria",
                "Analyze this specification for technical feasibility",
                "Validate that all business goals are traceable to requirements"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "document_content": {
                        "type": "string",
                        "description": "Document content to validate"
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Type of document: brd, requirements, specification"
                    },
                    "validation_scope": {
                        "type": "string",
                        "description": "Validation scope: completeness, consistency, clarity, all"
                    }
                },
                "required": ["document_content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "is_valid": {
                        "type": "boolean",
                        "description": "Overall validation result"
                    },
                    "validation_score": {
                        "type": "number",
                        "description": "Validation score 0-100"
                    },
                    "issues": {
                        "type": "array",
                        "description": "List of validation issues"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of validation results"
                    }
                }
            }
        )
        
        return skill
