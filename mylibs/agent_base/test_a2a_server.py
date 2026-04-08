import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient
from agent_base.a2a_server import BaseA2AServer
from fastapi import HTTPException
import uuid
from fastapi import HTTPException, Request
from a2a.server import A2AServer
from a2a.types import Message, Task, TaskStatus
import logging
from starlette.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
import json
import uuid

logger = logging.getLogger(__name__)

class TestA2AServer(A2AServer):
    """Test version of A2A server that bypasses authentication for local testing"""
    
    def __init__(self, agent_card, task_manager, host="localhost", port=None, include_query_handler=False, agent_url=None, plugin_type="agent"):
        super().__init__(agent_card=agent_card, task_manager=task_manager, host=host, port=port)
        self.agent_url = agent_url

        @self.app.route('/.well-known/ai-plugin.json', methods=['GET'])
        async def well_known(request: Request):
            return JSONResponse(content=self.agent_card.model_dump(), status_code=200)

        if include_query_handler:
            @self.app.route('/process_query', methods=['POST'])
            async def process_query(request: Request):
                try:
                    data = await request.json()
                    user_query = data.get("query")
                    force_fresh = data.get("force_fresh", False)
                    space_name = data.get("space_name", None)
                    
                    # Generate test values for auth-related fields
                    session_id = str(uuid.uuid4())
                    user_id = str(uuid.uuid4())
                    user_rbac = ["test_role"]
                    app_id = "test_app"
                    auth_header = "test_auth_header"
                    
                    if not user_query:
                        return JSONResponse(content={"error": "Query is required"}, status_code=400)

                    print("\n[Breaking Down Query...]")
                    plan = await task_manager.agent.break_down_query(
                        user_query, 
                        force_fresh=force_fresh,
                        user_rbac=user_rbac,
                        app_id=app_id,
                        auth_header=auth_header,
                        session_id=session_id,
                        user_id=user_id,
                        space_name=space_name
                    )
                    print("[Generated Plan]:", plan)

                    print("\n[Sending Tasks to Supervisor Agent...]")
                    await task_manager.agent.prepare_for_supervisor(
                        plan,
                        goal=user_query,
                        force_fresh=force_fresh,
                        user_rbac=user_rbac,
                        app_id=app_id,
                        auth_header=auth_header,
                        user_id=user_id,
                        session_id=session_id,
                        space_name=space_name
                    )
                    print("[Tasks Sent to Supervisor Agent]")

                    return JSONResponse(content={"message": "Query processed successfully", "tasks": plan}, status_code=200)

                except Exception as e:
                    logger.error(f"[/process_query Error] {e}")
                    return JSONResponse(content={"error": str(e)}, status_code=500)

        @self.app.route("/task", methods=["POST"])
        async def task_compat_handler(request: Request):
            try:
                body = await request.json()
                task_id = body.get("task_id", "task_compat")
                input_data = body.get("input", {})
                query_text = input_data.get("ping", "SELECT 1")

                send_task = SendTaskRequest(
                    id=task_id,
                    method="tasks/send",
                    params={
                        "id": task_id,
                        "message": {
                            "role": "user",
                            "parts": [{"type": "text", "text": query_text}]
                        }
                    }
                )

                result = await self.task_manager.on_send_task(send_task)

                return JSONResponse(content={
                    "task_id": task_id,
                    "result": result.result.status.message.parts[0].text
                })

            except Exception as e:
                logger.error(f"Exception in /task: {e}", exc_info=True)
                return JSONResponse(content={"error": str(e)}, status_code=500)

    async def _process_request(self, request: Request):
        """Override to bypass token validation"""
        try:
            # For test server, create a simple request with basic test data
            test_claims = {
                "method": "tasks/send",
                "params": {
                    "id": str(uuid.uuid4()),
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": "test query"}]
                    },
                    "metadata": {
                        "test_mode": True
                    }
                }
            }

            class ModifiedRequest(StarletteRequest):
                async def json(self_inner):
                    return test_claims

                async def body(self_inner):
                    return json.dumps(test_claims).encode("utf-8")

            modified_request = ModifiedRequest(request.scope, request.receive)
            return await super()._process_request(modified_request)

        except Exception as e:
            logger.error(f"Error in test server: {e}")
            return JSONResponse(
                content={"error": str(e)},
                status_code=500
            )

