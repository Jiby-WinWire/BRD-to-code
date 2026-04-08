"""Validation Tool for Validation Agent

Wraps validation functionality as a LangChain tool using ToolClass.
"""

import json
import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationInput(BaseModel):
    """Input schema for validation tool"""
    document_content: str = Field(
        description="BRD or requirements document content to validate"
    )
    document_type: str = Field(
        default="brd",
        description="Type of document: brd, requirements, specification"
    )
    validation_scope: Optional[str] = Field(
        default=None,
        description="Specific validation scope: completeness, consistency, clarity, all"
    )


class ValidationIssue(BaseModel):
    """Single validation issue"""
    severity: str = Field(description="critical, warning, info")
    category: str = Field(description="Issue category")
    description: str = Field(description="Issue description")
    location: str = Field(description="Location in document")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")


class ValidationOutput(BaseModel):
    """Output schema for validation"""
    document_title: Optional[str] = Field(
        default=None,
        description="Extracted document title"
    )
    is_valid: bool = Field(
        description="Overall validation result"
    )
    validation_score: float = Field(
        description="Validation score 0-100"
    )
    issues: list[ValidationIssue] = Field(
        description="List of validation issues"
    )
    summary: str = Field(
        description="Summary of validation results"
    )
    from_cache: bool = Field(
        default=False,
        description="Whether result was retrieved from cache"
    )
    similarity_score: float = Field(
        default=0.0,
        description="Similarity score if from cache"
    )


