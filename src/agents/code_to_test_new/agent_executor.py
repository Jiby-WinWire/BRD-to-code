"""Agent executor for CodeToTestAgent.

Provides standalone test and A2A server entrypoints similar to the BRD generator.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.code_to_test.code_to_test_agent import CodeToTestAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_environment():
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment from: {env_path}")
    else:
        logger.warning(f"No .env file found at: {env_path}")


def get_required_env(key: str, default=None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Required environment variable not set: {key}")
    return value


def create_code_to_test_agent(session_id: str = None, agent_url: str = None) -> CodeToTestAgent:
    load_environment()
    session_id = session_id or str(uuid4())
    logger.info(f"Creating CodeToTest Agent for session: {session_id}")

    redis_url = get_required_env('REDIS_URL', 'redis://localhost:6379')
    use_fake_redis = os.getenv('USE_FAKE_REDIS', 'auto').lower()
    if use_fake_redis == 'auto':
        try:
            import redis
            test_client = redis.StrictRedis.from_url(redis_url, socket_timeout=2)
            test_client.ping()
            logger.info('✅ Connected to Redis server')
            use_fake_redis = False
        except Exception as e:
            logger.warning(f'⚠️  Redis server not available: {str(e)}')
            logger.info('🔄 Using in-memory FakeRedis instead (no Docker needed)')
            use_fake_redis = True
    else:
        use_fake_redis = use_fake_redis == 'true'

    if use_fake_redis:
        redis_url = 'fakeredis://localhost'

    azure_openai_endpoint = get_required_env('AZURE_OPENAI_ENDPOINT')
    azure_openai_key = get_required_env('AZURE_OPENAI_API_KEY', os.getenv('AZURE_OPENAI_KEY'))
    azure_openai_deployment = get_required_env('AZURE_OPENAI_DEPLOYMENT', os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt4o_mktgenai'))
    if agent_url is None:
        agent_url = os.getenv('CODE_TO_TEST_URL', 'http://localhost:8002')

    discovery_url = os.getenv('DISCOVERY_API_URL')
    client_id = os.getenv('CLIENT_ID', 'code-to-test-client')
    enable_policy = os.getenv('ENABLE_POLICY', 'false').lower() == 'true'

    agent = CodeToTestAgent(
        session_id=session_id,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_key=azure_openai_key,
        azure_openai_deployment=azure_openai_deployment,
        redis_url=redis_url,
        discovery_url=discovery_url,
        client_id=client_id,
        agent_url=agent_url,
        enable_policy=enable_policy
    )

    logger.info("CodeToTest Agent created successfully")
    return agent


async def run_standalone_test():
    logger.info("=== CodeToTest Agent Standalone Test ===")
    agent = create_code_to_test_agent()
    test_prompt = [
        {
            "fields": {
                "summary": "Create a simple task management API",
                "description": "Allow users to create, update, and list tasks with status and due date.",
                "labels": ["functional"]
            }
        }
    ]

    try:
        result = await agent.generate_code_and_tests(
            stories=test_prompt,
            task_id="test-" + str(uuid4())
        )
        logger.info("Generated code file paths: %s", list(result['code_files'].keys()))
        logger.info("Generated test file paths: %s", list(result['test_files'].keys()))
        logger.info("Standalone test completed successfully")
    except Exception as e:
        logger.error(f"Standalone test failed: {e}", exc_info=True)
        raise


def start_a2a_server(port: int = 8002):
    logger.info(f"Starting CodeToTest A2A Server on port {port}")
    agent = create_code_to_test_agent(agent_url=f"http://localhost:{port}")
    agent.start(host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CodeToTest Agent")
    parser.add_argument(
        '--mode',
        choices=['test', 'server'],
        default='test',
        help='Run mode: test (standalone) or server (A2A)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8002,
        help='Port for A2A server (default: 8002)'
    )
    args = parser.parse_args()
    if args.mode == 'test':
        asyncio.run(run_standalone_test())
    else:
        start_a2a_server(port=args.port)
