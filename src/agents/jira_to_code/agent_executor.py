"""Agent Executor for Jira To Code

Entry point for running Jira To Code agent as standalone service
or within A2A server.
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

from src.agents.jira_to_code.jira_to_code_agent import JiraToCodeAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_environment():
    """Load environment variables from .env file"""
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment from: {env_path}")
    else:
        logger.warning(f"No .env file found at: {env_path}")


def get_required_env(key: str, default=None) -> str:
    """Get required environment variable
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If required variable not set and no default
    """
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Required environment variable not set: {key}")
    return value


def create_jira_agent(session_id: str = None, agent_url: str = None) -> JiraToCodeAgent:
    """Create Jira To Code Agent instance
    
    Args:
        session_id: Session identifier (generates UUID if not provided)
        agent_url: Override agent URL (defaults to env var or localhost:8005)
        
    Returns:
        Initialized JiraToCodeAgent
    """
    load_environment()
    
    session_id = session_id or str(uuid4())
    logger.info(f"Creating Jira To Code Agent for session: {session_id}")
    
    # Required configuration
    redis_url = get_required_env('REDIS_URL', 'redis://localhost:6379')
    
    # Check if real Redis is available, otherwise use fakeredis
    use_fake_redis = os.getenv('USE_FAKE_REDIS', 'auto').lower()
    if use_fake_redis == 'auto':
        # Try to connect to real Redis
        try:
            import redis
            test_client = redis.StrictRedis.from_url(redis_url, socket_timeout=2)
            test_client.ping()
            logger.info("✅ Connected to Redis server")
            use_fake_redis = False
        except Exception as e:
            logger.warning(f"⚠️  Redis server not available: {str(e)}")
            logger.info("🔄 Using in-memory FakeRedis instead (no Docker needed)")
            use_fake_redis = True
    else:
        use_fake_redis = use_fake_redis == 'true'
    
    # Override redis_url for fakeredis
    if use_fake_redis:
        redis_url = 'fakeredis://localhost'
    
    azure_openai_endpoint = get_required_env('AZURE_OPENAI_ENDPOINT')
    azure_openai_key = get_required_env('AZURE_OPENAI_KEY', os.getenv('AZURE_OPENAI_API_KEY'))
    azure_openai_deployment = get_required_env('AZURE_OPENAI_DEPLOYMENT', os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt4o_mktgenai'))
    
    # Optional configuration for policy
    discovery_url = os.getenv('DISCOVERY_API_URL')
    client_id = os.getenv('CLIENT_ID', 'jira-to-code-client')
    
    # Use provided agent_url or fall back to environment or default
    if agent_url is None:
        agent_url = os.getenv('JIRA_TO_CODE_URL', 'http://localhost:8010')
    
    # Feature flags
    enable_policy = os.getenv('ENABLE_POLICY', 'false').lower() == 'true'
    
    # Create agent
    agent = JiraToCodeAgent(
        session_id=session_id,
        redis_url=redis_url,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_key=azure_openai_key,
        azure_openai_deployment=azure_openai_deployment,
        discovery_url=discovery_url,
        client_id=client_id,
        agent_url=agent_url,
        enable_policy=enable_policy
    )
    
    logger.info("Jira To Code Agent created successfully")
    return agent


async def run_standalone_test():
    """Run standalone test of code generation from Jira issue"""
    logger.info("=== Jira To Code Agent Standalone Test ===")
    
    # Create agent
    agent = create_jira_agent()
    
    # Test issue
    test_issue = """
    Implement a signup form validation and user registration feature.
    Requirements:
    - Accept email and password from user
    - Validate email format and password strength
    - Create user record in database
    - Send verification email
    - Return 201 status on success
    - Handle errors gracefully with meaningful messages
    - Include comprehensive unit tests
    """
    
    try:
        logger.info("Converting Jira issue to code...")
        result = await agent.convert_issue(
            issue_text=test_issue,
            task_id="test-" + str(uuid4())
        )
        
        logger.info("\n" + "="*80)
        logger.info("CODE GENERATION RESULT")
        logger.info("="*80)
        logger.info(f"From Cache: {result.get('from_cache', False)}")
        logger.info("\n" + "="*80)
        logger.info("GENERATED CODE:")
        logger.info("="*80)
        logger.info(result['code_snippet'])
        logger.info("\n" + "="*80)
        logger.info("EXPLANATION:")
        logger.info("="*80)
        logger.info(result.get('explanation', 'N/A'))
        logger.info("="*80 + "\n")
        
        # Save to file
        output_dir = project_root / 'output' / 'jira_to_code_test'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        code_file = output_dir / 'generated_code.py'
        
        with open(code_file, 'w') as f:
            f.write(result['code_snippet'])
        
        logger.info(f"Code saved to: {code_file}")
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        raise


def start_a2a_server(port: int = 8005):
    """Start A2A server for inter-agent communication
    
    Args:
        port: Server port number
    """
    logger.info(f"Starting Jira To Code A2A Server on port {port}")
    
    # Determine agent URL based on environment or use localhost with specified port
    agent_url = os.getenv('JIRA_TO_CODE_URL')
    if not agent_url:
        # Use localhost with the specified port (accessible by supervisor)
        agent_url = f"http://localhost:{port}"
    
    logger.info(f"Agent URL for discovery: {agent_url}")
    
    # Create agent with proper agent_url
    agent = create_jira_agent(agent_url=agent_url)
    
    # Start server using agent's built-in method
    agent.start(host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Jira To Code Agent")
    parser.add_argument(
        '--mode',
        choices=['test', 'server'],
        default='test',
        help='Run mode: test (standalone) or server (A2A)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8005,
        help='Port for A2A server (default: 8005)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        asyncio.run(run_standalone_test())
    else:
        start_a2a_server(port=args.port)
