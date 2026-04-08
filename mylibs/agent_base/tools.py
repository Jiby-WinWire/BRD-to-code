from langchain_core.tools import tool, Tool
from typing import Callable, Optional, Any

class ToolClass:
    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        return_direct: bool = False,
        args_schema: Optional[Any] = None
    ):
        """
        Base wrapper for LangGraph-compatible tools.

        :param func: The function to wrap as a tool
        :param name: Name of the tool
        :param description: Description of the tool
        :param return_direct: Whether to return immediately after using this tool
        :param args_schema: Optional custom Pydantic schema for arguments
        """
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or f"Tool: {self.name}"
        self.return_direct = return_direct
        self.args_schema = args_schema

    def get_tool(self) -> Tool:
        """
        Returns the function wrapped as a LangChain Tool instance
        """
        return Tool.from_function(
            func=self.func,
            name=self.name,
            description=self.description,
            return_direct=self.return_direct,
            args_schema=self.args_schema
        )
