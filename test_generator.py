# Test case and pytest test generation logic using LLM
from typing import List, Dict
import logging
from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name

logger = logging.getLogger(__name__)

def stories_to_test_cases(stories: List[Dict]) -> List[Dict]:
    """
    Generate test case descriptions from Jira user stories.
    """
    test_cases = []
    for idx, story in enumerate(stories):
        summary = story["fields"].get("summary", f"Story {idx+1}")
        acceptance = story["fields"].get("description", "").split("Acceptance Criteria:")[-1].strip().split("\n-")
        acceptance = [a.strip("- ") for a in acceptance if a.strip()]
        for i, crit in enumerate(acceptance):
            test_cases.append({
                "story": summary,
                "test_case": f"TC_{idx+1}_{i+1}",
                "steps": [f"Step {i+1}: {crit}"],
                "expected": crit
            })
    return test_cases

def code_to_pytest_tests(code_files: Dict[str, str]) -> Dict[str, str]:
    """
    Generate executable pytest test files from code files using LLM.
    Returns a dict mapping test file paths to contents.
    """
    if not code_files or "src/api/main.py" not in code_files:
        logger.warning("No code files provided for test generation")
        return {}
    
    llm = get_llm_client()
    deployment_name = get_llm_deployment_name()
    
    main_code = code_files["src/api/main.py"]
    models_code = code_files.get("src/api/models.py", "")
    services_code = code_files.get("src/api/services.py", "")
    
    system_prompt = """You are an expert in Python pytest and FastAPI testing.
Generate comprehensive, executable pytest tests for the FastAPI code.

Requirements:
- Add sys.path setup at the beginning to import from src/api
- Import the service singleton from services.py and add an autouse fixture to reset state before each test
- CRITICAL: Examine the services.py code carefully to identify the EXACT attribute names (including underscore prefixes like _posts, _next_id)
- Use FastAPI TestClient
- Test all endpoints with valid and invalid data
- Test edge cases and error scenarios
- Include assertions for status codes, response structure, and data validation
- Test CRUD operations end-to-end
- Make tests executable and comprehensive
- Return ONLY valid Python test code, no explanations"""
    
    models_preview = models_code[:500] if models_code else ""
    main_preview = main_code[:1500] if main_code else ""
    services_preview = services_code[:1000] if services_code else ""
    
    prompt = f"""Generate pytest tests for this FastAPI application:

SERVICES (EXAMINE CAREFULLY FOR EXACT ATTRIBUTE NAMES):
{services_preview}

MODELS:
{models_preview}

MAIN:
{main_preview}

Return executable pytest code that tests all endpoints and functionality.

IMPORTANT: 
1. Start with path setup and imports:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "api"))
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
```

2. Add an autouse fixture to reset service state before each test:
   - Import the service singleton from services.py (e.g., `from services import blog_post_service`)
   - CRITICAL: Look at the SERVICES code above to find the EXACT attribute names
   - If attributes start with underscore (e.g., `_posts`, `_next_id`), use those exact names
   - In the fixture, clear all dict/list storage attributes (e.g., `._posts.clear()`)
   - Reset any ID counters to 1 (e.g., `._next_id = 1`)

Example fixture for a service with `_posts` and `_next_id`:
```python
from services import blog_post_service

@pytest.fixture(autouse=True)
def reset_service_state():
    blog_post_service._posts.clear()  # Use EXACT attribute name from services.py
    blog_post_service._next_id = 1    # Use EXACT attribute name from services.py
```

3. Then add comprehensive test functions for all endpoints."""
    
    try:
        logger.info("Generating executable pytest tests using LLM...")
        response = llm.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=3000
        )
        
        content = response.choices[0].message.content
        logger.debug(f"LLM test response length: {len(content)} chars")
        
        # Extract Python code from markdown if present
        import re
        code_match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
        if code_match:
            test_code = code_match.group(1)
        elif '```' in content:
            test_code = re.sub(r'```.*?\n', '', content).replace('```', '')
        else:
            test_code = content
        
        # Ensure imports are present
        if 'import pytest' not in test_code:
            test_code = "import pytest\n" + test_code
        if 'from fastapi.testclient import TestClient' not in test_code:
            test_code = test_code.replace('import pytest\n', 'import pytest\nfrom fastapi.testclient import TestClient\n')
        
        logger.info("Successfully generated executable pytest tests")
        return {"tests/test_api.py": test_code}
        
    except Exception as e:
        logger.error(f"Error generating tests with LLM: {e}")
        return _generate_fallback_tests(main_code)

def _generate_fallback_tests(main_code: str) -> Dict[str, str]:
    """Generate basic functional tests as fallback"""
    test_code = """import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "api"))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_user():
    response = client.post("/users", json={"name": "John Doe", "email": "john@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"

def test_get_user():
    # First create a user
    create_response = client.post("/users", json={"name": "Jane Doe", "email": "jane@example.com"})
    user_id = create_response.json()["id"]
    
    # Then get the user
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == "Jane Doe"

def test_get_nonexistent_user():
    response = client.get("/users/9999")
    assert response.status_code == 404

def test_create_item():
    response = client.post("/items", json={
        "name": "Pizza",
        "description": "Delicious cheese pizza",
        "price": 12.99
    })
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "Pizza"
    assert data["price"] == 12.99

def test_get_all_items():
    # Create some items first
    client.post("/items", json={"name": "Burger", "description": "Beef burger", "price": 8.99})
    client.post("/items", json={"name": "Fries", "description": "French fries", "price": 3.99})
    
    response = client.get("/items")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 2

def test_invalid_user_data():
    response = client.post("/users", json={"name": "No Email"})
    assert response.status_code == 422
"""
    
    logger.info("Generated fallback executable tests")
    return {"tests/test_api.py": test_code}