@pytest.fixture
def mock_task_manager():
    task_manager = AsyncMock()
    task_manager.agent.break_down_query = AsyncMock(return_value=["task1", "task2"])
    task_manager.agent.prepare_for_supervisor = AsyncMock()
    return task_manager

@pytest.fixture
def mock_agent_card():
    return AsyncMock(model_dump=AsyncMock(return_value={"name": "test_agent"}))

@pytest.fixture
def test_server(mock_agent_card, mock_task_manager):
    server = BaseA2AServer(
        agent_card=mock_agent_card,
        task_manager=mock_task_manager,
        include_query_handler=True,
        agent_url="http://localhost",
    )
    return TestClient(server.app)

@pytest.mark.asyncio
@patch("..a2a_server.validate_token", new_callable=AsyncMock)
async def test_process_query_success(mock_validate_token, test_server, mock_task_manager):
    mock_validate_token.return_value = {
        "claims": {
            "roles": ["role1"],
            "aud": "app_id",
            "oid": "user_id_jwt"
        }
    }
    headers = {
        "Authorization": "Bearer test_token",
        "Client-ID": "test_client_id"
    }
    data = {
        "query": "test_query",
        "force_fresh": True
    }
    response = test_server.post("/process_query", headers=headers, json=data)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Query processed successfully",
        "tasks": ["task1", "task2"]
    }
    mock_task_manager.agent.break_down_query.assert_called_once_with(
        "test_query",
        force_fresh=True,
        user_rbac=["role1"],
        app_id="app_id",
        auth_header="Bearer test_token",
        session_id=mock.ANY,
        user_id="user_id_jwt"
    )
    mock_task_manager.agent.prepare_for_supervisor.assert_called_once()

@pytest.mark.asyncio
@patch("..a2a_server.validate_token", new_callable=AsyncMock)
async def test_process_query_missing_auth_header(mock_validate_token, test_server):
    data = {"query": "test_query"}
    response = test_server.post("/process_query", json=data)
    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization header missing"}

@pytest.mark.asyncio
@patch("..a2a_server.validate_token", new_callable=AsyncMock)
async def test_process_query_missing_client_id(mock_validate_token, test_server):
    headers = {"Authorization": "Bearer test_token"}
    data = {"query": "test_query"}
    response = test_server.post("/process_query", headers=headers, json=data)
    assert response.status_code == 400
    assert response.json() == {"detail": "Client-ID header missing"}

@pytest.mark.asyncio
@patch("..a2a_server.validate_token", new_callable=AsyncMock)
async def test_process_query_missing_query(mock_validate_token, test_server):
    mock_validate_token.return_value = {"claims": {}}
    headers = {
        "Authorization": "Bearer test_token",
        "Client-ID": "test_client_id"
    }
    data = {}
    response = test_server.post("/process_query", headers=headers, json=data)
    assert response.status_code == 400
    assert response.json() == {"error": "Query is required"}

@pytest.mark.asyncio
@patch("..a2a_server.validate_token", new_callable=AsyncMock)
async def test_process_query_internal_error(mock_validate_token, test_server, mock_task_manager):
    mock_validate_token.side_effect = Exception("Validation error")
    headers = {
        "Authorization": "Bearer test_token",
        "Client-ID": "test_client_id"
    }
    data = {"query": "test_query"}
    response = test_server.post("/process_query", headers=headers, json=data)
    assert response.status_code == 500
    assert response.json() == {"error": "Validation error"}