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