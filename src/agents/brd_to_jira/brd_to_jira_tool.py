"""BRD to JIRA Conversion Tool

Wraps BRD to JIRA conversion functionality for the BRD to JIRA Agent.
"""

import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BRDToJiraInput(BaseModel):
    """Input schema for BRD to JIRA conversion tool"""
    brd_json: Dict[str, Any] = Field(
        description="Business Requirements Document in JSON format"
    )
    project_key: str = Field(
        default="PROJ",
        description="JIRA project key"
    )
    include_acceptance_criteria: bool = Field(
        default=True,
        description="Whether to include acceptance criteria in tickets"
    )


class JiraTicket(BaseModel):
    """JIRA ticket structure"""
    key: str = Field(description="JIRA ticket key (auto-generated)")
    summary: str = Field(description="Short ticket summary")
    description: str = Field(description="Detailed description")
    issue_type: str = Field(description="Issue type (Story, Epic, Task, Bug, etc.)")
    story_points: Optional[int] = Field(default=None, description="Story points estimation")
    acceptance_criteria: Optional[list[str]] = Field(default=None, description="Acceptance criteria")
    labels: Optional[list[str]] = Field(default=None, description="Labels for categorization")
    priority: str = Field(default="Medium", description="Priority level")


class BRDToJiraOutput(BaseModel):
    """Output schema for BRD to JIRA conversion"""
    jira_tickets: list[JiraTicket] = Field(
        description="List of generated JIRA tickets"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Conversion metadata"
    )
    from_cache: bool = Field(
        default=False,
        description="Whether result was retrieved from cache"
    )


