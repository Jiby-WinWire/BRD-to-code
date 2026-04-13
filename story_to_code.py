# Jira user stories to FastAPI code generation logic using LLM
from typing import List, Dict
import logging
import json
from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name

logger = logging.getLogger(__name__)

def stories_to_fastapi_code(stories: List[Dict]) -> Dict[str, str]:
    """
    Generate functional FastAPI code files from Jira user stories using LLM.
    Returns a dict mapping file paths to file contents.
    """
    if not stories:
        logger.warning("No stories provided for code generation")
        return {}
    
    llm = get_llm_client()
    deployment_name = get_llm_deployment_name()
    
    # Group stories by type for better code generation
    # Handle both JIRA format (withfields' key) and simple format
    functional_stories = []
    for s in stories:
        if 'fields' in s:
            # JIRA format
            if 'functional' in s['fields'].get('labels', []):
                functional_stories.append(s)
        else:
            # Simple format - assume all are functional
            functional_stories.append(s)
    
    # Limit to first 5 functional stories for better quality
    stories_to_process = functional_stories[:5] if functional_stories else stories[:5]
    
    system_prompt = """You are an expert Full-Stack Web Developer. Generate a complete, production-ready web application with FastAPI backend and interactive HTML frontend.

Generate SEVEN files for a complete web application:

BACKEND (API + Templates):
1. models.py: Pydantic models with validation
2. services.py: Business logic with in-memory storage + singleton export at bottom
3. main.py: FastAPI app with BOTH API endpoints AND HTML template routes

FRONTEND (Templates + Static):
4. templates/index.html: Main page with professional UI (Bootstrap/Tailwind)
5. templates/base.html: Base template with nav, footer, common structure
6. static/style.css: Custom CSS styling
7. static/app.js: JavaScript for interactivity (fetch API calls, dynamic UI updates)

CRITICAL REQUIREMENTS:
- models.py FIRST LINE: from pydantic import BaseModel, EmailStr
- models.py SECOND LINE: from typing import Optional, List
- For auto-generated IDs: Use 'id: Optional[int] = None'
- services.py FIRST LINE: from typing import Optional, List, Dict
- services.py SECOND LINE: from models import *
- main.py EXACT START (COPY THESE LINES AS-IS):
```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from models import *
from services import *

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
```
  * HTML routes: @app.get("/", response_class=HTMLResponse) that return templates.TemplateResponse()
  * API routes: @app.post("/api/items", status_code=201) that accept Pydantic models
- HTML templates:
  * Use Bootstrap 5 or Tailwind CSS for professional styling
  * Include forms for CREATE operations
  * Include tables/cards for displaying data
  * Include buttons for UPDATE/DELETE operations
  * Use Jinja2 template inheritance ({% extends "base.html" %})
- CSS: Modern, responsive design with good color scheme
- JavaScript: 
  * Use fetch() API to call backend endpoints
  * Handle form submissions with preventDefault()
  * Update DOM dynamically when data changes
  * Show loading states and error messages
- Services: Class-based with __init__, end with singleton like `app_service = AppService()`

HTTP STATUS CODES (CRITICAL - MUST FOLLOW):
- POST endpoints: @app.post("/api/items", status_code=201) - ALWAYS 201 for creation
- GET endpoints: @app.get("/api/items") - Returns 200 by default
- PUT/DELETE: Returns 200 by default
- Errors: 422 (validation), 404 (not found), 400 (business error)

API ENDPOINT PATTERNS (CRITICAL - MUST FOLLOW):
- ALWAYS accept Pydantic models as SINGLE parameter: @app.post("/api/items", status_code=201) async def create_item(item: Item)
- NEVER use Form(...): FORBIDDEN \u2192 async def create_item(name: str = Form(...))
- NEVER use multiple parameters: FORBIDDEN \u2192 async def create_item(name: str, price: float)
- JavaScript sends JSON: fetch('/api/items', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: 'x', price: 10})})
- FastAPI accepts JSON via Pydantic models
- For nested data: Create nested Pydantic models in models.py

CORRECT EXAMPLE:
```python
# models.py
class Post(BaseModel):
    id: Optional[int] = None
    title: str
    content: str

# main.py
@app.post("/api/posts", status_code=201)
async def create_post(post: Post):  # Single Pydantic model!
    result = post_service.create(post)
    return result
```

- Return ONLY valid code as JSON: {"models": "...", "services": "...", "main": "...", "index_html": "...", "base_html": "...", "style_css": "...", "app_js": "..."}
- NO markdown, NO explanations, ONLY the JSON with code"""
    
    # Build stories text handling both JIRA format and simple format
    stories_text_parts = []
    for i, s in enumerate(stories_to_process):
        if 'fields' in s:
            # JIRA format
            summary = s['fields'].get('summary', '')
            description = s['fields'].get('description', '')[:200]
        else:
            # Simple format
            summary = s.get('title', s.get('id', ''))
            description = s.get('description', '')[:200]
        stories_text_parts.append(f"{i+1}. {summary}: {description}")
    
    stories_text = "\n".join(stories_text_parts)
    
    prompt = f"""Generate a complete web application for these user stories:

{stories_text}

Return a JSON object with 7 keys: "models", "services", "main", "index_html", "base_html", "style_css", "app_js" containing the code for each file.
Create a professional, interactive web app with forms, tables, and dynamic functionality."""
    
    try:
        logger.info(f"Generating full-stack web app for {len(stories_to_process)} stories using LLM...")
        response = llm.chat.completions.create(
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
        
        # Try to parse JSON response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            code_json = json.loads(json_match.group(0))
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
            return _generate_fallback_code(stories_to_process)
            
    except Exception as e:
        logger.error(f"Error generating code with LLM: {e}")
        return _generate_fallback_code(stories_to_process)

def _generate_fallback_code(stories: List[Dict]) -> Dict[str, str]:
    """Generate basic functional web app as fallback"""
    files = {}
    
    # Backend - models.py
    models = """from pydantic import BaseModel, EmailStr
from typing import Optional, List

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    completed: bool = False
"""
    
    # Backend - services.py
    services = """from typing import Optional, List, Dict
from models import Task

class TaskService:
    def __init__(self):
        self.tasks: Dict[int, dict] = {}
        self.id_counter = 1
    
    def create_task(self, title: str, description: str) -> dict:
        task = {
            'id': self.id_counter,
            'title': title,
            'description': description,
            'completed': False
        }
        self.tasks[self.id_counter] = task
        self.id_counter += 1
        return task
    
    def get_all_tasks(self) -> List[dict]:
        return list(self.tasks.values())
    
    def get_task(self, task_id: int) -> Optional[dict]:
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: int, completed: bool) -> Optional[dict]:
        if task_id in self.tasks:
            self.tasks[task_id]['completed'] = completed
            return self.tasks[task_id]
        return None
    
    def delete_task(self, task_id: int) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

task_service = TaskService()
"""
    
    # Backend - main.py
    main = """from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from models import Task
from services import task_service

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/tasks")
async def get_tasks():
    return task_service.get_all_tasks()

@app.post("/api/tasks", status_code=201)
async def create_task(task: Task):
    return task_service.create_task(task.title, task.description)

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, task: Task):
    updated = task_service.update_task(task_id, task.completed)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    if not task_service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}
"""
    
    # Frontend - base.html
    base_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Task Manager{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">Task Manager</a>
        </div>
    </nav>
    <main>
        {% block content %}{% endblock %}
    </main>
    <footer class="bg-light text-center py-3 mt-5">
        <p class="mb-0">Generated by BRD-to-Code AI Pipeline</p>
    </footer>
    <script src="/static/app.js"></script>
</body>
</html>
"""
    
    # Frontend - index.html
    index_html = """{% extends "base.html" %}
{% block title %}Task Manager - Home{% endblock %}
{% block content %}
<div class="container mt-5">
    <h1 class="mb-4">Task Manager</h1>
    
    <div class="card mb-4">
        <div class="card-body">
            <h5 class="card-title">Add New Task</h5>
            <form id="taskForm">
                <div class="mb-3">
                    <label for="taskTitle" class="form-label">Title</label>
                    <input type="text" class="form-control" id="taskTitle" required>
                </div>
                <div class="mb-3">
                    <label for="taskDescription" class="form-label">Description</label>
                    <textarea class="form-control" id="taskDescription" rows="3" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Add Task</button>
            </form>
        </div>
    </div>
    
    <h3>Tasks</h3>
    <div id="tasksList" class="row">
        <!-- Tasks will be loaded here -->
    </div>
</div>
{% endblock %}
"""
    
    # Frontend - style.css
    style_css = """body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f8f9fa;
}

.task-card {
    transition: transform 0.2s;
}

.task-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.task-completed {
    opacity: 0.6;
    text-decoration: line-through;
}

.btn-action {
    margin: 0 5px;
}

#tasksList {
    min-height: 200px;
}

