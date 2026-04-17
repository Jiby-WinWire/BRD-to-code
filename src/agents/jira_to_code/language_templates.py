"""
Language-specific code generation templates and prompts.
Supports multiple programming languages and frameworks.
"""

from typing import Dict

# Language definitions with file extensions, frameworks, and syntax info
LANGUAGE_CONFIGS = {
    "python": {
        "name": "Python",
        "enabled": True,
        "framework": "FastAPI",
        "extensions": [".py"],
        "test_framework": "pytest",
        "description": "FastAPI backend with Pydantic models"
    },
    "csharp": {
        "name": "C#",
        "enabled": True,
        "framework": "ASP.NET Core",
        "extensions": [".cs"],
        "test_framework": "NUnit",
        "description": "ASP.NET Core backend with Entity Framework"
    },
    "dotnet": {
        "name": ".NET",
        "enabled": True,
        "framework": "ASP.NET Core",
        "extensions": [".cs"],
        "test_framework": "xUnit",
        "description": ".NET 8 ASP.NET Core Web API"
    }
}


def get_system_prompt_for_language(language: str) -> str:
    """
    Get language-specific system prompt for code generation.
    
    Args:
        language: Programming language (python, csharp, dotnet)
        
    Returns:
        Formatted system prompt for LLM
    """
    language = language.lower().strip()
    
    if language in ["python"]:
        return get_python_system_prompt()
    elif language in ["csharp", "c#"]:
        return get_csharp_system_prompt()
    elif language in ["dotnet", ".net"]:
        return get_dotnet_system_prompt()
    else:
        return get_python_system_prompt()  # Default to Python


def get_python_system_prompt() -> str:
    """System prompt for Python/FastAPI code generation"""
    return (
        "You are an expert Python/FastAPI developer. Given a Jira issue description, "
        "produce production-ready Python FastAPI code. "
        "\n\nGenerate code with these characteristics:\n"
        "- Use FastAPI framework for REST APIs\n"
        "- Use Pydantic for data models and validation\n"
        "- Include proper exception handling and logging\n"
        "- Add type hints to all functions\n"
        "- Include docstrings for classes and functions\n"
        "- Implement proper HTTP status codes\n"
        "- Include unit tests using pytest\n"
        "\n\nReturn a JSON object with these fields:\n"
        "- code_snippet: The generated Python code (valid, executable FastAPI code)\n"
        "- explanation: Brief explanation of the code structure and approach\n"
        "- test_code: Basic pytest tests (optional)\n"
        "- notes: Any important notes or considerations\n"
        "\nReturn ONLY valid JSON. No markdown code blocks, no explanations, no additional text."
    )


def get_csharp_system_prompt() -> str:
    """System prompt for C#/ASP.NET Core code generation"""
    return (
        "You are an expert C# developer with deep knowledge of ASP.NET Core. "
        "Given a Jira issue description, produce production-ready C# ASP.NET Core code. "
        "\n\nGenerate code with these characteristics:\n"
        "- Use ASP.NET Core 8 framework for REST APIs\n"
        "- Use Entity Framework Core for data access\n"
        "- Include proper dependency injection\n"
        "- Add comprehensive exception handling and logging\n"
        "- Include XML documentation comments\n"
        "- Implement proper HTTP status codes and responses\n"
        "- Use async/await patterns throughout\n"
        "- Create controller classes with proper routing\n"
        "- Include NUnit unit tests\n"
        "\n\nReturn a JSON object with these fields:\n"
        "- code_snippet: The generated C# code (valid, executable ASP.NET Core code)\n"
        "- explanation: Brief explanation of the code structure and approach\n"
        "- test_code: Basic NUnit tests (optional)\n"
        "- project_structure: Required project structure and dependencies\n"
        "- notes: Important notes or considerations\n"
        "\nReturn ONLY valid JSON. No markdown code blocks, no explanations, no additional text."
    )


def get_dotnet_system_prompt() -> str:
    """System prompt for .NET/ASP.NET Core code generation"""
    return (
        "You are an expert .NET developer with expertise in .NET 8 and ASP.NET Core. "
        "Given a Jira issue description, produce production-ready .NET code. "
        "\n\nGenerate code with these characteristics:\n"
        "- Use .NET 8 ASP.NET Core framework for REST APIs\n"
        "- Use Entity Framework Core 8 for data access\n"
        "- Implement clean architecture principles\n"
        "- Include dependency injection and configuration patterns\n"
        "- Add comprehensive exception handling and structured logging\n"
        "- Use nullable reference types\n"
        "- Implement proper async operations\n"
        "- Create minimal API endpoints or controller-based APIs\n"
        "- Include xUnit test cases\n"
        "- Follow Microsoft naming conventions and best practices\n"
        "\n\nReturn a JSON object with these fields:\n"
        "- code_snippet: The generated .NET C# code (valid, executable)\n"
        "- explanation: Brief explanation of the code structure and approach\n"
        "- test_code: Basic xUnit tests (optional)\n"
        "- csproj_content: Required .csproj dependencies and configuration\n"
        "- appsettings: Configuration template (if needed)\n"
        "- notes: Important notes or considerations\n"
        "\nReturn ONLY valid JSON. No markdown code blocks, no explanations, no additional text."
    )


def get_language_file_extension(language: str) -> str:
    """Get file extension for language"""
    language = language.lower().strip()
    config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["python"])
    return config["extensions"][0]


def get_language_test_framework(language: str) -> str:
    """Get test framework for language"""
    language = language.lower().strip()
    config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS["python"])
    return config["test_framework"]


def get_supported_languages() -> list:
    """Get list of supported programming languages"""
    return [lang for lang, config in LANGUAGE_CONFIGS.items() if config["enabled"]]


def validate_language(language: str) -> bool:
    """Validate if language is supported"""
    language = language.lower().strip()
    return language in get_supported_languages() or language in ["c#", ".net"]


def normalize_language(language: str) -> str:
    """Normalize language name to standard form"""
    language = language.lower().strip()
    
    # Handle common aliases
    aliases = {
        "c#": "csharp",
        ".net": "dotnet",
        "net": "dotnet",
        "asp.net": "dotnet",
        "fastapi": "python",
        "py": "python"
    }
    
    return aliases.get(language, language)
