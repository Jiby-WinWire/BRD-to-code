"""Agent Executor for Validation Agent

Entry point for running Validation agent as standalone service
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

from src.agents.validation.validation_agent import ValidationAgent

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


def create_validation_agent(session_id: str = None, agent_url: str = None) -> ValidationAgent:
    """Create Validation Agent instance
    
    Args:
        session_id: Session identifier (generates UUID if not provided)
        agent_url: Override agent URL (defaults to env var or localhost:8002)
        
    Returns:
        Initialized ValidationAgent
    """
    load_environment()
    
    session_id = session_id or str(uuid4())
    logger.info(f"Creating Validation Agent for session: {session_id}")
    
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
    azure_search_index = os.getenv('AZURE_SEARCH_INDEX', 'validation-cache-index')
    azure_openai_embedding_deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
    
    # Optional configuration for policy
    discovery_url = os.getenv('DISCOVERY_API_URL')
    client_id = os.getenv('CLIENT_ID', 'validation-client')
    
    # Use provided agent_url or fall back to environment or default
    if agent_url is None:
        agent_url = os.getenv('VALIDATION_AGENT_URL', 'http://localhost:8002')
    
    # Feature flags
    enable_policy = os.getenv('ENABLE_POLICY', 'false').lower() == 'true'
    enable_caching = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
    
    # Create agent
    agent = ValidationAgent(
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
    
    logger.info("Validation Agent created successfully")
    return agent


async def run_standalone_test():
    """Run standalone test of document validation"""
    logger.info("=== Validation Agent Standalone Test ===")
    
    # Create agent
    agent = create_validation_agent()
    
    # Test document (a BRD)
    test_document = """
    # Customer Relationship Management System - BRD
    
    ## Overview
    Build a comprehensive CRM system for sales teams to track leads, manage customer interactions,
    and generate sales reports. The system should integrate with email providers and provide
    real-time analytics dashboards for sales performance monitoring.
    
    ## Business Goals
    - Increase sales team productivity by 30%
    - Reduce customer response time to under 2 hours
    - Enable data-driven sales forecasting
    - Improve customer retention through better engagement tracking
    - Provide actionable sales insights
    
    ## Functional Requirements
    - Contact management with full customer history
    - Deal pipeline tracking with custom stages
    - Email integration for automatic communication logging
    - Task management and activity tracking
    - Sales reporting and analytics dashboard
    - Opportunity forecasting
    - Integration with calendar systems
    
    ## Non-Functional Requirements
    - System must support 1000+ concurrent users
    - Response time <2 seconds for all operations
    - 99.9% availability SLA
    - Data encryption at rest and in transit
    - GDPR compliance for customer data
    - Daily automated backups
    
    ## Stakeholders
    - Sales Manager: Oversees sales team and performance
    - Sales Representative: Primary end-user for daily operations
    - System Administrator: Manages system deployment and maintenance
    - Finance Team: Manages licensing and budgets
    
    ## Acceptance Criteria
    - All users can log in and access assigned accounts within 5 seconds
    - Sales reports can be generated in under 30 seconds
    - Email sync completes within 5 minutes of receipt
    - System uptime is >= 99.9%
    - No data loss or corruption events
    """
    
    try:
        logger.info("Validating test document...")
        result = await agent.validate_document(
            document_content=test_document,
            task_id="test-" + str(uuid4()),
            document_type="brd"
        )
        
        logger.info("\n" + "="*80)
        logger.info("VALIDATION RESULT")
        logger.info("="*80)
        logger.info(f"Document Title: {result.get('document_title', 'N/A')}")
        logger.info(f"Is Valid: {result.get('is_valid', False)}")
        logger.info(f"Validation Score: {result.get('validation_score', 0)}/100")
        logger.info(f"Issues Found: {len(result.get('issues', []))}")
        logger.info(f"From Cache: {result.get('from_cache', False)}")
        logger.info("\nSummary:")
        logger.info(result.get('summary', 'No summary available'))
        
        if result.get('issues'):
            logger.info("\n" + "="*80)
            logger.info("ISSUES FOUND:")
            logger.info("="*80)
            for i, issue in enumerate(result.get('issues', []), 1):
                logger.info(f"\n{i}. [{issue.get('severity').upper()}] {issue.get('category')}")
                logger.info(f"   Location: {issue.get('location')}")
                logger.info(f"   Description: {issue.get('description')}")
                if issue.get('suggestion'):
                    logger.info(f"   Suggestion: {issue.get('suggestion')}")
        
        logger.info("="*80 + "\n")
        
        # Save to file
        output_dir = project_root / 'output' / 'validation_test'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        json_file = output_dir / 'test_validation.json'
        with open(json_file, 'w') as f:
            # Convert result for JSON serialization
            result_data = {
                'document_title': result.get('document_title'),
                'is_valid': result.get('is_valid'),
                'validation_score': result.get('validation_score'),
                'issues': result.get('issues', []),
                'summary': result.get('summary'),
                'from_cache': result.get('from_cache')
            }
            json.dump(result_data, f, indent=2)
        
        logger.info(f"Validation result saved to: {output_dir}")
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        raise


def start_a2a_server(port: int = 8004):
    """Start A2A server for inter-agent communication
    
    Args:
        port: Server port number
    """
    logger.info(f"Starting Validation A2A Server on port {port}")
    
    # Determine agent URL based on environment or use localhost with specified port
    agent_url = os.getenv('VALIDATION_AGENT_URL')
    if not agent_url:
        # Use localhost with the specified port (accessible by supervisor)
        agent_url = f"http://localhost:{port}"
    
    logger.info(f"Agent URL for discovery: {agent_url}")
    
    # Create agent with proper agent_url
    agent = create_validation_agent(agent_url=agent_url)
    
    # Start server using agent's built-in method
    agent.start(host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validation Agent")
    parser.add_argument(
        '--mode',
        choices=['test', 'server'],
        default='test',
        help='Run mode: test (standalone) or server (A2A)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8004,
        help='Port for A2A server (default: 8004)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        asyncio.run(run_standalone_test())
    else:
        start_a2a_server(port=args.port)
