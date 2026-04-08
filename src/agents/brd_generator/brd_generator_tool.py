"""BRD Generation Tool for BRD Generator Agent

Wraps BRD generation functionality as a LangChain tool using ToolClass.
"""

import json
import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BRDGenerationInput(BaseModel):
    """Input schema for BRD generation tool"""
    user_prompt: str = Field(
        description="Natural language description of the software requirements"
    )
    include_markdown: bool = Field(
        default=True,
        description="Whether to also generate markdown format"
    )


class BRDGenerationOutput(BaseModel):
    """Output schema for BRD generation"""
    brd_json: Dict[str, Any] = Field(
        description="Structured BRD in JSON format"
    )
    brd_markdown: Optional[str] = Field(
        default=None,
        description="BRD in markdown format"
    )
    from_cache: bool = Field(
        default=False,
        description="Whether result was retrieved from cache"
    )
    similarity_score: float = Field(
        default=0.0,
        description="Similarity score if from cache"
    )


async def generate_brd_function(
    user_prompt: str,
    llm,
    deployment_name: str,
    memory_manager=None,
    task_id: Optional[str] = None,
    include_markdown: bool = True
) -> BRDGenerationOutput:
    """Generate Business Requirements Document from user prompt
    
    Args:
        user_prompt: Natural language requirements description
        llm: Azure OpenAI client instance
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching (optional)
        task_id: Task identifier for tracking
        include_markdown: Whether to generate markdown format
        
    Returns:
        BRDGenerationOutput with JSON and markdown BRD
    """
    logger.info(f"Generating BRD for prompt: {user_prompt[:100]}...")
    
    # Check cache first if memory manager is available
    if memory_manager:
        try:
            cached = await memory_manager.search_cached_brd(
                user_prompt=user_prompt,
                similarity_threshold=0.85
            )
            if cached:
                logger.info("BRD retrieved from cache!")
                return BRDGenerationOutput(
                    brd_json=json.loads(cached["brd_json"]),
                    brd_markdown=cached.get("brd_markdown"),
                    from_cache=True,
                    similarity_score=cached.get("similarity_score", 0.0)
                )
        except Exception as e:
            logger.warning(f"Cache check failed, generating fresh: {str(e)}")
    
    # Generate BRD JSON
    system_prompt_json = (
        "You are a senior business analyst with expertise in software requirements gathering. "
        "Given a user request, generate a comprehensive Business Requirement Document (BRD) in JSON format. "
        "\n\nThe BRD MUST include these sections:\n"
        "- title: Clear, concise project title\n"
        "- description: High-level overview of the project (2-3 paragraphs)\n"
        "- business_goals: List of strategic business objectives\n"
        "- functional_requirements: Detailed list of functional capabilities\n"
        "- non_functional_requirements: Performance, security, scalability requirements\n"
        "- stakeholders: List of key stakeholders and their roles\n"
        "- acceptance_criteria: Measurable success criteria\n"
        "- assumptions: Key assumptions and dependencies\n"
        "- constraints: Technical, budget, timeline constraints\n"
        "- risks: Potential risks and mitigation strategies\n"
        "\nReturn ONLY valid JSON. No markdown code blocks, no explanations, no additional text."
    )
    
    try:
        # Generate JSON BRD using LangChain invoke
        messages = [
            {"role": "system", "content": system_prompt_json},
            {"role": "user", "content": user_prompt}
        ]
        
        response = llm.invoke(messages)
        content = response.content
        
        logger.debug(f"Raw LLM response:\n{content}")
        
        # Extract JSON from markdown if present
        if "```json" in content or "```" in content:
            logger.info("Detected markdown code block, extracting JSON...")
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
        
        brd_json = json.loads(content.strip())
        logger.info(f"Successfully generated BRD JSON with keys: {list(brd_json.keys())}")
        
        # Generate markdown format if requested
        brd_markdown = None
        if include_markdown:
            brd_markdown = await generate_brd_markdown(
                brd_json=brd_json,
                llm=llm,
                deployment_name=deployment_name
            )
        
        # Cache the result if memory manager available
        if memory_manager and task_id:
            try:
                await memory_manager.cache_brd(
                    user_prompt=user_prompt,
                    brd_json=brd_json,
                    brd_markdown=brd_markdown or "",
                    task_id=task_id
                )
                logger.info("BRD cached successfully")
            except Exception as e:
                logger.warning(f"Failed to cache BRD: {str(e)}")
        
        return BRDGenerationOutput(
            brd_json=brd_json,
            brd_markdown=brd_markdown,
            from_cache=False,
            similarity_score=1.0
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse BRD JSON: {str(e)}")
        logger.error(f"Raw content:\n{content if 'content' in locals() else 'No content'}")
        raise ValueError(f"LLM did not return valid JSON for BRD. Error: {e}")
    except Exception as e:
        logger.error(f"Failed to generate BRD: {str(e)}")
        raise ValueError(f"Failed to generate BRD from prompt: {e}")


async def generate_brd_markdown(
    brd_json: Dict[str, Any],
    llm,
    deployment_name: str
) -> str:
    """Convert BRD JSON to well-formatted markdown
    
    Args:
        brd_json: Structured BRD JSON
        llm: Azure OpenAI client
        deployment_name: Model deployment name
        
    Returns:
        Markdown formatted BRD
    """
    system_prompt_md = (
        "You are a technical writer. Convert this BRD JSON into a well-formatted, "
        "professional markdown document. Use proper headings, lists, tables where appropriate. "
        "Make it readable and visually appealing. Return ONLY the markdown text."
    )
    
    try:
        messages = [
            {"role": "system", "content": system_prompt_md},
            {"role": "user", "content": f"Convert this BRD to markdown:\n\n{json.dumps(brd_json, indent=2)}"}
        ]
        
        response = llm.invoke(messages)
        markdown = response.content.strip()
        
        # Remove markdown code block wrapper if present
        if markdown.startswith("```markdown"):
            markdown = re.sub(r'^```markdown\s*', '', markdown)
            markdown = re.sub(r'\s*```$', '', markdown)
        elif markdown.startswith("```"):
            markdown = re.sub(r'^```\s*', '', markdown)
            markdown = re.sub(r'\s*```$', '', markdown)
        
        logger.info("Successfully generated BRD markdown")
        return markdown.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate markdown: {str(e)}")
        # Fallback: create basic markdown from JSON
        return json_to_markdown_fallback(brd_json)


def json_to_markdown_fallback(brd_json: Dict[str, Any]) -> str:
    """Fallback markdown generator from BRD JSON
    
    Args:
        brd_json: BRD in JSON format
        
    Returns:
        Basic markdown representation
    """
    md = []
    
    # Title
    md.append(f"# {brd_json.get('title', 'Business Requirements Document')}\n")
    
    # Description
    if 'description' in brd_json:
        md.append("## Overview\n")
        md.append(f"{brd_json['description']}\n")
    
    # Business Goals
    if 'business_goals' in brd_json:
        md.append("## Business Goals\n")
        for goal in brd_json['business_goals']:
            md.append(f"- {goal}")
        md.append("")
    
    # Functional Requirements
    if 'functional_requirements' in brd_json:
        md.append("## Functional Requirements\n")
        for req in brd_json['functional_requirements']:
            md.append(f"- {req}")
        md.append("")
    
    # Non-Functional Requirements
    if 'non_functional_requirements' in brd_json:
        md.append("## Non-Functional Requirements\n")
        for req in brd_json['non_functional_requirements']:
            md.append(f"- {req}")
        md.append("")
    
    # Stakeholders
    if 'stakeholders' in brd_json:
        md.append("## Stakeholders\n")
        for stakeholder in brd_json['stakeholders']:
            md.append(f"- {stakeholder}")
        md.append("")
    
    # Other sections
    for key in ['assumptions', 'constraints', 'risks', 'acceptance_criteria']:
        if key in brd_json:
            title = key.replace('_', ' ').title()
            md.append(f"## {title}\n")
            items = brd_json[key]
            if isinstance(items, list):
                for item in items:
                    md.append(f"- {item}")
            else:
                md.append(str(items))
            md.append("")
    
    return "\n".join(md)


# Create the tool wrapper (will be instantiated in agent)
def create_brd_generation_tool(llm, deployment_name: str, memory_manager=None):
    """Create BRD generation tool with closure over dependencies
    
    Args:
        llm: Azure OpenAI client
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching
        
    Returns:
        Async function ready for ToolClass wrapping
    """
    from mylibs.agent_base.tools import ToolClass
    
    async def tool_function(user_prompt: str, task_id: str = None) -> str:
        """Generate BRD from user prompt"""
        result = await generate_brd_function(
            user_prompt=user_prompt,
            llm=llm,
            deployment_name=deployment_name,
            memory_manager=memory_manager,
            task_id=task_id,
            include_markdown=True
        )
        
        # Return formatted string result
        output = {
            "brd_json": result.brd_json,
            "brd_markdown": result.brd_markdown,
            "from_cache": result.from_cache
        }
        return json.dumps(output, indent=2)
    
    return ToolClass(
        name="generate_brd",
        description=(
            "Generate a comprehensive Business Requirements Document (BRD) from "
            "natural language requirements. Returns structured JSON and markdown formats. "
            "Input: user_prompt (string)"
        ),
        func=tool_function,
        args_schema=BRDGenerationInput
    ).get_tool()
