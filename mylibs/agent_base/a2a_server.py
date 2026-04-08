from fastapi import HTTPException, Request
from fastapi import FastAPI
from a2a.types import Message, Task, TaskStatus
import logging
from starlette.responses import JSONResponse
import json,os
from starlette.requests import Request as StarletteRequest
import uuid
import uvicorn
from agent_base.types import SendTaskRequest, TaskSendParams

logger = logging.getLogger(__name__)

# Compatibility base class for task managers
class InMemoryTaskManager:
    """Base class for task managers - provides compatibility with old API"""
    async def on_send_task(self, request):
        """Handle incoming task - subclasses must implement this"""
        raise NotImplementedError("Subclass must implement on_send_task")
    
    async def on_send_task_subscribe(self, request):
        """Handle streaming task - subclasses can override this"""
        raise NotImplementedError("Streaming not implemented for this agent.")

class BaseA2AServer:
    """Standalone A2A server implementation for compatibility"""
    def __init__(self, agent_card, task_manager, host="localhost", port = None, include_query_handler=False,agent_url=None, plugin_type="agent"):
        self.app = FastAPI()
        self.agent_card = agent_card
        self.task_manager = task_manager
        self.host = host
        self.port = port
        
        # Add minimal attributes to prevent errors
        self.agent_key_registry = {}  # Empty registry for compatibility
        self.agent_url = agent_url
        well_known_path = "/.well-known/agent.json" if plugin_type == "agent" else "/.well-known/ai-plugin.json"

        # Register agent card endpoint - works for both agent.json and ai-plugin.json
        @self.app.get('/.well-known/agent.json')
        async def well_known_agent(request: Request):
            return JSONResponse(content=self.agent_card.model_dump(by_alias=True), status_code=200)
        
        @self.app.get('/.well-known/ai-plugin.json')
        async def well_known_plugin(request: Request):
            return JSONResponse(content=self.agent_card.model_dump(by_alias=True), status_code=200)

        # Test endpoint to verify server is responding
        @self.app.get('/health')
        async def health_check(request: Request):
            return JSONResponse(content={"status": "healthy", "agent": "BaseA2AServer"}, status_code=200)

        # JSON-RPC endpoint at root for A2A SDK client compatibility
        @self.app.post('/')
        async def jsonrpc_handler(request: Request):
            try:
                body = await request.json()
                method = body.get("method")
                params = body.get("params", {})
                request_id = body.get("id")
                
                logger.info(f"[JSON-RPC] Received request: method={method}, id={request_id}")
                logger.info(f"[JSON-RPC] Params keys: {list(params.keys()) if isinstance(params, dict) else 'not a dict'}")
                
                # Handle message/send method
                if method == "message/send":
                    # Convert params dict to TaskSendParams object
                    # The params should already be in the right format from A2AClient
                    task_send_params = TaskSendParams(**params)
                    
                    # Create SendTaskRequest
                    send_task = SendTaskRequest(
                        id=request_id or str(uuid.uuid4()),
                        method="tasks/send",
                        params=task_send_params
                    )
                    
                    logger.info(f"[JSON-RPC] Calling task_manager.on_send_task with SendTaskRequest")
                    
                    # Call task manager
                    result = await self.task_manager.on_send_task(send_task)
                    
                    logger.info(f"[JSON-RPC] Task manager returned result: {type(result)}")
                    
                    # Debug: Log what we're about to return
                    if hasattr(result, 'model_dump'):
                        dumped = result.model_dump(by_alias=True)
                        logger.info(f"[JSON-RPC] model_dump keys: {dumped.keys() if dumped else 'None'}")
                        logger.info(f"[JSON-RPC] model_dump['result'] type: {type(dumped.get('result')) if dumped and 'result' in dumped else 'NO RESULT KEY'}")
                        
                        # CRITICAL FIX: SendTaskResponse is already a JSON-RPC wrapper
                        # Extract just the 'result' field to avoid double-wrapping
                        actual_result = dumped.get('result') if 'result' in dumped else dumped
                        logger.info(f"[JSON-RPC] Extracted actual result type: {type(actual_result)}")
                    else:
                        actual_result = result
                        logger.warning(f"[JSON-RPC] result has no model_dump, using as-is: {type(result)}")
                    
                    # Return JSON-RPC response
                    return JSONResponse(content={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": actual_result
                    })
                else:
                    logger.warning(f"[JSON-RPC] Unknown method: {method}")
                    return JSONResponse(content={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }, status_code=404)
                    
            except Exception as e:
                logger.error(f"[JSON-RPC] handler error: {e}", exc_info=True)
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": body.get("id") if 'body' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }, status_code=500)

        # Optional: /process_query route for agents with planning/supervision
        if include_query_handler:
            @self.app.route('/process_query', methods=['POST'])
            async def process_query(request: Request):
                try:
                    data = await request.json()
                    # No authentication - simplified for development
                    metadata = data.get("metadata", {})
                    session_id = metadata.get("session_id") or request.headers.get("Session-ID") or str(uuid.uuid4())
                    user_id = metadata.get("user_id") or request.headers.get("Client-ID") or str(uuid.uuid4())
                    user_rbac = ["test_role"]
                    auth_header = "test_auth_header"
                    
                    user_query = data.get("query")
                    
                    # Pass force_fresh if present, else default to False
                    force_fresh = data.get("force_fresh", False)
                    # Pass space_name if present, else default to None
                    space_name = data.get("space_name", None)
                    
                    # Use space_name as app_id if provided, otherwise default to "global"
                    app_id = space_name if space_name else "global"
                    
                    if not user_query:
                        return JSONResponse(content={"error": "Query is required"}, status_code=400)

                    print("\n[Breaking Down Query...]")
                    plan = await task_manager.agent.break_down_query(user_query, force_fresh=force_fresh, user_rbac=user_rbac, app_id=app_id, auth_header=auth_header, session_id=session_id, user_id=user_id, space_name=space_name)
                    print("[Generated Plan]:", plan)

                    print("\n[Sending Tasks to Supervisor Agent...]")
                    await task_manager.agent.prepare_for_supervisor(plan, goal=user_query, force_fresh=force_fresh, user_rbac=user_rbac,app_id=app_id,auth_header=auth_header,user_id=user_id,session_id=session_id,space_name=space_name)
                    print("[Tasks Sent to Supervisor Agent]")

                    return JSONResponse(content={"message": "Query processed successfully", "tasks": plan}, status_code=200)

                except Exception as e:
                    logger.error(f"[/process_query Error] {e}")
                    return JSONResponse(content={"error": str(e)}, status_code=500)
                
        @self.app.route("/task", methods=["POST"])
        async def task_compat_handler(request: Request):
            try:
                headers = request.headers
                auth_header = headers.get("authorization")
                client_id = headers.get("client-id")

                if not auth_header or not auth_header.startswith("Bearer "):
                    raise ValueError("Missing or malformed Authorization header")

                token = auth_header.split(" ", 1)[1].strip()
                if not client_id:
                    raise ValueError("Missing required Client-ID header")

                #  Step 1: Validate token
                token_data = await validate_token(token=token, client_id=client_id)
                logger.info(f" Token data: {token_data}")
                
                roles = token_data["claims"].get("roles", [])
                required_role = AUTHORIZED_ROLE

                if required_role not in roles:
                    logger.error(f" Role check failed: Required '{required_role}' not in {roles}")
                    raise HTTPException(status_code=403, detail="Role not available, don't have access to verify")

                #  Step 2: Parse request
                body = await request.json()

                task_id = body.get("task_id", "task_compat")
                input_data = body.get("input", {})
                query_text = input_data.get("ping", "SELECT 1")

                #  Step 3: Construct send_task
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

                #  Step 4: Call task manager
                result = await self.task_manager.on_send_task(send_task)

                return JSONResponse(content={
                    "task_id": task_id,
                    "result": result.result.status.message.parts[0].text
                })

            except Exception as e:
                logger.error(f" Exception in /task: {e}", exc_info=True)
                return JSONResponse(content={"error": str(e)}, status_code=500)

                
    async def _process_request(self, request: Request):
        try:
            # TESTING MODE: Skip JWT validation and allow plain requests
            # Step 1: Pass the prevalidation
            claims = await self.prevalidate_token(request)

            # Step 2: Check if claims is received
            if claims is None:
                # TESTING: Allow plain requests without JWT encryption
                return await super()._process_request(request)  # Security bypass for testing
                # raise HTTPException(
                #     status_code=401, 
                #     detail="Missing encrypted token - security violation: All agent-to-agent communication must be encrypted"
                # )

            # Step 3: Create a modified request that returns decoded claims
            class ModifiedRequest(StarletteRequest):
                async def json(self_inner):
                    # Extract the params from claims - this contains the actual task data
                    return claims.get("params", {})

                async def body(self_inner):
                    # Return the params as JSON body, not the entire claims
                    return json.dumps(claims.get("params", {})).encode("utf-8")

            modified_request = ModifiedRequest(request.scope, request.receive)

            # Step 4: Call the superclass method with the modified request 
            return await super()._process_request(modified_request)

        except Exception as e:
            return self._handle_exception(e)
        
    async def prevalidate_token(self, request: Request):
        body = await request.json()
        token = body.get("token")
        sender_agent = body.get("sender_agent")

        if not token:
            return None  # Token not present, let base class handle

        if not sender_agent:
            raise ValueError("Missing sender_agent_id in request body.")
        
        # Lookup public JWK for the agent
        jwk_obj = self.agent_key_registry.get(sender_agent)
        if not jwk_obj:
            raise ValueError(f"No public key registered for agent: {sender_agent}")
        
        try:
            jwt_token = JWT(jwt=token, key=jwk_obj)
            claims = json.loads(jwt_token.claims)
            receiver_agent_url = (
                claims.get("params", {})
                    .get("metadata", {})
                    .get("receiver_agent_url")
                )
            if self.normalize_url(receiver_agent_url) != self.normalize_url(self.agent_url):
                raise ValueError(f"Token intended for {receiver_agent_url}, not this agent ({self.agent_url}).")
            
            return claims
        except JWException as e:
            raise ValueError(f"Token validation failed: {str(e)}")
        
    def normalize_url(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"
    
    def start(self):
        """Start the FastAPI server"""
        uvicorn.run(self.app, host=self.host, port=self.port)