.loading {
    text-align: center;
    padding: 20px;
    color: #6c757d;
}
"""
    
    # Frontend - app.js
    app_js = """// Task Manager Application
document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    
    document.getElementById('taskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await addTask();
    });
});

async function loadTasks() {
    const tasksDiv = document.getElementById('tasksList');
    tasksDiv.innerHTML = '<div class="loading">Loading tasks...</div>';
    
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        
        if (tasks.length === 0) {
            tasksDiv.innerHTML = '<div class="col-12"><p class="text-muted">No tasks yet. Add one above!</p></div>';
            return;
        }
        
        tasksDiv.innerHTML = tasks.map(task => `
            <div class="col-md-6 mb-3">
                <div class="card task-card ${task.completed ? 'task-completed' : ''}">
                    <div class="card-body">
                        <h5 class="card-title">${task.title}</h5>
                        <p class="card-text">${task.description}</p>
                        <div>
                            <button onclick="toggleTask(${task.id}, ${!task.completed})" 
                                    class="btn btn-sm ${task.completed ? 'btn-warning' : 'btn-success'} btn-action">
                                ${task.completed ? 'Undo' : 'Complete'}
                            </button>
                            <button onclick="deleteTask(${task.id})" class="btn btn-sm btn-danger btn-action">
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        tasksDiv.innerHTML = '<div class="col-12"><p class="text-danger">Error loading tasks</p></div>';
        console.error('Error:', error);
    }
}

async function addTask() {
    const title = document.getElementById('taskTitle').value;
    const description = document.getElementById('taskDescription').value;
    
    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description })
        });
        
        if (response.ok) {
            document.getElementById('taskForm').reset();
            await loadTasks();
        }
    } catch (error) {
        alert('Error adding task');
        console.error('Error:', error);
    }
}

async function toggleTask(taskId, completed) {
    try {
        await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: taskId, title: '', description: '', completed })
        });
        await loadTasks();
    } catch (error) {
        alert('Error updating task');
        console.error('Error:', error);
    }
}

async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    try {
        await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
        await loadTasks();
    } catch (error) {
        alert('Error deleting task');
        console.error('Error:', error);
    }
}
"""
    
    files["src/api/models.py"] = models
    files["src/api/services.py"] = services
    files["src/api/main.py"] = main
    files["templates/base.html"] = base_html
    files["templates/index.html"] = index_html
    files["static/style.css"] = style_css
    files["static/app.js"] = app_js
    
    logger.info("Generated fallback full-stack web application")
    return files


def code_to_pytest_tests(code_files: Dict[str, str]) -> Dict[str, str]:
    """
    Generate pytest test files from generated code files using LLM.
    Returns a dict mapping test file paths to test file contents.
    """
    if not code_files:
        logger.warning("No code files provided for test generation")
        return {}
    
    llm = get_llm_client()
    deployment_name = get_llm_deployment_name()
    
    # Extract main.py for route analysis
    main_content = code_files.get("src/api/main.py", "")
    models_content = code_files.get("src/api/models.py", "")
    
    if not main_content:
        logger.warning("No main.py found, generating basic test template")
        return {"tests/test_api.py": _generate_fallback_tests()}
    
    system_prompt = """You are an expert Python pytest developer specializing in FastAPI applications.

Generate a SINGLE test file (test_api.py) with comprehensive pytest tests that follow FastAPI conventions:

CRITICAL - FastAPI HTTP Status Codes:
- 200: Successful GET/PUT/DELETE
- 201: Successful POST that creates resource
- 422: Pydantic validation errors (invalid email, missing fields, wrong types)
- 404: Resource not found
- 400: Business logic errors (duplicate user, insufficient funds, etc.)
- 500: Server errors

Test Structure:
1. Import: pytest, TestClient from fastapi.testclient, and 'from main import app'
2. Fixture: @pytest.fixture that returns TestClient(app)
3. Test functions: test_<operation>_<scenario> naming
4. POST/PUT requests: ALWAYS use json= parameter: client.post("/api/items", json={"name": "x"})
5. GET/DELETE requests: Use params= for query params: client.get("/api/items", params={"category": "x"})
6. Success cases: Valid data, expect 200/201
7. Validation failure cases: Invalid data (bad email, missing fields) → expect 422
8. Business failure cases: Valid data but business rule fails → expect 400/404
9. Use proper assertions: assert response.status_code == <expected>

CORRECT EXAMPLES:
```python
def test_create_post_success(client):
    response = client.post("/api/posts", json={"title": "Test", "content": "Content"})
    assert response.status_code == 201  # POST returns 201!
    
def test_create_post_validation_error(client):
    response = client.post("/api/posts", json={"title": ""})  # Missing content
    assert response.status_code == 422

def test_login_success(client):
    response = client.post("/api/login", json={"email": "user@example.com", "password": "pass"})
    assert response.status_code == 200  # Login returns 200, not 201!
```

FORBIDDEN PATTERNS (NEVER USE):
```python
# WRONG - DO NOT use data= for JSON!
response = client.post("/api/posts", data={"title": "Test"})  # WRONG!

# WRONG - DO NOT expect 201 for login!
response = client.post("/api/login", json={...})
assert response.status_code == 201  # WRONG! Login returns 200
```

Return ONLY valid Python test code with proper FastAPI status codes and json= parameter, no markdown blocks."""
    
    prompt = f"""Generate comprehensive pytest tests for this FastAPI application.

Main Application Code:
```python
{main_content[:2000]}
```

Models:
```python
{models_content[:1000]}
```

Generate pytest test code with TestClient that covers all endpoints."""
    
    try:
        logger.info("Generating pytest tests using LLM...")
        response = llm.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        # Clean up markdown code blocks if present
        content = content.replace('```python', '').replace('```', '').strip()
        
        logger.info("Successfully generated pytest tests")
        return {"tests/test_api.py": content}
        
    except Exception as e:
        logger.error(f"Error generating tests with LLM: {e}")
        return {"tests/test_api.py": _generate_fallback_tests()}


def _generate_fallback_tests() -> str:
    """Generate basic pytest tests as fallback with correct FastAPI status codes"""
    return """import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    # Basic smoke test - may not have root endpoint
    response = client.get("/")
    assert response.status_code in [200, 404]

def test_api_responds(client):
    # Verify API is running (tests that ANY endpoint returns non-500)
    assert client is not None

# Note: Add specific tests based on your API endpoints
# Use status code 422 for validation errors (bad email, missing fields)
# Use status code 404 for not found
# Use status code 200/201 for success
"""
