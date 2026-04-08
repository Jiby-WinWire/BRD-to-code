"""Test Jira To Code Agent via JSON-RPC A2A Protocol - FIXED"""

import json
import sys
import asyncio
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from a2a.types import Message, TextPart, Role
from agent_base import SendTaskRequest

import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_jira_to_code_jsonrpc():
    """Test Jira To Code agent via A2A JSON-RPC"""
    
    logger.info("=== Testing Jira To Code Agent via JSON-RPC A2A ===\n")
    
    # Test Jira issue
    test_issue = """
    Implement user authentication with JWT tokens.
    Requirements:
    - Accept email and password for login
    - Generate JWT access token on successful auth
    - Implement JWT verification for protected routes
    - Add refresh token mechanism
    - Hash passwords using bcrypt
    - Return 401 on invalid credentials
    """
    
    task_id = str(uuid4())
    message_id = str(uuid4())
    
    # Prepare JSON-RPC request (informational display)
    print("📝 JSON-RPC Request Format:")
    print("=" * 80)
    
    json_rpc_request = {
        "jsonrpc": "2.0",
        "id": task_id,
        "method": "jira_to_code",
        "params": {
            "issue_text": test_issue
        }
    }
    print(json.dumps(json_rpc_request, indent=2))
    print("=" * 80)
    print()
    
    # Create proper A2A Message
    message = Message(
        messageId=message_id,
        role=Role.user,
        parts=[TextPart(text=test_issue)]
    )
    
    # Create SendTaskRequest with proper A2A schema
    request = SendTaskRequest(
        id=task_id,
        method="tasks/send",
        params={"message": message}
    )
    
    print("📡 A2A Task Request Details:")
    print("=" * 80)
    print(f"Task ID: {task_id}")
    print(f"Message ID: {message_id}")
    print(f"Method: tasks/send (A2A Protocol)")
    print(f"Agent Server: http://localhost:8003")
    print(f"Issue Text: {test_issue[:80]}...")
    print("=" * 80)
    print()
    
    try:
        # Load environment
        env_path = project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        # Import agent
        from src.agents.jira_to_code.jira_to_code_agent import JiraToCodeAgent
        
        # Setup Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        use_fake = os.getenv('USE_FAKE_REDIS', 'auto').lower()
        
        if use_fake == 'auto':
            try:
                import redis
                test_client = redis.StrictRedis.from_url(redis_url, socket_timeout=2)
                test_client.ping()
                print("✅ Connected to Redis\n")
            except:
                redis_url = 'fakeredis://localhost'
                print("✅ Using FakeRedis (in-memory)\n")
        elif use_fake == 'true':
            redis_url = 'fakeredis://localhost'
            print("✅ Using FakeRedis (in-memory)\n")
        
        # Create agent
        logger.info("Initializing Jira To Code Agent...")
        agent = JiraToCodeAgent(
            session_id=task_id,
            redis_url=redis_url,
            azure_openai_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_openai_key=os.getenv('AZURE_OPENAI_KEY'),
            azure_openai_deployment=os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt4o_mktgenai')
        )
        logger.info("✅ Agent initialized")
        print()
        
        # Get task manager and process request
        task_manager = agent.get_task_manager()
        logger.info("Processing A2A task request via Task Manager...")
        
        response = await task_manager.on_send_task(request)
        
        print("✅ Task Processed Successfully!\n")
        print("=" * 80)
        print("📤 A2A Task Response:")
        print("=" * 80)
        print(f"Response ID: {response.id}")
        print(f"Task ID: {response.result.id}")
        print(f"Status: {response.result.status.value}")
        print()
        
        # Extract generated code
        if response.result.message and response.result.message.parts:
            result_text = response.result.message.parts[0].text
            print("Generated Code:")
            print("-" * 80)
            print(result_text)
            print("-" * 80)
        print()
        
        # Show JSON-RPC response format
        json_rpc_response = {
            "jsonrpc": "2.0",
            "id": task_id,
            "result": {
                "task_id": response.result.id,
                "status": response.result.status.value,
                "code_generated": True
            }
        }
        
        print("📤 JSON-RPC Response Format:")
        print("=" * 80)
        print(json.dumps(json_rpc_response, indent=2))
        print("=" * 80)
        print()
        
        logger.info("✅ JSON-RPC Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        
        json_rpc_error = {
            "jsonrpc": "2.0",
            "id": task_id,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }
        
        print("\n❌ JSON-RPC Error Response:")
        print("=" * 80)
        print(json.dumps(json_rpc_error, indent=2))
        print("=" * 80)
        raise


if __name__ == "__main__":
    asyncio.run(test_jira_to_code_jsonrpc())

