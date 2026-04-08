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
    functional_stories = [s for s in stories if 'functional' in s['fields'].get('labels', [])]
    
    # Limit to first 5 functional stories for better quality
    stories_to_process = functional_stories[:5] if functional_stories else stories[:5]
    
    system_prompt = """You are an expert Python FastAPI developer. Generate production-ready, executable FastAPI code based on user stories.
Generate THREE separate code files with REAL implementation:
1. models.py: Pydantic models with proper validation
2. services.py: Business logic with in-memory storage (dicts/lists) + MUST export a singleton instance at the bottom
3. main.py: FastAPI routes that import and use the service singleton from services.py

Requirements:
- Use realistic field names and data structures
- Implement actual CRUD operations with in-memory storage
- Include proper error handling
- Use HTTP status codes correctly
- Make it executable and testable
- CRITICAL: services.py MUST end with a singleton export like: `blog_service = BlogService()`
- CRITICAL: main.py MUST import the singleton from services: `from services import blog_service`
- Return ONLY valid Python code, no explanations"""
    
    stories_text = "\n".join([
        f"{i+1}. {s['fields'].get('summary', '')}: {s['fields'].get('description', '')[:200]}"
        for i, s in enumerate(stories_to_process)
    ])
    
    prompt = f"""Generate executable FastAPI code for these user stories:

{stories_text}

Return a JSON object with three keys: "models", "services", "main" containing the Python code for each file."""
    
    try:
        logger.info(f"Generating executable code for {len(stories_to_process)} stories using LLM...")
        response = llm.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
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
                "src/api/main.py": code_json.get("main", "from fastapi import FastAPI\napp = FastAPI()\n")
            }
            logger.info("Successfully generated executable code files")
            return files
        else:
            logger.warning("Could not parse JSON from LLM response, using fallback")
            return _generate_fallback_code(stories_to_process)
            
    except Exception as e:
        logger.error(f"Error generating code with LLM: {e}")
        return _generate_fallback_code(stories_to_process)

def _generate_fallback_code(stories: List[Dict]) -> Dict[str, str]:
    """Generate basic functional code as fallback"""
    files = {}
    
    # Generate models
    models = ["from pydantic import BaseModel\nfrom typing import Optional\n\n"]
    models.append("class User(BaseModel):\n    id: Optional[int] = None\n    name: str\n    email: str\n\n")
    models.append("class Item(BaseModel):\n    id: Optional[int] = None\n    name: str\n    description: str\n    price: float\n\n")
    
    # Generate services with actual logic
    services = ["# In-memory storage\nusers_db = {}\nitems_db = {}\nuser_id_counter = 1\nitem_id_counter = 1\n\n"]
    services.append("def create_user(name: str, email: str):\n    global user_id_counter\n    user = {'id': user_id_counter, 'name': name, 'email': email}\n    users_db[user_id_counter] = user\n    user_id_counter += 1\n    return user\n\n")
    services.append("def get_user(user_id: int):\n    return users_db.get(user_id)\n\n")
    services.append("def create_item(name: str, description: str, price: float):\n    global item_id_counter\n    item = {'id': item_id_counter, 'name': name, 'description': description, 'price': price}\n    items_db[item_id_counter] = item\n    item_id_counter += 1\n    return item\n\n")
    services.append("def get_all_items():\n    return list(items_db.values())\n\n")
    
    # Generate main with actual routes
    main = ["from fastapi import FastAPI, HTTPException\nfrom .models import User, Item\nfrom . import services\n\napp = FastAPI()\n\n"]
    main.append("@app.post('/users', response_model=User)\ndef create_user(user: User):\n    return services.create_user(user.name, user.email)\n\n")
    main.append("@app.get('/users/{user_id}')\ndef get_user(user_id: int):\n    user = services.get_user(user_id)\n    if not user:\n        raise HTTPException(status_code=404, detail='User not found')\n    return user\n\n")
    main.append("@app.post('/items', response_model=Item)\ndef create_item(item: Item):\n    return services.create_item(item.name, item.description, item.price)\n\n")
    main.append("@app.get('/items')\ndef get_items():\n    return services.get_all_items()\n\n")
    
    files["src/api/models.py"] = "".join(models)
    files["src/api/services.py"] = "".join(services)
    files["src/api/main.py"] = "".join(main)
    
    logger.info("Generated fallback executable code")
    return files