async def validate_document_function(
    document_content: str,
    llm,
    deployment_name: str,
    memory_manager=None,
    task_id: Optional[str] = None,
    document_type: str = "brd",
    validation_scope: Optional[str] = None
) -> ValidationOutput:
    """Validate document content
    
    Args:
        document_content: Document text to validate
        llm: Azure OpenAI client instance
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching (optional)
        task_id: Task identifier for tracking
        document_type: Type of document being validated
        validation_scope: Specific scope of validation
        
    Returns:
        ValidationOutput with validation results
    """
    logger.info(f"Validating {document_type} document (first 100 chars): {document_content[:100]}...")
    
    # Check cache first if memory manager is available
    if memory_manager:
        try:
            cached = await memory_manager.search_cached_validation(
                document_content=document_content,
                similarity_threshold=0.85
            )
            if cached:
                logger.info("Validation result retrieved from cache!")
                return ValidationOutput(
                    document_title=cached.get("document_title"),
                    is_valid=cached.get("is_valid", True),
                    validation_score=cached.get("validation_score", 0.0),
                    issues=[ValidationIssue(**issue) for issue in cached.get("issues", [])],
                    summary=cached.get("summary", ""),
                    from_cache=True,
                    similarity_score=cached.get("similarity_score", 0.0)
                )
        except Exception as e:
            logger.warning(f"Cache check failed, validating fresh: {str(e)}")
    
    # Build validation prompt
    scope_instruction = ""
    if validation_scope:
        scope_instruction = f"\nFocus validation on: {validation_scope}"
    
    system_prompt = (
        f"You are an expert {document_type.upper()} validator and requirements analyst. "
        f"Your role is to thoroughly validate the provided {document_type} document for quality, completeness, and consistency.\n"
        f"\nValidation Criteria:\n"
        f"1. **Completeness**: Does it include all required sections?\n"
        f"2. **Consistency**: Are there contradictions or inconsistencies?\n"
        f"3. **Clarity**: Is the language clear and unambiguous?\n"
        f"4. **Measurability**: Are requirements specific and measurable?\n"
        f"5. **Traceability**: Can requirements be traced to business goals?\n"
        f"6. **Feasibility**: Are the requirements technically feasible?\n"
        f"{scope_instruction}\n"
        f"\nProvide your analysis in JSON format with this structure:\n"
        f"{{\n"
        f'  "document_title": "extracted title or null",\n'
        f'  "is_valid": true/false,\n'
        f'  "validation_score": 0-100,\n'
        f'  "issues": [\n'
        f'    {{\n'
        f'      "severity": "critical|warning|info",\n'
        f'      "category": "completeness|consistency|clarity|measurability|traceability|feasibility",\n'
        f'      "description": "detailed issue description",\n'
        f'      "location": "section or line reference",\n'
        f'      "suggestion": "suggested improvement or null"\n'
        f'    }}\n'
        f'  ],\n'
        f'  "summary": "brief summary of validation results"\n'
        f"}}\n"
        f"\nReturn ONLY valid JSON. No markdown code blocks, no explanations."
    )
    
    try:
        # Generate validation results using LangChain invoke
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please validate this {document_type} document:\n\n{document_content}"}
        ]
        
        response = llm.invoke(messages)
        content = response.content
        
        logger.debug(f"Raw LLM validation response:\n{content}")
        
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
        
        validation_json = json.loads(content.strip())
        logger.info(f"Successfully generated validation result. Score: {validation_json.get('validation_score', 0)}/100")
        
        # Convert issues to ValidationIssue objects
        issues = [ValidationIssue(**issue) for issue in validation_json.get("issues", [])]
        
        # Cache the result if memory manager available
        if memory_manager and task_id:
            try:
                await memory_manager.cache_validation(
                    document_content=document_content,
                    validation_result=validation_json,
                    task_id=task_id
                )
                logger.info("Validation result cached successfully")
            except Exception as e:
                logger.warning(f"Failed to cache validation result: {str(e)}")
        
        return ValidationOutput(
            document_title=validation_json.get("document_title"),
            is_valid=validation_json.get("is_valid", True),
            validation_score=validation_json.get("validation_score", 0.0),
            issues=issues,
            summary=validation_json.get("summary", ""),
            from_cache=False,
            similarity_score=1.0
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse validation JSON: {str(e)}")
        logger.error(f"Raw content:\n{content if 'content' in locals() else 'No content'}")
        raise ValueError(f"LLM did not return valid JSON for validation. Error: {e}")
    except Exception as e:
        logger.error(f"Failed to validate document: {str(e)}")
        raise ValueError(f"Failed to validate document: {e}")


# Create the tool wrapper (will be instantiated in agent)
def create_validation_tool(llm, deployment_name: str, memory_manager=None):
    """Create validation tool with closure over dependencies
    
    Args:
        llm: Azure OpenAI client
        deployment_name: Model deployment name
        memory_manager: Memory manager for caching
        
    Returns:
        Async function ready for ToolClass wrapping
    """
    from mylibs.agent_base.tools import ToolClass
    
    async def tool_function(
        document_content: str, 
        task_id: str = None,
        document_type: str = "brd",
        validation_scope: str = None
    ) -> str:
        """Validate document content"""
        result = await validate_document_function(
            document_content=document_content,
            llm=llm,
            deployment_name=deployment_name,
            memory_manager=memory_manager,
            task_id=task_id,
            document_type=document_type,
            validation_scope=validation_scope
        )
        
        return json.dumps({
            "document_title": result.document_title,
            "is_valid": result.is_valid,
            "validation_score": result.validation_score,
            "issues": [issue.dict() for issue in result.issues],
            "summary": result.summary,
            "from_cache": result.from_cache
        }, indent=2)
    
    # Wrap with ToolClass
    tool = ToolClass(
        name="validate_document",
        description="Validate and analyze BRD or requirements documents for completeness, consistency, and clarity",
        func=tool_function,
        input_schema={
            "type": "object",
            "properties": {
                "document_content": {
                    "type": "string",
                    "description": "BRD or requirements document content to validate"
                },
                "document_type": {
                    "type": "string",
                    "description": "Type of document: brd, requirements, specification",
                    "enum": ["brd", "requirements", "specification"]
                },
                "validation_scope": {
                    "type": "string",
                    "description": "Optional validation scope: completeness, consistency, clarity, all"
                }
            },
            "required": ["document_content"]
        }
    )
    
    return tool
