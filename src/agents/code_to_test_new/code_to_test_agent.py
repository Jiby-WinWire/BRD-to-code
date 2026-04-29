"""Code-to-Test agent implementation with A2A support."""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from a2a.types import Task, TaskStatus, Message, TextPart
from langchain_openai import AzureChatOpenAI

from agent_base.agent import AgentClass
from agent_base import InMemoryTaskManager, SendTaskRequest, SendTaskResponse
from src.agents.code_to_test_new.code_to_test_tool import create_code_to_test_tool
from src.agents.code_to_test_new.memory_manager import CodeToTestMemoryManager, CodeToTestAgentStatus
from src.agents.code_to_test_new.policy_manager import PolicyManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CodeToTestTaskManager(InMemoryTaskManager):
    """Task manager for CodeToTestAgent handling A2A SendTaskRequests."""

    def __init__(self, agent: 'CodeToTestAgent'):
        super().__init__()
        self.agent = agent
        logger.info("CodeToTestTaskManager initialized")

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        logger.info(f"Received SendTaskRequest: {request.id}")
        task_id = request.id or str(uuid4())
        
        # Extract context_id safely - supervisor may send it or we generate one
        context_id = getattr(request.params, 'context_id', None) or str(uuid4())

        status = CodeToTestAgentStatus(
            status="processing",
            task_id=task_id,
            session_id=self.agent.session_id,
            start_time=datetime.utcnow().isoformat()
        )
        await self.agent.memory_manager.push_task_status(task_id, status)

        try:
            # Robust message extraction - handle dict, object with .text, object with .root.text
            raw_text = None
            if request.params and request.params.message:
                parts = request.params.message.parts if hasattr(request.params.message, 'parts') else []
                if parts:
                    first_part = parts[0]
                    if isinstance(first_part, dict):
                        raw_text = first_part.get('text', '')
                    elif hasattr(first_part, 'root'):
                        if hasattr(first_part.root, 'text'):
                            raw_text = first_part.root.text
                    elif hasattr(first_part, 'text'):
                        raw_text = first_part.text

            if not raw_text:
                raise ValueError("SendTaskRequest did not contain any text payload")

            logger.info(f"📥 Received raw_text: {len(raw_text)} chars")
            logger.info(f"📥 Raw text preview: {raw_text[:500] if len(raw_text) > 0 else '(empty)'}...")

            stories = self._parse_stories(raw_text)
            if not stories:
                raise ValueError("No stories payload found in task request")

            status.stories = stories
            await self.agent.memory_manager.push_task_status(task_id, status)

            if self.agent.policy_manager:
                logger.info("Validating policies...")
                policy_result = self.agent.policy_manager.validate_all_policies(
                    session_id=self.agent.session_id,
                    task_data={"stories": stories},
                    resources=["azure_openai", "redis_state"],
                    task_type="code_generation"
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
                    status.end_time = datetime.utcnow().isoformat()
                    await self.agent.memory_manager.push_task_status(task_id, status)

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

            logger.info("Generating code and tests from %d stories", len(stories))
            result = await self.agent.generate_code_and_tests(
                stories=stories,
                task_id=task_id
            )

            status.status = "completed"
            status.code_files = result.get("code_files")
            status.test_files = result.get("test_files")
            status.note = result.get("note")
            status.end_time = datetime.utcnow().isoformat()
            await self.agent.memory_manager.push_task_status(task_id, status)

            # PHASE 3: Return actual file contents, not just file names
            response_text = json.dumps({
                "code_files": result["code_files"],  # Full file contents: {path: content}
                "test_files": result["test_files"],  # Full file contents: {path: content}
                "note": result.get("note", "Code generation completed"),
                "summary": {
                    "code_count": len(result["code_files"]),
                    "test_count": len(result["test_files"]),
                    "code_paths": list(result["code_files"].keys()),
                    "test_paths": list(result["test_files"].keys())
                }
            }, indent=2)

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
            logger.error(f"CodeToTest task failed: {str(e)}", exc_info=True)
            existing_status = await self.agent.memory_manager.pull_task_status(task_id)
            if existing_status:
                existing_status.status = "failed"
                existing_status.error_message = str(e)
                existing_status.end_time = datetime.utcnow().isoformat()
                await self.agent.memory_manager.push_task_status(task_id, existing_status)

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

    def _parse_stories(self, raw_text: str) -> List[Dict[str, Any]]:
        import re
        try:
            # Try direct JSON parse first
            try:
                payload = json.loads(raw_text)
                if isinstance(payload, dict) and "stories" in payload:
                    return payload["stories"]
                if isinstance(payload, list):
                    return payload
            except json.JSONDecodeError:
                # Fallback: extract JSON array from mixed text
                match = re.search(r'(\[.*\])', raw_text, re.DOTALL)
                if match:
                    json_text = match.group(1)
                    payload = json.loads(json_text)
                    if isinstance(payload, list):
                        return payload
                raise ValueError("Unable to parse JSON stories from task request payload")
            raise ValueError("JSON payload must contain a list of stories or a top-level 'stories' key")
        except Exception as e:
            raise ValueError("Unable to parse JSON stories from task request payload") from e


class CodeToTestAgent(AgentClass):
    """Agent that generates code and pytest tests from Jira stories."""

    def __init__(
        self,
        session_id: str,
        azure_openai_endpoint: str,
        azure_openai_key: str,
        azure_openai_deployment: str,
        redis_url: str = 'fakeredis://localhost',
        azure_openai_api_version: str = "2023-05-15",
        discovery_url: Optional[str] = None,
        client_id: str = "code-to-test-client",
        agent_url: str = "http://localhost:8002",
        enable_policy: bool = False
    ):
        self.session_id = session_id
        self.deployment_name = azure_openai_deployment
        self.agent_url = agent_url

        logger.info(f"Initializing CodeToTest Agent for session: {session_id}")

        self.redis_client = self._init_redis(redis_url)
        self.memory_manager = CodeToTestMemoryManager(redis_client=self.redis_client)

        self.llm = AzureChatOpenAI(
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            api_version=azure_openai_api_version,
            azure_deployment=azure_openai_deployment,
            temperature=0.2
        )

        self.policy_manager = None
        if enable_policy and discovery_url:
            self.policy_manager = PolicyManager(
                discovery_app_url=discovery_url,
                client_id=client_id,
                agent_url=agent_url
            )
            logger.info("Policy Manager initialized")
        else:
            logger.info("Policy validation disabled")

        code_to_test_tool = create_code_to_test_tool()

        config = {
            "deployment_name": azure_openai_deployment,
            "model_name": azure_openai_deployment,
            "model_version": azure_openai_api_version,
            "api_key": azure_openai_key,
            "api_version": azure_openai_api_version,
            "azure_endpoint": azure_openai_endpoint,
            "temperature": 0.2
        }

        super().__init__(
            agent_name="code-to-test",
            tools=[code_to_test_tool],
            config=config,
            memory_backend=None,
            prompt=(
                "You are a code generation agent that produces executable FastAPI code and pytest tests from Jira user stories. "
                "Use the generate_code_and_tests tool to create production-ready code and corresponding tests."
            )
        )

        self.task_manager = CodeToTestTaskManager(self)
        logger.info("CodeToTest Agent fully initialized")

    def _init_redis(self, redis_url: str):
        try:
            if redis_url.startswith('fakeredis://'):
                logger.info("Using FakeRedis (in-memory, no server needed)")
                import fakeredis
                client = fakeredis.FakeStrictRedis(decode_responses=True)
                logger.info("✅ FakeRedis initialized successfully")
                return client
            else:
                from redis import StrictRedis
                client = StrictRedis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                client.ping()
                logger.info(f"✅ Redis connected: {redis_url}")
                return client
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            raise

    async def generate_code_and_tests(
        self,
        stories: List[Dict[str, Any]],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        logger.info("Invoking code-to-test generation workflow")
        from src.agents.code_to_test_new.code_to_test_tool import generate_code_and_tests_function

        output = await generate_code_and_tests_function(
            stories=stories,
            task_id=task_id or str(uuid4())
        )

        return {
            "code_files": output.code_files,
            "test_files": output.test_files,
            "note": output.note
        }

    def get_task_manager(self):
        return self.task_manager

    def build_agent_card(self):
        from agent_base.types import (
            BaseAgentcard,
            BaseAgentSkill,
            BaseAgentCapabilities,
            BaseAgentAuthentication,
            AgentAccess
        )

        skill = BaseAgentSkill(
            id="generate_code_and_tests",
            name="Code and Test Generation",
            description=(
                "Generate executable FastAPI code and pytest tests from Jira user stories. "
                "The agent accepts structured stories and returns generated code/test file payloads."
            ),
            tags=["code-generation", "test-generation", "fastapi", "pytest"],
            examples=[
                "Generate FastAPI code and pytest tests for user stories describing an order management system",
                "Create API implementation and test suite from task management stories"
            ],
            input_schema={
                "type": "object",
                "properties": {
                    "stories": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of Jira story objects with summary and description"
                    }
                },
                "required": ["stories"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "code_files": {
                        "type": "object",
                        "description": "Generated code file contents indexed by path"
                    },
                    "test_files": {
                        "type": "object",
                        "description": "Generated pytest test file contents indexed by path"
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
            name="Code to Test Agent",
            description="Enterprise agent for generating executable FastAPI code and pytest tests from Jira stories",
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
            owner_email="code-to-test@winwire.com"
        )

    def start(self, host: str = "0.0.0.0", port: int = 8002):
        logger.info(f"Starting CodeToTest A2A Server on {host}:{port}")
        self.agent_url = f"http://{host}:{port}"
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
