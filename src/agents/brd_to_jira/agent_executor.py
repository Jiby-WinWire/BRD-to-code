"""Agent Executor for BRD to JIRA Agent

Entry point for running BRD to JIRA agent as standalone service
or within A2A server.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.brd_to_jira.brd_to_jira_agent_standalone import BRDToJiraAgent

# Try to import FastAPI for server mode
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global agent instance
agent_instance: BRDToJiraAgent = None

# FastAPI app (if available)
if HAS_FASTAPI:
    app = FastAPI(
        title="BRD to JIRA Agent",
        description="Converts Business Requirements Documents to JIRA tickets",
        version="1.0.0"
    )


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


def create_brd_to_jira_agent(session_id: str = None, agent_url: str = None) -> BRDToJiraAgent:
    """Create BRD to JIRA Agent instance
    
    Args:
        session_id: Session identifier (generates UUID if not provided)
        agent_url: Override agent URL (defaults to env var or localhost:8002)
        
    Returns:
        Initialized BRDToJiraAgent
    """
    load_environment()
    
    session_id = session_id or str(uuid4())
    logger.info(f"Creating BRD to JIRA Agent for session: {session_id}")
    
    # Required configuration
    redis_url = get_required_env('REDIS_URL', 'redis://localhost:6379')
    
    # Use real Redis (no fallback to FakeRedis)
    use_fake_redis = os.getenv('USE_FAKE_REDIS', 'false').lower()
    if use_fake_redis == 'false':
        # Use real Redis
        logger.info(f"Connecting to Redis at: {redis_url}")
        use_fake_redis = False
    else:
        use_fake_redis = use_fake_redis == 'true'
    
    # Override redis_url for fakeredis if explicitly requested
    if use_fake_redis:
        redis_url = 'fakeredis://localhost'
        logger.info("Using FakeRedis (explicitly requested via USE_FAKE_REDIS=true)")
    
    # Azure OpenAI configuration
    azure_openai_endpoint = get_required_env('AZURE_OPENAI_ENDPOINT')
    azure_openai_key = get_required_env('AZURE_OPENAI_KEY', os.getenv('AZURE_OPENAI_API_KEY'))
    azure_openai_deployment = get_required_env(
        'AZURE_OPENAI_DEPLOYMENT',
        os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt4o_mktgenai')
    )
    azure_openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2023-05-15')
    
    # JIRA configuration
    jira_server_url = os.getenv('JIRA_SERVER_URL', 'http://localhost:8080')
    jira_username = os.getenv('JIRA_USERNAME')
    jira_api_token = os.getenv('JIRA_API_TOKEN')
    jira_project_key = os.getenv('JIRA_PROJECT_KEY', 'PROJ')
    
    # Agent configuration
    agent_url_override = agent_url or os.getenv('AGENT_URL', 'http://localhost:8002')
    enable_caching = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
    
    logger.info(f"Azure OpenAI configured with deployment: {azure_openai_deployment}")
    logger.info(f"JIRA configured with server: {jira_server_url}")
    logger.info(f"Caching: {'enabled' if enable_caching else 'disabled'}")
    
    # Create agent
    agent = BRDToJiraAgent(
        session_id=session_id,
        redis_url=redis_url,
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_key=azure_openai_key,
        azure_openai_deployment=azure_openai_deployment,
        azure_openai_api_version=azure_openai_api_version,
        jira_server_url=jira_server_url,
        jira_username=jira_username,
        jira_api_token=jira_api_token,
        jira_project_key=jira_project_key,
        agent_url=agent_url_override,
        enable_caching=enable_caching
    )
    
    return agent


async def main():
    """Main entry point for BRD to JIRA agent"""
    global agent_instance
    try:
        agent_instance = create_brd_to_jira_agent()
        logger.info("✅ BRD to JIRA Agent successfully initialized")
        logger.info(f"Agent name: {agent_instance.agent_name}")
        logger.info(f"Session ID: {agent_instance.session_id}")
        
        # Example: Test the agent with sample BRD
        sample_brd = {
            "title": "Customer Management Portal",
            "description": "A web-based portal for managing customer interactions",
            "business_goals": [
                "Improve customer engagement by 30%",
                "Reduce support ticket resolution time by 50%"
            ],
            "functional_requirements": [
                "User authentication with SSO support",
                "Customer profile management",
                "Support ticket creation and tracking",
                "Real-time notifications"
            ],
            "non_functional_requirements": [
                "Support 10,000 concurrent users",
                "99.9% uptime SLA",
                "Response time < 200ms for 95th percentile"
            ]
        }
        
        logger.info("Testing BRD to JIRA conversion with sample BRD...")
        # The agent is ready to receive requests via A2A protocol
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}", exc_info=True)
        sys.exit(1)


def start_server(host: str = "0.0.0.0", port: int = 8002):
    """Start FastAPI server for BRD to JIRA Agent
    
    Args:
        host: Server host (default: 0.0.0.0)
        port: Server port (default: 8002)
    """
    global agent_instance
    
    if not HAS_FASTAPI:
        logger.error("FastAPI not available. Install with: pip install fastapi uvicorn")
        sys.exit(1)
    
    # Initialize agent
    agent_instance = create_brd_to_jira_agent()
    
    # Setup endpoints
    setup_api_endpoints()
    
    logger.info(f"🚀 Starting BRD to JIRA Agent Server on {host}:{port}")
    logger.info(f"📚 API Docs: http://{host}:{port}/docs")
    logger.info(f"🔄 ReDoc: http://{host}:{port}/redoc")
    
    # Start server
    uvicorn.run(app, host=host, port=port)


def setup_api_endpoints():
    """Setup FastAPI endpoints for the agent"""
    
    @app.get("/.well-known/agent.json", tags=["Agent"])
    async def agent_card():
        """Get agent card metadata (well-known endpoint)
        
        Returns:
            Agent card with capabilities, skills, and metadata
        """
        return {
            "id": "brd-to-jira",
            "name": "BRD to JIRA Agent",
            "version": "1.0.0",
            "displayName": "BRD to JIRA Converter",
            "description": "Converts Business Requirements Documents to structured JIRA tickets",
            "provider": "BRD-to-Code",
            "url": agent_instance.agent_url if agent_instance else "http://localhost:8002",
            "owner": {
                "name": "WinWire Team",
                "email": "team@example.com"
            },
            "capabilities": [
                "BRD Parsing",
                "JIRA Ticket Generation",
                "Semantic Conversion",
                "Story Point Estimation"
            ],
            "skills": [
                {
                    "name": "convert_brd_to_jira",
                    "description": "Convert Business Requirements Document to JIRA tickets",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "brd_json": {
                                "type": "object",
                                "description": "Business Requirements Document in JSON format"
                            },
                            "project_key": {
                                "type": "string",
                                "description": "JIRA project key",
                                "default": "PROJ"
                            }
                        },
                        "required": ["brd_json"]
                    },
                    "outputSchema": {
                        "type": "object",
                        "properties": {
                            "jira_tickets": {
                                "type": "array",
                                "description": "Generated JIRA tickets"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Conversion metadata"
                            }
                        }
                    }
                }
            ],
            "supportedInputModes": ["text", "json"],
            "supportedOutputModes": ["json"],
            "authentication": {
                "required": False,
                "type": "none"
            },
            "rateLimit": {
                "requestsPerMinute": 100,
                "tokensPerMinute": 90000
            },
            "serviceEndpoints": {
                "convert": "/convert",
                "status": "/status/{task_id}",
                "health": "/health"
            }
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "agent": agent_instance.agent_name if agent_instance else "not-initialized",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/convert", tags=["Conversion"])
    async def convert_brd_to_jira(brd_json: dict, project_key: str = "PROJ"):
        """Convert BRD to JIRA tickets
        
        Args:
            brd_json: Business Requirements Document in JSON format
            project_key: JIRA project key (default: PROJ)
            
        Returns:
            Generated JIRA tickets
        """
        if not agent_instance:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        try:
            result = await agent_instance.convert_brd_to_jira(brd_json=brd_json)
            return {
                "success": True,
                "data": result,
                "message": f"Generated {len(result.get('jira_tickets', []))} JIRA tickets"
            }
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/status/{task_id}", tags=["Status"])
    async def get_task_status(task_id: str):
        """Get task status
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status information
        """
        if not agent_instance:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        try:
            status = await agent_instance.memory_manager.pull_jira_status(task_id)
            if not status:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            return {
                "success": True,
                "data": {
                    "task_id": status.task_id,
                    "status": status.status,
                    "session_id": status.session_id,
                    "num_tickets": len(status.jira_tickets or []),
                    "error": status.error_message,
                    "start_time": status.start_time,
                    "end_time": status.end_time
                }
            }
        except Exception as e:
            logger.error(f"Failed to get status: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BRD to JIRA Agent")
    parser.add_argument(
        '--mode',
        choices=['test', 'server'],
        default='test',
        help='Run mode: test (default) or server'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Server host (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8002,
        help='Server port (default: 8002)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        logger.info("Running in TEST mode")
        asyncio.run(main())
    elif args.mode == 'server':
        logger.info("Running in SERVER mode")
        start_server(host=args.host, port=args.port)
    else:
        asyncio.run(main())
