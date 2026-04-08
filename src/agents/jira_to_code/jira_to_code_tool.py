"""Jira To Code Tool

Converts Jira issue descriptions into starter code snippets and tests.
Implements caching and LLM-based generation.
"""

import json
import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from agent_base.tools import ToolClass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class JiraToCodeInput(BaseModel):
    """Input schema for code generation from Jira"""
    issue_text: str = Field(description="Jira issue description to convert to code")


class JiraToCodeOutput(BaseModel):
    """Output schema for code generation"""
    code_snippet: str = Field(description="Generated code snippet")
    explanation: str = Field(description="Explanation of the generated code")
    from_cache: bool = Field(default=False, description="Whether result was retrieved from cache")


async def generate_code_from_jira_function(
    issue_text: str,
    llm,
    deployment_name: str,
    memory_manager=None,
    task_id: Optional[str] = None,
    include_tests: bool = True,
) -> JiraToCodeOutput:
    """Generate code from Jira issue description
    
    Args:
        issue_text: Jira issue description
        llm: Azure OpenAI client instance
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching (optional)
        task_id: Task identifier for tracking
        include_tests: Whether to include test stubs
        
    Returns:
        JiraToCodeOutput with code_snippet, explanation, from_cache
    """
    logger.info(f"Generating code for issue: {issue_text[:100]}...")
    
    # Check cache first if memory manager is available
    if memory_manager:
        try:
            cached = await memory_manager.search_cached_code(
                issue_text=issue_text,
                similarity_threshold=0.85
            )
            if cached:
                logger.info("Code retrieved from cache!")
                return JiraToCodeOutput(
                    code_snippet=cached["code_snippet"],
                    explanation=cached.get("explanation", ""),
                    from_cache=True
                )
        except Exception as e:
            logger.warning(f"Cache check failed, generating fresh: {str(e)}")
    
    # Generate code via LLM
    system_prompt = (
        "You are a senior developer. Given a Jira issue description, produce a concise, "
        "production-ready code skeleton. Include function signatures, important classes, "
        "error handling, and unit tests when appropriate. "
        "\n\nReturn a JSON object with these fields:\n"
        "- code_snippet: The generated code (valid Python/JavaScript)\n"
        "- explanation: Brief explanation of the code structure and approach\n"
        "- notes: Any important notes or considerations\n"
        "\nReturn ONLY valid JSON. No markdown code blocks, no explanations, no additional text."
    )
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": issue_text}
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
        
        data = json.loads(content.strip())
        logger.info(f"Successfully generated code with keys: {list(data.keys())}")
        
        result = JiraToCodeOutput(
            code_snippet=data.get("code_snippet", ""),
            explanation=data.get("explanation", "No explanation provided"),
            from_cache=False
        )
        
        # Cache the result if memory manager available
        if memory_manager and task_id:
            try:
                await memory_manager.cache_code(
                    issue_text=issue_text,
                    code_snippet=result.code_snippet,
                    explanation=result.explanation,
                    task_id=task_id
                )
                logger.info("Code cached successfully")
            except Exception as e:
                logger.warning(f"Failed to cache code: {str(e)}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse code generation JSON: {str(e)}")
        logger.error(f"Raw content:\n{content if 'content' in locals() else 'No content'}")
        # Return fallback
        return JiraToCodeOutput(
            code_snippet=f"# Error parsing LLM response: {str(e)}\n# Raw response:\n# {content if 'content' in locals() else 'No content'}",
            explanation="Error occurred during code generation",
            from_cache=False
        )
    except Exception as e:
        logger.error(f"Failed to generate code: {str(e)}")
        return JiraToCodeOutput(
            code_snippet=f"# Error: {str(e)}",
            explanation=f"Failed to generate code: {str(e)}",
            from_cache=False
        )


def create_jira_to_code_tool(llm, deployment_name: str, memory_manager=None):
    """Create Jira to Code tool with closure over dependencies
    
    Args:
        llm: Azure OpenAI client
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching
        
    Returns:
        Async function ready for ToolClass wrapping
    """
    
    async def tool_function(issue_text: str, task_id: str = None) -> str:
        """Generate code from Jira issue description"""
        result = await generate_code_from_jira_function(
            issue_text=issue_text,
            llm=llm,
            deployment_name=deployment_name,
            memory_manager=memory_manager,
            task_id=task_id
        )
        
        # Return formatted string result
        output = {
            "code_snippet": result.code_snippet,
            "explanation": result.explanation,
            "from_cache": result.from_cache
        }
        return json.dumps(output, indent=2)
    
    return ToolClass(
        name="generate_code_from_jira",
        description=(
            "Generate starter code snippets and tests from Jira issue descriptions. "
            "Analyzes the issue text and produces production-ready code with error handling. "
            "Input: issue_text (string)"
        ),
        func=tool_function,
        args_schema=JiraToCodeInput
    ).get_tool()

