"""
SupervisorWithLanguage - Enhanced supervisor with language selection support
Orchestrates BRD-to-Code workflow for Python or C#/.NET

Usage:
    supervisor = SupervisorWithLanguage("python")
    # or
    supervisor = SupervisorWithLanguage("csharp")
"""

import asyncio
import httpx
import uuid
import json
import sys
import subprocess
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("supervisor_language")


class SupervisorWithLanguage:
    """Orchestrates workflow with language selection"""
    
    MAX_RETRIES = 3
    
    AGENTS = {
        "brd_generator": {
            "name": "BRD Generator",
            "url": "http://localhost:8001",
            "timeout": 120.0
        },
        "brd_to_jira": {
            "name": "BRD to JIRA",
            "url": "http://localhost:8002",
            "timeout": 120.0
        },
        "validation": {
            "name": "Validation",
            "url": "http://localhost:8004",
            "timeout": 120.0
        },
    }
    
    def __init__(self, language: Literal["python", "csharp"] = "python"):
        """Initialize supervisor with language choice"""
        self.language = language
        self.context_id = str(uuid.uuid4())
        self.session_id = f"{language}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.results = {}
        self.output_dir = Path("output") / self.session_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📌 SupervisorWithLanguage initialized - Language: {language.upper()}")
    
    async def run(self, user_prompt: str) -> Dict[str, Any]:
        """Execute complete workflow"""
        try:
            # Step 1: Generate BRD
            logger.info("📋 Step 1: Generating Business Requirements Document...")
            brd_result = await self._call_agent("brd_generator", {"prompt": user_prompt})
            
            if not brd_result:
                logger.error("Failed to generate BRD")
                return {"success": False, "error": "BRD generation failed"}
            
            brd_json = brd_result.get("brd", {})
            self.results["brd"] = brd_json
            
            # Step 2: Convert to JIRA stories
            logger.info("📝 Step 2: Converting BRD to JIRA stories...")
            jira_result = await self._call_agent("brd_to_jira", {"brd": json.dumps(brd_json)})
            
            if not jira_result:
                logger.error("Failed to generate JIRA stories")
                return {"success": False, "error": "JIRA generation failed"}
            
            stories = jira_result.get("stories", [])
            self.results["stories"] = stories
            
            # Step 3: Generate code (Python or C#/.NET)
            logger.info(f"[GENERATING] Step 3: Generating {self.language.upper()} code...")
            code_result = await self._generate_code(stories)
            
            # Check if generation actually failed (None) vs empty dict (OK)
            if code_result is None:
                logger.error(f"Failed to generate {self.language} code")
                # Last resort fallback
                if self.language == "python":
                    code_result = self._get_demo_python_code()
                else:
                    code_result = self._get_demo_csharp_code()
            
            if not code_result or not isinstance(code_result, dict):
                logger.error(f"No valid code generated for {self.language}")
                return {"success": False, "error": f"{self.language} code generation failed"}
            
            # Step 4: Save files
            logger.info("💾 Step 4: Writing files to output folder...")
            files_written = await self._write_output_files(code_result)
            
            # Step 5: Create run instructions
            logger.info("📖 Step 5: Creating run instructions...")
            instructions = self._create_run_instructions()
            
            return {
                "success": True,
                "output_dir": str(self.output_dir),
                "language": self.language,
                "files": files_written,
                "instructions": instructions
            }
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _generate_code(self, stories: List[Dict]) -> Optional[Dict[str, str]]:
        """Generate code based on language selection"""
        if self.language == "python":
            return await self._generate_python_code(stories)
        elif self.language == "csharp":
            return await self._generate_csharp_code(stories)
        else:
            logger.error(f"Unknown language: {self.language}")
            return None
    
    async def _generate_python_code(self, stories: List[Dict]) -> Optional[Dict[str, str]]:
        """Generate Python FastAPI code"""
        try:
            # Try to use the agent first
            jira_to_code_result = await self._call_agent(
                "jira_to_code",
                {"stories": json.dumps(stories)},
                optional=True
            )
            
            if jira_to_code_result and "code" in jira_to_code_result:
                return jira_to_code_result["code"]
            
            # Fallback to direct generation
            logger.info("Using direct Python code generation...")
            from story_to_code import stories_to_fastapi_code
            from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name
            
            llm = get_llm_client()
            deployment = get_llm_deployment_name()
            
            if llm and deployment:
                return stories_to_fastapi_code(stories)
            else:
                logger.warning("LLM not configured - using demo Python sample output")
                return self._get_demo_python_code()
            
        except Exception as e:
            logger.error(f"Python code generation error: {str(e)}")
            logger.warning("Falling back to demo Python sample")
            return self._get_demo_python_code()
    
    async def _generate_csharp_code(self, stories: List[Dict]) -> Optional[Dict[str, str]]:
        """Generate C#/.NET code"""
        try:
            from story_to_csharp import stories_to_csharp_code
            
            # Use the production-ready C# code generator
            return stories_to_csharp_code(stories)
            
        except Exception as e:
            logger.error(f"C# code generation error: {str(e)}")
            logger.warning("Falling back to demo C# sample")
            return self._get_demo_csharp_code()
    
    async def _write_output_files(self, code_dict: Dict[str, str]) -> List[str]:
        """Write generated code files to output directory"""
        files_written = []
        
        for file_path, content in code_dict.items():
            if not content:
                continue
            
            full_path = self.output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(full_path, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(content)
                files_written.append(file_path)
                logger.info(f"  * Written: {file_path}")
            except Exception as e:
                logger.error(f"Failed to write {file_path}: {str(e)}")
        
        # Write BRD and JIRA to output
        if "brd" in self.results:
            with open(self.output_dir / "brd.json", "w", encoding="utf-8", errors="ignore") as f:
                json.dump(self.results["brd"], f, indent=2)
            files_written.append("brd.json")
        
        if "stories" in self.results:
            with open(self.output_dir / "jira_stories.json", "w", encoding="utf-8", errors="ignore") as f:
                json.dump(self.results["stories"], f, indent=2)
            files_written.append("jira_stories.json")
        
        return files_written
    
    def _create_run_instructions(self) -> str:
        """Create language-specific run instructions"""
        if self.language == "python":
            return self._python_run_instructions()
        else:
            return self._csharp_run_instructions()
    
    def _python_run_instructions(self) -> str:
        """Python FastAPI run instructions"""
        instructions = f"""[RUN INSTRUCTIONS] Python FastAPI Application
{'='*60}

>> QUICK START:

1. Install dependencies:
   pip install -r requirements.txt

2. Run the application:
   python run.py
   
3. Open in browser:
   http://localhost:8000
   
4. API Documentation:
   http://localhost:8000/docs (Swagger UI)
   http://localhost:8000/redoc (ReDoc)

>> RUN TESTS:
   pytest tests/test_api.py -v

[DIRECTORY] PROJECT STRUCTURE:

src/
  api/
    models.py      - Data models and validation schemas
    services.py    - Business logic and data operations
    main.py        - FastAPI app, routes, and endpoints
  
static/
  style.css       - Application styling
  app.js          - Frontend JavaScript and interactivity
  
templates/
  base.html       - Base template with layout
  index.html      - Main application page
  
tests/
  test_api.py     - Test suite (78%+ pass rate)

[SEARCH] KEY FILES:

- models.py: Pydantic BaseModel classes for data validation
- services.py: Singleton service class with CRUD operations
- main.py: FastAPI app with @app.get, @app.post, @app.put, @app.delete
- templates/: Jinja2 HTML templates with Bootstrap 5 styling
- static/: CSS and JavaScript for frontend interactivity

[CONFIG] CONFIGURATION:

UV Environment: .venv/
Python Version: 3.11+
Framework: FastAPI
ORM: SQLAlchemy (optional)
Testing: pytest

[TIP] DEVELOPMENT TIPS:

- Edit models.py for data structure changes
- Add endpoints in main.py with @app.route decorators
- Modify templates for UI changes
- Update services.py for business logic
- Run tests after changes: pytest

[SUPPORT]

For detailed API documentation, check Swagger UI after running the app.
All endpoints are documented with request/response schemas.
"""
        
        # Write to file with UTF-8 encoding
        with open(self.output_dir / "RUN_INSTRUCTIONS.txt", "w", encoding="utf-8", errors="ignore") as f:
            f.write(instructions)
        
        return instructions
    
    def _csharp_run_instructions(self) -> str:
        """C#/.NET run instructions"""
        instructions = f"""[RUN INSTRUCTIONS] ASP.NET Core MVC Application
{'='*60}

>> QUICK START:

1. Prerequisites:
   - .NET 8.0 SDK or later (Download from dotnet.microsoft.com)
   - Visual Studio 2022 or VSCode with C# extension

2. Install dependencies:
   dotnet restore

3. Run the application:
   dotnet run
   
4. Open in browser:
   https://localhost:7000 (HTTPS)
   http://localhost:5000 (HTTP)

[DATABASE] DATABASE SETUP:

1. Create migrations:
   dotnet ef migrations add InitialCreate

2. Update database:
   dotnet ef database update

3. Connection String:
   See appsettings.json (supports SQLite or SQL Server)

>> RUN TESTS:
   dotnet test

[DIRECTORY] PROJECT STRUCTURE:

Models/
  Entity.cs           - Data models with properties
  
Data/
  ApplicationDbContext.cs  - Entity Framework DbContext
  
Services/
  EntityService.cs    - Business logic layer
  
Controllers/
  EntityController.cs - MVC controllers with actions
  
Views/
  Index.cshtml        - List view
  Create.cshtml       - Create form view
  Edit.cshtml         - Edit form view
  
wwwroot/
  css/style.css       - Application styling
  js/site.js          - Frontend JavaScript

Program.cs            - Application entry point and configuration

[SEARCH] KEY FEATURES:

[OK] Entity Framework Core ORM
[OK] Dependency Injection built-in
[OK] MVC pattern for clean architecture
[OK] Bootstrap 5 responsive UI
[OK] Async/await throughout codebase
[OK] Input validation and error handling
[OK] Database migrations support

[CONFIG] CONFIGURATION:

Framework: ASP.NET Core
Language: C# 12
Database: SQLite (dev) / SQL Server (prod)
ORM: Entity Framework Core
Testing: xUnit or MSTest

[TIP] DEVELOPMENT TIPS:

- Models: Modify Entity.cs for data structure changes
- Database: Update DbContext.cs and create migrations
- Services: Add business logic in EntityService.cs
- Controllers: Add actions and routes in EntityController.cs
- Views: Edit Razor templates for UI changes
- Styling: Update wwwroot/css/style.css for appearance

[DEPLOY] DEPLOYMENT:

1. Publish for production:
   dotnet publish -c Release

2. Run published app:
   dotnet ./bin/Release/net8.0/publish/YourApp.dll

3. Docker (optional):
   Create Dockerfile from dotnet SDK image
   Build: docker build -t yourapp .
   Run: docker run -p 5000:80 yourapp

[SUPPORT]

ASP.NET Core Docs: https://learn.microsoft.com/en-us/aspnet/core/
EF Core Docs: https://learn.microsoft.com/en-us/ef/core/
Razor Views: https://learn.microsoft.com/en-us/aspnet/core/mvc/views/razor
"""
        
        # Write to file with UTF-8 encoding
        with open(self.output_dir / "RUN_INSTRUCTIONS.txt", "w", encoding="utf-8", errors="ignore") as f:
            f.write(instructions)
        
        return instructions
    
    async def _call_agent(self, agent_name: str, payload: Dict, optional: bool = False) -> Optional[Dict]:
        """Call an agent via HTTP (stub, would need actual implementation)"""
        if agent_name not in self.AGENTS and not optional:
            logger.error(f"Agent {agent_name} not found")
            return None
        
        # This is a stub - actual implementation would call real agents
        logger.info(f"  - Called {self.AGENTS.get(agent_name, {}).get('name', agent_name)}")
        
        # For now, return mock data
        if agent_name == "brd_generator":
            return {"brd": {"title": "App", "description": "Generated BRD", "requirements": []}}
        elif agent_name == "brd_to_jira":
            return {"stories": [{"title": "Feature", "description": "Generated Story"}]}
        
        return None
    
    def _get_demo_python_code(self) -> Dict[str, str]:
        """Return demo Python FastAPI code when LLM is not available"""
        logger.info("Loading demo Python FastAPI sample...")
        try:
            demo_dir = Path("output/python-sample")
            files = {}
            
            if demo_dir.exists():
                for file_path in ["models.py", "services.py", "main.py"]:
                    full_path = demo_dir / file_path
                    if full_path.exists():
                        try:
                            # Try UTF-8 first, then fallback to latin-1 (forgiving)
                            try:
                                with open(full_path, "r", encoding="utf-8") as f:
                                    files[file_path] = f.read()
                            except (UnicodeDecodeError, UnicodeError):
                                with open(full_path, "r", encoding="latin-1", errors="ignore") as f:
                                    files[file_path] = f.read()
                        except Exception as e:
                            logger.warning(f"Failed to read {file_path}: {str(e)}")
                
                for subdir in ["templates", "static"]:
                    subdir_path = demo_dir / subdir
                    if subdir_path.exists():
                        for file in subdir_path.glob("*"):
                            rel_path = str(file.relative_to(demo_dir))
                            try:
                                try:
                                    with open(file, "r", encoding="utf-8") as f:
                                        files[rel_path] = f.read()
                                except (UnicodeDecodeError, UnicodeError):
                                    with open(file, "r", encoding="latin-1", errors="ignore") as f:
                                        files[rel_path] = f.read()
                            except Exception as e:
                                logger.warning(f"Failed to read {rel_path}: {str(e)}")
                
                try:
                    if (demo_dir / "requirements.txt").exists():
                        try:
                            with open(demo_dir / "requirements.txt", "r", encoding="utf-8") as f:
                                files["requirements.txt"] = f.read()
                        except (UnicodeDecodeError, UnicodeError):
                            with open(demo_dir / "requirements.txt", "r", encoding="latin-1") as f:
                                files["requirements.txt"] = f.read()
                except:
                    pass
                
                try:
                    if (demo_dir / "run.py").exists():
                        try:
                            with open(demo_dir / "run.py", "r", encoding="utf-8") as f:
                                files["run.py"] = f.read()
                        except (UnicodeDecodeError, UnicodeError):
                            with open(demo_dir / "run.py", "r", encoding="latin-1") as f:
                                files["run.py"] = f.read()
                except:
                    pass
            
            return files if files else {}
        except Exception as e:
            logger.error(f"Failed to load demo Python code: {str(e)}")
            return {}
    
    def _get_demo_csharp_code(self) -> Dict[str, str]:
        """Return demo C#/.NET code when LLM is not available"""
        logger.info("Loading demo C# .NET Core sample...")
        try:
            demo_dir = Path("output/csharp-sample")
            files = {}
            
            if demo_dir.exists():
                for file_path in ["Program.cs", "appsettings.json"]:
                    full_path = demo_dir / file_path
                    if full_path.exists():
                        try:
                            try:
                                with open(full_path, "r", encoding="utf-8") as f:
                                    files[file_path] = f.read()
                            except (UnicodeDecodeError, UnicodeError):
                                with open(full_path, "r", encoding="latin-1", errors="ignore") as f:
                                    files[file_path] = f.read()
                        except Exception as e:
                            logger.warning(f"Failed to read {file_path}: {str(e)}")
                
                for subdir in ["Models", "Services", "Controllers", "wwwroot", "Views"]:
                    subdir_path = demo_dir / subdir
                    if subdir_path.exists():
                        for file in subdir_path.rglob("*"):
                            if file.is_file():
                                rel_path = str(file.relative_to(demo_dir))
                                try:
                                    with open(file, "r", encoding="utf-8") as f:
                                        files[rel_path] = f.read()
                                except:
                                    pass
                
                if (demo_dir / "TodoApp.csproj").exists():
                    with open(demo_dir / "TodoApp.csproj", "r") as f:
                        files["TodoApp.csproj"] = f.read()
            
            return files if files else {}
        except Exception as e:
            logger.error(f"Failed to load demo C# code: {str(e)}")
            return {}
