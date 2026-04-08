"""Test Jira To Code Agent via JSON-RPC A2A Protocol"""

import json
import sys
import asyncio
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from a2a.types import Message, TextPart
from agent_base import SendTaskRequest
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_jira_to_code_via_a2a():
    """Test Jira To Code agent via A2A JSON-RPC"""

    logger.info("=== Testing Jira To Code Agent via A2A JSON-RPC ===\n")

    # Create a test Jira issue
    test_issue = """
    Implement user authentication with login and logout functionality.
    Requirements:
    - Accept username and password
    - Validate credentials against database
    - Create session token on success
    - Return error message on failure
    - Add password hashing for security
    - Include rate limiting to prevent brute force
    """

    # Create A2A Send Task Request (JSON-RPC style)
    task_id = str(uuid4())
    message_id = str(uuid4())

    print("?? Test JSON-RPC Request:")
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

    # Create A2A Message with TextPart for the issue
    message = Message(
        messageId=message_id,
        role="user",
        parts=[TextPart(text=test_issue)]
    )

    # Create SendTaskRequest (using agent_base types)
    # Note: method must be 'tasks/send' as per A2A protocol
    request = SendTaskRequest(
        id=task_id,
        method="tasks/send",
        params={"message": message}
    )

    logger.info(f"Sending A2A task request to Jira To Code agent...")
    logger.info(f"Task ID: {task_id}")
    logger.info(f"Message ID: {message_id}")
    logger.info(f"Role: user")
    logger.info(f"Issue: {test_issue[:100]}...")

    print("\n?? A2A Request Details:")
    print("=" * 80)
    print(f"Task ID: {task_id}")
    print(f"Message ID: {message_id}")
    print(f"Method: tasks/send")
    print(f"Role: user")
    print("=" * 80)
    print()

    try:
        # Direct import and call the agent
        from src.agents.jira_to_code.jira_to_code_agent import JiraToCodeAgent    
        from dotenv import load_dotenv
        import os

        # Load environment
        env_path = project_root / '.env'
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)

        # Create agent
        redis_url = os.getenv('REDIS_URL', 'fakeredis://localhost')
        use_fake = os.getenv('USE_FAKE_REDIS', 'auto').lower()
        if use_fake == 'auto':
            try:
                import redis
                test_client = redis.StrictRedis.from_url(redis_url, socket_timeout=2)
                test_client.ping()
            except:
                redis_url = 'fakeredis://localhost'
        elif use_fake == 'true':
            redis_url = 'fakeredis://localhost'

        agent = JiraToCodeAgent(
            session_id=task_id,
            redis_url=redis_url,
            azure_openai_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_openai_key=os.getenv('AZURE_OPENAI_KEY'),
            azure_openai_deployment=os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt4o_mktgenai')
        )

        # Get task manager
        task_manager = agent.get_task_manager()

        # Process the request via task manager
        logger.info("Processing task via A2A Task Manager...")
        response = await task_manager.on_send_task(request)

        print("\n? A2A Response Received:")
        print("=" * 80)
        print(f"Response ID: {response.id}")
        print(f"Task ID: {response.result.id}")
        print(f"Status: {response.result.status}")
        print()

        # Extract result
        if response.result and response.result.message and response.result.message.parts:
            result_text = response.result.message.parts[0].text
            print("?? Generated Code Output:")
            print("-" * 80)
            print(result_text[:800] + ("..." if len(result_text) > 800 else ""))  
            print("-" * 80)

        print()
        print("=" * 80)

        # Create JSON-RPC response
        json_rpc_response = {
            "jsonrpc": "2.0",
            "id": task_id,
            "result": {
                "task_id": response.result.id,
                "status": str(response.result.status),
                "message": (result_text[:300] + "..." if response.result.message else None)
            }
        }

        print("\n?? JSON-RPC Response:")
        print("=" * 80)
        print(json.dumps(json_rpc_response, indent=2))
        print("=" * 80)

        logger.info("? Test completed successfully!")
        
    except Exception as e:
        logger.error(f"? Test failed: {str(e)}", exc_info=True)

        error_response = {
            "jsonrpc": "2.0",
            "id": task_id,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }

        print("\n? JSON-RPC Error Response:")
        print("=" * 80)
        print(json.dumps(error_response, indent=2))
        print("=" * 80)
        raise


if __name__ == "__main__":
    asyncio.run(test_jira_to_code_via_a2a())
