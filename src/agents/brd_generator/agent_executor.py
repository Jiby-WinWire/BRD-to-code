"""Agent Executor for BRD Generator

Entry point for running BRD Generator agent as standalone service
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

from src.agents.brd_generator.brd_generator_agent import BRDGeneratorAgent

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


def create_brd_agent(session_id: str = None, agent_url: str = None) -> BRDGeneratorAgent:
    """Create BRD Generator Agent instance
    
    Args:
        session_id: Session identifier (generates UUID if not provided)
        agent_url: Override agent URL (defaults to env var or localhost:8001)
        
    Returns:
        Initialized BRDGeneratorAgent
    """
    load_environment()
    
    session_id = session_id or str(uuid4())
    logger.info(f"Creating BRD Generator Agent for session: {session_id}")
    
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
    
    # Optional configuration for caching
    azure_search_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
    azure_search_key = os.getenv('AZURE_SEARCH_KEY')
    azure_search_index = os.getenv('AZURE_SEARCH_INDEX', 'brd-cache-index')
    azure_openai_embedding_deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
    
    # Optional configuration for policy
    discovery_url = os.getenv('DISCOVERY_API_URL')
    client_id = os.getenv('CLIENT_ID', 'brd-generator-client')
    
    # Use provided agent_url or fall back to environment or default
    if agent_url is None:
        agent_url = os.getenv('BRD_GENERATOR_URL', 'http://localhost:8001')
    
    # Feature flags
    enable_policy = os.getenv('ENABLE_POLICY', 'false').lower() == 'true'
    enable_caching = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
    
    # Create agent
    agent = BRDGeneratorAgent(
        session_id=session_id,
        redis_url=redis_url,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_key=azure_openai_key,
        azure_openai_deployment=azure_openai_deployment,
        azure_search_endpoint=azure_search_endpoint,
        azure_search_key=azure_search_key,
        azure_search_index=azure_search_index,
        azure_openai_embedding_deployment=azure_openai_embedding_deployment,
        discovery_url=discovery_url,
        client_id=client_id,
        agent_url=agent_url,
        enable_policy=enable_policy,
        enable_caching=enable_caching
    )
    
    logger.info("BRD Generator Agent created successfully")
    return agent


async def run_standalone_test():
    """Run standalone test of BRD generation"""
    logger.info("=== BRD Generator Agent Standalone Test ===")
    
    # Create agent
    agent = create_brd_agent()
    
    # Test prompt
    test_prompt = """
    Create a BRD for a customer relationship management (CRM) system 
    that helps sales teams track leads, manage customer interactions, 
    and generate sales reports. The system should include contact management,
    deal pipeline tracking, email integration, and analytics dashboard.
    """
    
    try:
        logger.info("Generating BRD from test prompt...")
        result = await agent.generate_brd(
            user_prompt=test_prompt,
            task_id="test-" + str(uuid4())
        )
        
        logger.info("\n" + "="*80)
        logger.info("BRD GENERATION RESULT")
        logger.info("="*80)
        logger.info(f"From Cache: {result.get('from_cache', False)}")
        logger.info(f"Similarity Score: {result.get('similarity_score', 0.0):.3f}")
        logger.info("\nBRD Title: " + result['brd_json'].get('title', 'N/A'))
        logger.info("\n" + "="*80)
        logger.info("MARKDOWN OUTPUT:")
        logger.info("="*80)
        logger.info(result.get('brd_markdown', 'No markdown generated'))
        logger.info("="*80 + "\n")
        
        # Save to file
        output_dir = project_root / 'output' / 'brd_test'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_file = output_dir / 'test_brd.json'
        md_file = output_dir / 'test_brd.md'
        
        import json
        with open(json_file, 'w') as f:
            json.dump(result['brd_json'], f, indent=2)
        
        with open(md_file, 'w') as f:
            f.write(result.get('brd_markdown', ''))
        
        logger.info(f"BRD saved to: {output_dir}")
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        raise


def start_a2a_server(port: int = 8001):
    """Start A2A server for inter-agent communication
    
    Args:
        port: Server port number
    """
    logger.info(f"Starting BRD Generator A2A Server on port {port}")
    
    # Create agent
    agent = create_brd_agent()
    
    # Start server using agent's built-in method
    agent.start(host="0.0.0.0", port=port)



if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BRD Generator Agent")
    parser.add_argument(
        '--mode',
        choices=['test', 'server'],
        default='test',
        help='Run mode: test (standalone) or server (A2A)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8001,
        help='Port for A2A server (default: 8001)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        asyncio.run(run_standalone_test())
    else:
        start_a2a_server(port=args.port)