async def convert_brd_to_jira_function(
    brd_json: Dict[str, Any],
    llm,
    deployment_name: str,
    memory_manager=None,
    jira_config: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    include_acceptance_criteria: bool = True
) -> BRDToJiraOutput:
    """Convert Business Requirements Document to JIRA tickets
    
    Args:
        brd_json: BRD in JSON format
        llm: Azure OpenAI client instance
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching (optional)
        jira_config: JIRA configuration (optional)
        task_id: Task identifier for tracking
        include_acceptance_criteria: Whether to include acceptance criteria
        
    Returns:
        BRDToJiraOutput with generated JIRA tickets
    """
    logger.info(f"Converting BRD to JIRA tickets (task: {task_id})")
    
    if jira_config is None:
        jira_config = {
            'server_url': 'http://localhost:8080',
            'project_key': 'PROJ'
        }
    
    # Check cache first if memory manager is available
    if memory_manager:
        try:
            # Create content-aware cache key to avoid returning wrong cached results
            import hashlib
            brd_hash = hashlib.md5(json.dumps(brd_json, sort_keys=True).encode()).hexdigest()
            cache_key = f"brd_to_jira:{brd_hash}"
            cached = await memory_manager.get_cached_conversion(cache_key)
            if cached:
                logger.info("Conversion retrieved from cache!")
                return BRDToJiraOutput(
                    jira_tickets=cached.get("jira_tickets", []),
                    metadata=cached.get("metadata", {}),
                    from_cache=True
                )
        except Exception as e:
            logger.warning(f"Cache check failed, generating fresh: {str(e)}")
    
    # System prompt for JIRA ticket generation
    system_prompt = (
        "You are an expert JIRA ticket creator. "
        "Given a Business Requirements Document (BRD), convert it into well-structured JIRA tickets. "
        "\n\nRules:\n"
        "1. Each functional requirement should become a Story\n"
        "2. Business goals should become Epics\n"
        "3. Non-functional requirements should become Tasks\n"
        "4. Include clear acceptance criteria for each ticket\n"
        "5. Estimate story points based on complexity (1-13 using Fibonacci scale)\n"
        "6. Use clear, concise language for summaries\n"
        "7. Priorities: Critical, High, Medium, Low\n"
        "\n\nRespond ONLY with valid JSON array of tickets. Do not include markdown formatting."
    )
    
    # Prepare user message
    user_message = (
        f"Convert the following BRD to JIRA tickets for project {jira_config.get('project_key', 'PROJ')}:\n\n"
        f"{json.dumps(brd_json, indent=2)}"
    )
    
    try:
        # Call LLM to convert BRD to JIRA tickets
        # Use LangChain invoke API instead of predict
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse response
        try:
            tickets_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response if wrapped in markdown
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                tickets_data = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JIRA tickets from LLM response: {response_text}")
        
        # Validate and structure tickets
        if not isinstance(tickets_data, list):
            tickets_data = [tickets_data]
        
        jira_tickets = []
        for idx, ticket_data in enumerate(tickets_data):
            ticket = JiraTicket(
                key=f"{jira_config.get('project_key', 'PROJ')}-{idx + 1}",
                summary=ticket_data.get('summary', f"Task {idx + 1}"),
                description=ticket_data.get('description', ''),
                issue_type=ticket_data.get('issue_type', 'Story'),
                story_points=ticket_data.get('story_points'),
                acceptance_criteria=ticket_data.get('acceptance_criteria') if include_acceptance_criteria else None,
                labels=ticket_data.get('labels', []),
                priority=ticket_data.get('priority', 'Medium')
            )
            jira_tickets.append(ticket)
        
        # Cache the result (use content hash for cache key)
        if memory_manager:
            try:
                import hashlib
                brd_hash = hashlib.md5(json.dumps(brd_json, sort_keys=True).encode()).hexdigest()
                cache_key = f"brd_to_jira:{brd_hash}"
                cache_data = {
                    "jira_tickets": [json.loads(t.json()) for t in jira_tickets],
                    "metadata": {
                        "source_brd_title": brd_json.get('title', 'Unknown'),
                        "num_tickets": len(jira_tickets),
                        "project_key": jira_config.get('project_key', 'PROJ')
                    }
                }
                await memory_manager.cache_conversion(cache_key, cache_data)
                logger.info(f"Conversion cached with content hash: {brd_hash[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to cache conversion: {str(e)}")
        
        return BRDToJiraOutput(
            jira_tickets=jira_tickets,
            metadata={
                "source_brd_title": brd_json.get('title', 'Unknown'),
                "num_tickets": len(jira_tickets),
                "project_key": jira_config.get('project_key', 'PROJ')
            }
        )
        
    except Exception as e:
        logger.error(f"BRD to JIRA conversion failed: {str(e)}", exc_info=True)
        raise


def create_brd_to_jira_tool(
    llm,
    deployment_name: str,
    memory_manager=None,
    jira_config: Optional[Dict[str, Any]] = None
):
    """Create BRD to JIRA conversion tool
    
    Args:
        llm: Azure OpenAI LLM client
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching
        jira_config: JIRA configuration
        
    Returns:
        Configured tool for LangChain agent
    """
    from langchain_core.tools import tool
    
    @tool
    async def convert_brd_to_jira(
        brd_json: Dict[str, Any],
        project_key: str = "PROJ",
        include_acceptance_criteria: bool = True
    ) -> Dict[str, Any]:
        """Convert Business Requirements Document to JIRA tickets
        
        Args:
            brd_json: Business Requirements Document in JSON format
            project_key: JIRA project key (default: PROJ)
            include_acceptance_criteria: Include acceptance criteria in tickets
            
        Returns:
            Dictionary with generated JIRA tickets and metadata
        """
        config = jira_config or {'project_key': project_key}
        config['project_key'] = project_key
        
        result = await convert_brd_to_jira_function(
            brd_json=brd_json,
            llm=llm,
            deployment_name=deployment_name,
            memory_manager=memory_manager,
            jira_config=config,
            include_acceptance_criteria=include_acceptance_criteria
        )
        
        return {
            "jira_tickets": [json.loads(t.json()) for t in result.jira_tickets],
            "metadata": result.metadata,
            "from_cache": result.from_cache
        }
    
    return convert_brd_to_jira
