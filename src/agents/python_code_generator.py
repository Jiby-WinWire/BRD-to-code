from typing import Dict, List, Any
from src.agents.base_code_generator import BaseCodeGenerator
import logging
from src.agents.utils import safe_json_loads
from pathlib import Path
from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name

logger = logging.getLogger(__name__)

class PythonCodeGenerator(BaseCodeGenerator):
    """Generates production-ready Python FastAPI code from user stories"""

    @staticmethod
    def generate_from_stories(stories: List[Dict], llm_client=None, deployment_name: str = None) -> Dict[str, str]:
        if not stories:
            logger.warning("No stories provided for code generation")
            return {}
        if llm_client is None:
            llm_client = get_llm_client()
        if deployment_name is None:
            deployment_name = get_llm_deployment_name()
        functional_stories = [s for s in stories if isinstance(s, dict)]
        stories_to_process = functional_stories[:5] if functional_stories else stories[:5]
        if llm_client is not None:
            result = PythonCodeGenerator._generate_with_llm(stories_to_process, llm_client, deployment_name)
            if result:
                return result
            logger.warning("LLM generation failed, falling back to templates")
        else:
            logger.info("⚠️  Azure OpenAI not configured, using template generation")
        return PythonCodeGenerator._generate_from_templates(stories_to_process)

    @staticmethod
    def _generate_with_llm(stories: List[Dict], llm_client, deployment_name: str) -> Dict[str, str]:
        system_prompt = """You are an expert Full-Stack Web Developer. Generate a complete, production-ready web application with FastAPI backend and interactive HTML frontend.\n\nGenerate SEVEN files for a complete web application:\n\nBACKEND (API + Templates):\n1. models.py: Pydantic models with validation\n2. services.py: Business logic with in-memory storage + singleton export at bottom\n3. main.py: FastAPI app with BOTH API endpoints AND HTML template routes\n\nFRONTEND (Templates + Static):\n4. templates/index.html: Main page with professional UI (Bootstrap/Tailwind)\n5. templates/base.html: Base template with nav, footer, common structure\n6. static/style.css: Custom CSS styling\n7. static/app.js: JavaScript for interactivity (fetch API calls, dynamic UI updates)\n\nCRITICAL REQUIREMENTS:\n- models.py FIRST LINE: from pydantic import BaseModel, EmailStr\n- models.py SECOND LINE: from typing import Optional, List\n- For auto-generated IDs: Use 'id: Optional[int] = None'\n- services.py FIRST LINE: from typing import Optional, List, Dict\n- services.py SECOND LINE: from models import *\n- main.py EXACT START (COPY THESE LINES AS-IS):\n```python\nfrom fastapi import FastAPI, HTTPException, Request\nfrom fastapi.responses import HTMLResponse\nfrom fastapi.staticfiles import StaticFiles\nfrom fastapi.templating import Jinja2Templates\nfrom typing import List, Optional\nfrom models import *\nfrom services import *\n\napp = FastAPI()\napp.mount("/static", StaticFiles(directory="static"), name="static")\ntemplates = Jinja2Templates(directory="templates")\n\n@app.get("/", response_class=HTMLResponse)\nasync def home(request: Request):\n    return templates.TemplateResponse(request, "index.html", {})\n```\n  * HTML routes: Use CORRECT TemplateResponse syntax: templates.TemplateResponse(request, "template.html", {})\n    - NEVER use old syntax: templates.TemplateResponse("template.html", {"request": request}) ❌\n    - ALWAYS use new syntax: templates.TemplateResponse(request, "template.html", {}) ✅\n  * API routes: @app.post("/api/items", status_code=201) that accept Pydantic models\n- HTML templates:\n  * Use Bootstrap 5 or Tailwind CSS for professional styling\n  * Include forms for CREATE operations\n  * Include tables/cards for displaying data\n  * Include buttons for UPDATE/DELETE operations\n  * Use Jinja2 template inheritance ({% extends \"base.html\" %})\n- CSS: Modern, responsive design with good color scheme\n- JavaScript: \n  * Use fetch() API to call backend endpoints\n  * Handle form submissions with preventDefault()\n  * Update DOM dynamically when data changes\n  * Show loading states and error messages\n- Services: Class-based with __init__, end with singleton like `app_service = AppService()`\n\nHTTP STATUS CODES (CRITICAL - MUST FOLLOW):\n- POST endpoints: @app.post("/api/items", status_code=201) - ALWAYS 201 for creation\n- GET endpoints: @app.get("/api/items") - Returns 200 by default\n- PUT/DELETE: Returns 200 by default\n- Errors: 422 (validation), 404 (not found), 400 (business error)\n\nAPI ENDPOINT PATTERNS (CRITICAL - MUST FOLLOW):\n- ALWAYS accept Pydantic models as SINGLE parameter: @app.post("/api/items", status_code=201) async def create_item(item: Item)\n- NEVER use Form(...): FORBIDDEN → async def create_item(name: str = Form(...))\n- NEVER use multiple parameters: FORBIDDEN → async def create_item(name: str, price: float)\n- JavaScript sends JSON: fetch('/api/items', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'x', price: 10})})\n- FastAPI accepts JSON via Pydantic models\n- For nested data: Create nested Pydantic models in models.py\n\nCORRECT EXAMPLE:\n```python\n# models.py\nclass Post(BaseModel):\n    id: Optional[int] = None\n    title: str\n    content: str\n\n# main.py\n@app.post("/api/posts", status_code=201)\nasync def create_post(post: Post):  # Single Pydantic model!\n    result = post_service.create(post)\n    return result\n```\n\n- Return ONLY valid code as JSON: {"models": "...", "services": "...", "main": "...", "index_html": "...", "base_html": "...", "style_css": "...", "app_js": "..."}\n- NO markdown, NO explanations, ONLY the JSON with code"""
        # Build stories text
        stories_text_parts = []
        for i, s in enumerate(stories):
            if 'fields' in s:
                summary = s['fields'].get('summary', '')
                description = s['fields'].get('description', '')[:200]
            else:
                summary = s.get('title', s.get('id', ''))
                description = s.get('description', '')[:200]
            stories_text_parts.append(f"{i+1}. {summary}: {description}")
        stories_text = "\n".join(stories_text_parts)
        prompt = f"""Generate a complete web application for these user stories:\n\n{stories_text}\n\nReturn a JSON object with 7 keys: \"models\", \"services\", \"main\", \"index_html\", \"base_html\", \"style_css\", \"app_js\" containing the code for each file.\nCreate a professional, interactive web app with forms, tables, and dynamic functionality."""
        try:
            logger.info(f"Generating full-stack web app for {len(stories)} stories using LLM...")
            response = llm_client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=6000
            )
            content = response.choices[0].message.content
            logger.debug(f"LLM response length: {len(content)} chars")
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                code_json = safe_json_loads(json_match.group(0), fallback={})
                files = {
                    "src/api/models.py": code_json.get("models", "from pydantic import BaseModel\n"),
                    "src/api/services.py": code_json.get("services", "# Services\n"),
                    "src/api/main.py": code_json.get("main", "from fastapi import FastAPI\napp = FastAPI()\n"),
                    "templates/index.html": code_json.get("index_html", "<html><body>Home</body></html>"),
                    "templates/base.html": code_json.get("base_html", "<html><body>{% block content %}{% endblock %}</body></html>"),
                    "static/style.css": code_json.get("style_css", "body { font-family: Arial; }"),
                    "static/app.js": code_json.get("app_js", "// Application JavaScript\nconsole.log('App loaded');")
                }
                logger.info("Successfully generated full-stack web application")
                return files
            else:
                logger.warning("Could not parse JSON from LLM response, using fallback")
                return PythonCodeGenerator._generate_from_templates(stories)
        except Exception as e:
            logger.error(f"Error generating code with LLM: {str(e)}")
            return {}

    @staticmethod
    def _generate_from_templates(stories: List[Dict]) -> Dict[str, str]:
        try:
            logger.info("Using template-based generation (no LLM required)")
            sample_path = Path(__file__).parent.parent / "output" / "python-sample"
            if sample_path.exists():
                logger.info(f"Loading templates from {sample_path}")
                files = {}
                file_mappings = {
                    "src/api/models.py": "models.py",
                    "src/api/services.py": "services.py",
                    "src/api/main.py": "main.py",
                    "templates/index.html": "index.html",
                    "templates/base.html": "base.html",
                    "static/style.css": "style.css",
                    "static/app.js": "app.js",
                }
                for output_path, template_filename in file_mappings.items():
                    full_path = sample_path / template_filename
                    if full_path.exists():
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                files[output_path] = f.read()
                            logger.info(f"  ✓ Loaded: {output_path}")
                        except Exception as e:
                            logger.warning(f"  ✗ Failed to load {output_path}: {str(e)}")
                return files if files else PythonCodeGenerator._generate_fallback_code([])
            else:
                logger.info("Using fallback code generation")
                return PythonCodeGenerator._generate_fallback_code(stories)
        except Exception as e:
            logger.error(f"Template generation failed: {str(e)}")
            return PythonCodeGenerator._generate_fallback_code(stories)

    @staticmethod
    def _generate_fallback_code(stories: List[Dict]) -> Dict[str, str]:
        # (Copy fallback code from story_to_code.py)
        files = {}
        files["src/api/models.py"] = "from pydantic import BaseModel, EmailStr\nfrom typing import Optional, List\n\nclass Task(BaseModel):\n    id: Optional[int] = None\n    title: str\n    description: str\n    completed: bool = False\n"
        files["src/api/services.py"] = "from typing import Optional, List, Dict\nfrom models import Task\n\nclass TaskService:\n    def __init__(self):\n        self.tasks: Dict[int, dict] = {}\n        self.id_counter = 1\n    \n    def create_task(self, title: str, description: str) -> dict:\n        task = {\n            'id': self.id_counter,\n            'title': title,\n            'description': description,\n            'completed': False\n        }\n        self.tasks[self.id_counter] = task\n        self.id_counter += 1\n        return task\n    \n    def get_all_tasks(self) -> List[dict]:\n        return list(self.tasks.values())\n    \n    def get_task(self, task_id: int) -> Optional[dict]:\n        return self.tasks.get(task_id)\n    \n    def update_task(self, task_id: int, completed: bool) -> Optional[dict]:\n        if task_id in self.tasks:\n            self.tasks[task_id]['completed'] = completed\n            return self.tasks[task_id]\n        return None\n    \n    def delete_task(self, task_id: int) -> bool:\n        if task_id in self.tasks:\n            del self.tasks[task_id]\n            return True\n        return False\n\ntask_service = TaskService()\n"
        files["src/api/main.py"] = "from fastapi import FastAPI, HTTPException, Request\nfrom fastapi.responses import HTMLResponse\nfrom fastapi.staticfiles import StaticFiles\nfrom fastapi.templating import Jinja2Templates\nfrom typing import List, Optional\nfrom models import Task\nfrom services import task_service\n\napp = FastAPI()\napp.mount(\"/static\", StaticFiles(directory=\"static\"), name=\"static\")\ntemplates = Jinja2Templates(directory=\"templates\")\n\n@app.get(\"/\", response_class=HTMLResponse)\nasync def home(request: Request):\n    return templates.TemplateResponse(request, \"index.html\", {})\n\n@app.get(\"/api/tasks\")\nasync def get_tasks():\n    return task_service.get_all_tasks()\n\n@app.post(\"/api/tasks\", status_code=201)\nasync def create_task(task: Task):\n    return task_service.create_task(task.title, task.description)\n\n@app.put(\"/api/tasks/{task_id}\")\nasync def update_task(task_id: int, task: Task):\n    updated = task_service.update_task(task_id, task.completed)\n    if not updated:\n        raise HTTPException(status_code=404, detail=\"Task not found\")\n    return updated\n\n@app.delete(\"/api/tasks/{task_id}\")\nasync def delete_task(task_id: int):\n    if not task_service.delete_task(task_id):\n        raise HTTPException(status_code=404, detail=\"Task not found\")\n    return {\"message\": \"Task deleted successfully\"}\n"
        files["templates/base.html"] = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>{% block title %}Task Manager{% endblock %}</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"/static/style.css\">\n</head>\n<body>\n    <nav class=\"navbar navbar-expand-lg navbar-dark bg-primary\">\n        <div class=\"container\">\n            <a class=\"navbar-brand\" href=\"/\">Task Manager</a>\n        </div>\n    </nav>\n    <main>\n        {% block content %}{% endblock %}\n    </main>\n    <footer class=\"bg-light text-center py-3 mt-5\">\n        <p class=\"mb-0\">Generated by BRD-to-Code AI Pipeline</p>\n    </footer>\n    <script src=\"/static/app.js\"></script>\n</body>\n</html>\n"
        files["templates/index.html"] = "{% extends \"base.html\" %}\n{% block title %}Task Manager - Home{% endblock %}\n{% block content %}\n<div class=\"container mt-5\">\n    <h1 class=\"mb-4\">Task Manager</h1>\n    \n    <div class=\"card mb-4\">\n        <div class=\"card-body\">\n            <h5 class=\"card-title\">Add New Task</h5>\n            <form id=\"taskForm\">\n                <div class=\"mb-3\">\n                    <label for=\"taskTitle\" class=\"form-label\">Title</label>\n                    <input type=\"text\" class=\"form-control\" id=\"taskTitle\" required>\n                </div>\n                <div class=\"mb-3\">\n                    <label for=\"taskDescription\" class=\"form-label\">Description</label>\n                    <textarea class=\"form-control\" id=\"taskDescription\" rows=\"3\" required></textarea>\n                </div>\n                <button type=\"submit\" class=\"btn btn-primary\">Add Task</button>\n            </form>\n        </div>\n    </div>\n    \n    <h3>Tasks</h3>\n    <div id=\"tasksList\" class=\"row\">\n        <!-- Tasks will be loaded here -->\n    </div>\n</div>\n{% endblock %}\n"
        files["static/style.css"] = "body {\n    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;\n    background-color: #f8f9fa;\n}\n\n.task-card {\n    transition: transform 0.2s;\n}\n\n.task-card:hover {\n    transform: translateY(-5px);\n    box-shadow: 0 4px 8px rgba(0,0,0,0.1);\n}\n\n.task-completed {\n    opacity: 0.6;\n    text-decoration: line-through;\n}\n\n.btn-action {\n    margin: 0 5px;\n}\n\n#tasksList {\n    min-height: 200px;\n}\n\n.loading {\n    text-align: center;\n    padding: 20px;\n    color: #6c757d;\n}\n"
        files["static/app.js"] = "// Task Manager Application\ndocument.addEventListener('DOMContentLoaded', () => {\n    loadTasks();\n    \n    document.getElementById('taskForm').addEventListener('submit', async (e) => {\n        e.preventDefault();\n        await addTask();\n    });\n});\n\nasync function loadTasks() {\n    const tasksDiv = document.getElementById('tasksList');\n    tasksDiv.innerHTML = '<div class=\"loading\">Loading tasks...</div>';\n    \n    try {\n        const response = await fetch('/api/tasks');\n        const tasks = await response.json();\n        \n        if (tasks.length === 0) {\n            tasksDiv.innerHTML = '<div class=\"col-12\"><p class=\"text-muted\">No tasks yet. Add one above!</p></div>';\n            return;\n        }\n        \n        tasksDiv.innerHTML = tasks.map(task => `\n            <div class=\"col-md-6 mb-3\">\n                <div class=\"card task-card ${task.completed ? 'task-completed' : ''}\">\n                    <div class=\"card-body\">\n                        <h5 class=\"card-title\">${task.title}</h5>\n                        <p class=\"card-text\">${task.description}</p>\n                        <div>\n                            <button onclick=\"toggleTask(${task.id}, ${!task.completed})\" \n                                    class=\"btn btn-sm ${task.completed ? 'btn-warning' : 'btn-success'} btn-action\">\n                                ${task.completed ? 'Undo' : 'Complete'}\n                            </button>\n                            <button onclick=\"deleteTask(${task.id})\" class=\"btn btn-sm btn-danger btn-action\">\n                                Delete\n                            </button>\n                        </div>\n                    </div>\n                </div>\n            </div>\n        `).join('');\n    } catch (error) {\n        tasksDiv.innerHTML = '<div class=\"col-12\"><p class=\"text-danger\">Error loading tasks</p></div>';\n        console.error('Error:', error);\n    }\n}\n\nasync function addTask() {\n    const title = document.getElementById('taskTitle').value;\n    const description = document.getElementById('taskDescription').value;\n    \n    try {\n        const response = await fetch('/api/tasks', {\n            method: 'POST',\n            headers: { 'Content-Type': 'application/json' },\n            body: JSON.stringify({ title, description })\n        });\n        \n        if (response.ok) {\n            document.getElementById('taskForm').reset();\n            await loadTasks();\n        }\n    } catch (error) {\n        alert('Error adding task');\n        console.error('Error:', error);\n    }\n}\n\nasync function toggleTask(taskId, completed) {\n    try {\n        await fetch(`/api/tasks/${taskId}`, {\n            method: 'PUT',\n            headers: { 'Content-Type': 'application/json' },\n            body: JSON.stringify({ id: taskId, title: '', description: '', completed })\n        });\n        await loadTasks();\n    } catch (error) {\n        alert('Error updating task');\n        console.error('Error:', error);\n    }\n}\n\nasync function deleteTask(taskId) {\n    if (!confirm('Are you sure you want to delete this task?')) return;\n    \n    try {\n        await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });\n        await loadTasks();\n    } catch (error) {\n        alert('Error deleting task');\n        console.error('Error:', error);\n    }\n}\n"
        logger.info("Generated fallback full-stack web application")
        return files
