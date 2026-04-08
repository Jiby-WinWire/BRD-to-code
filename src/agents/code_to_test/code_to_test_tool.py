"""Code-to-Test Tool wrapper for the CodeToTestAgent.

This module exposes a LangChain-compatible tool wrapper over the
existing code and pytest test generation helpers.
"""

import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from agent_base.tools import ToolClass
from typing import Optional

from test_generator import code_to_pytest_tests
from story_to_code import stories_to_fastapi_code

logger = logging.getLogger(__name__)


class CodeToTestInput(BaseModel):
    """Input schema for code/test generation tool."""
    stories: List[Dict[str, Any]] = Field(
        ..., description="List of Jira stories to generate code and tests from"
    )


class CodeToTestOutput(BaseModel):
    """Output schema for code/test generation tool."""
    code_files: Dict[str, str] = Field(
        ..., description="Generated code file contents indexed by path"
    )
    test_files: Dict[str, str] = Field(
        ..., description="Generated pytest test file contents indexed by path"
    )
    note: Optional[str] = Field(
        default=None,
        description="Optional summary note of the generation result"
    )


async def generate_code_and_tests_function(
    stories: List[Dict[str, Any]],
    task_id: str = None
) -> CodeToTestOutput:
    """Generate code and pytest tests from Jira stories.

    Args:
        stories: List of Jira story objects.
        task_id: Optional task identifier for tracking.

    Returns:
        CodeToTestOutput containing code and test files.
    """
    logger.info("Generating application code from stories (%d stories)...", len(stories))
    code_files = stories_to_fastapi_code(stories)
    logger.info("Generating pytest test files from generated code...")
    test_files = code_to_pytest_tests(code_files)

    return CodeToTestOutput(
        code_files=code_files,
        test_files=test_files,
        note=f"Generated {len(code_files)} code files and {len(test_files)} test files."
    )


def create_code_to_test_tool():
    """Create the code-to-test tool wrapper for LangChain agents."""
    async def tool_function(stories: List[Dict[str, Any]]) -> str:
        result = await generate_code_and_tests_function(stories=stories)
        return json.dumps({
            "code_files": result.code_files,
            "test_files": result.test_files,
            "note": result.note
        }, indent=2)

    return ToolClass(
        name="generate_code_and_tests",
        description=(
            "Generate executable FastAPI code files and pytest tests from Jira stories. "
            "Returns the generated code and test files in JSON format."
        ),
        func=tool_function,
        args_schema=CodeToTestInput
    ).get_tool()
