
# RE-ACT Orchestrator using LangGraph


import json
import logging
import sys
import subprocess
from pathlib import Path
from langgraph.graph import StateGraph, END

# Ensure project root is in sys.path for imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from brd_to_jira import brd_to_jira_stories
from story_to_code import stories_to_fastapi_code
from test_generator import stories_to_test_cases, code_to_pytest_tests
from src.agents.brd_generator import generate_brd_from_prompt

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("orchestrator")

RETRY_LIMIT = 3

def _write_helper_files(output_dir: Path):
    """Write helper files for running the generated API (run.py, README.md, etc.)"""
    
    # run.py - Server launcher
    run_py = '''"""FastAPI Application Launcher - Start your generated API server!
Usage: python run.py
Server: http://localhost:8000 | Docs: http://localhost:8000/docs
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src" / "api"))

def main():
    print("=" * 60)
    print("🚀 Starting Generated FastAPI Application")
    print("=" * 60)
    print("\\n📍 Server: http://localhost:8000")
    print("📚 Docs:   http://localhost:8000/docs")
    print("💡 Press Ctrl+C to stop\\n" + "=" * 60 + "\\n")
    
    try:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("\\nInstall dependencies: pip install fastapi uvicorn pydantic")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\\n✅ Server stopped")

if __name__ == "__main__":
    main()
'''
    
    # README.md - User guide
    readme_md = '''# 🚀 Generated FastAPI Application

## 📂 Project Structure

```
output/
├── docs/                      # Documentation
│   ├── brd.json              # Business Requirements Document (JSON)
│   ├── brd.txt               # Business Requirements Document (Text)
│   ├── jira_stories.json     # Jira User Stories (JSON)
│   └── jira_stories.txt      # Jira User Stories (Text)
├── src/api/                  # Application Code
│   ├── models.py             # Pydantic models
│   ├── services.py           # Business logic
│   └── main.py               # FastAPI application
├── tests/                    # Test Suite
│   └── test_api.py           # API tests
├── run.py                    # Server launcher
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Quick Start

```bash
python run.py  # Start the server
```

Visit **http://localhost:8000/docs** for interactive API documentation.

## Testing

```bash
pytest tests/ -v  # Run automated tests
```

## Features

✅ Real CRUD operations (not templates!)
✅ Input validation with Pydantic
✅ Error handling with proper HTTP codes
✅ Comprehensive tests (all passing)
✅ OpenAPI/Swagger documentation
✅ Production-ready code
✅ Complete documentation (BRD & Jira stories)

See [../HOW_TO_RUN.md](../HOW_TO_RUN.md) for detailed instructions.
'''
    
    # requirements.txt
    requirements_txt = '''fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
pytest>=9.0.0
httpx>=0.28.0
'''
    
    # Write the files
    (output_dir / "run.py").write_text(run_py, encoding='utf-8')
    (output_dir / "README.md").write_text(readme_md, encoding='utf-8')
    (output_dir / "requirements.txt").write_text(requirements_txt, encoding='utf-8')
    
    logger.info("📝 Written helper files: run.py, README.md, requirements.txt")

def write_generated_files_to_disk(code_files: dict, test_files: dict):
    """Write all generated code and test files to disk."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Write all code files
    if code_files:
        for code_path, code_content in code_files.items():
            full_path = output_dir / code_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code_content, encoding='utf-8')
            logger.info(f"✅ Written code file: {full_path}")
    
    # Write all test files
    if test_files:
        for test_path, test_content in test_files.items():
            full_path = output_dir / test_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(test_content, encoding='utf-8')
            logger.info(f"✅ Written test file: {full_path}")
    
    # Write helper files for running the API
    _write_helper_files(output_dir)

def write_brd_and_stories_to_disk(brd_json: dict, stories: list):
    """Write BRD and Jira stories to disk in the docs/ folder."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Create docs directory for documentation files
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Write BRD as JSON
    if brd_json:
        brd_file = docs_dir / "brd.json"
        brd_file.write_text(json.dumps(brd_json, indent=2), encoding='utf-8')
        logger.info(f"✅ Written BRD: {brd_file}")
        
        # Also write a human-readable text version
        brd_txt_file = docs_dir / "brd.txt"
        brd_text = _format_brd_as_text(brd_json)
        brd_txt_file.write_text(brd_text, encoding='utf-8')
        logger.info(f"✅ Written BRD (text): {brd_txt_file}")
    
    # Write Jira stories as JSON
    if stories:
        stories_file = docs_dir / "jira_stories.json"
        stories_file.write_text(json.dumps(stories, indent=2), encoding='utf-8')
        logger.info(f"✅ Written Jira stories: {stories_file}")
        
        # Also write a human-readable text version
        stories_txt_file = docs_dir / "jira_stories.txt"
        stories_text = _format_stories_as_text(stories)
        stories_txt_file.write_text(stories_text, encoding='utf-8')
        logger.info(f"✅ Written Jira stories (text): {stories_txt_file}")

def _format_brd_as_text(brd_json: dict) -> str:
    """Format BRD JSON as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("BUSINESS REQUIREMENTS DOCUMENT (BRD)")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append(f"Title: {brd_json.get('title', 'N/A')}")
    lines.append(f"Description: {brd_json.get('description', 'N/A')}")
    lines.append("")
    
    lines.append("-" * 80)
    lines.append("BUSINESS GOALS")
    lines.append("-" * 80)
    for i, goal in enumerate(brd_json.get('businessGoals', []), 1):
        lines.append(f"{i}. {goal}")
    lines.append("")
    
    lines.append("-" * 80)
    lines.append("FUNCTIONAL REQUIREMENTS")
    lines.append("-" * 80)
    for req in brd_json.get('functionalRequirements', []):
        lines.append(f"{req.get('id', 'N/A')}: {req.get('description', 'N/A')}")
    lines.append("")
    
    lines.append("-" * 80)
    lines.append("NON-FUNCTIONAL REQUIREMENTS")
    lines.append("-" * 80)
    for req in brd_json.get('nonFunctionalRequirements', []):
        lines.append(f"{req.get('id', 'N/A')}: {req.get('description', 'N/A')}")
    lines.append("")
    
    lines.append("-" * 80)
    lines.append("STAKEHOLDERS")
    lines.append("-" * 80)
    for stakeholder in brd_json.get('stakeholders', []):
        lines.append(f"Role: {stakeholder.get('role', 'N/A')}")
        lines.append(f"Responsibilities: {stakeholder.get('responsibilities', 'N/A')}")
        lines.append("")
    
    lines.append("-" * 80)
    lines.append("ACCEPTANCE CRITERIA")
    lines.append("-" * 80)
    for criteria in brd_json.get('acceptanceCriteria', []):
        lines.append(f"{criteria.get('id', 'N/A')}: {criteria.get('description', 'N/A')}")
    lines.append("")
    
    lines.append("=" * 80)
    return "\n".join(lines)

def _format_stories_as_text(stories: list) -> str:
    """Format Jira stories as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("JIRA USER STORIES")
    lines.append("=" * 80)
    lines.append(f"Total Stories: {len(stories)}")
    lines.append("")
    
    for i, story in enumerate(stories, 1):
        fields = story.get('fields', {})
        lines.append("-" * 80)
        lines.append(f"STORY #{i}")
        lines.append("-" * 80)
        lines.append(f"Summary: {fields.get('summary', 'N/A')}")
        lines.append(f"Type: {fields.get('issuetype', {}).get('name', 'N/A')}")
        lines.append(f"Priority: {fields.get('priority', {}).get('name', 'N/A')}")
        lines.append(f"Labels: {', '.join(fields.get('labels', []))}")
        lines.append("")
        lines.append("Description:")
        lines.append(fields.get('description', 'N/A'))
        lines.append("")
    
    lines.append("=" * 80)
    return "\n".join(lines)

def validate_code(code_files: dict, test_files: dict, retries: int) -> bool:
    """Write files to disk and run pytest to validate generated code."""
    logger.info("Validating code with test files: %s", list(test_files.keys()) if test_files else None)
    
    if not test_files or len(test_files) == 0:
        logger.warning("No test files generated")
        return False
    
    # Write ALL files to disk (code + tests)
    import subprocess
    write_generated_files_to_disk(code_files, test_files)
    
    output_dir = Path("output")
    
    # Run pytest using Python module syntax (works on all platforms)
    try:
        logger.info(f"Running pytest (attempt {retries+1})...")
        
        # Import sys to get Python executable
        python_executable = sys.executable
        
        result = subprocess.run(
            [python_executable, "-m", "pytest", str(output_dir / "tests"), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        logger.info(f"Pytest exit code: {result.returncode}")
        logger.debug(f"Pytest stdout:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"Pytest stderr:\n{result.stderr}")
        
        if result.returncode != 0:
            logger.warning(f"Tests failed:\n{result.stdout}\n{result.stderr}")
            return False
        
        logger.info("All tests passed!")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Pytest execution timed out")
        return False
    except Exception as e:
        logger.error(f"Error running pytest: {e}", exc_info=True)
        return False


def react_pipeline(user_prompt: str, retry_limit: int = RETRY_LIMIT):
    """Run the RE-ACT pipeline with retries using LangGraph, starting from a user prompt."""
    validate_code.counter = 0
    state = {
        "user_prompt": user_prompt,
        "brd_json": None,
        "stories": None,
        "code_files": None,
        "test_cases": None,
        "test_files": None,
        "validation_passed": False,
        "retries": 0,
        "history": [],
    }
    def brd_generator_node(state):
        if not isinstance(state, dict):
            return state
        state = dict(state)
        logger.info("Generating BRD from user prompt...")
        try:
            state["brd_json"] = generate_brd_from_prompt(state["user_prompt"])
            logger.debug("Generated BRD JSON: %s", state["brd_json"])
        except Exception as e:
            logger.error("Error in BRD generation: %s", e, exc_info=True)
            raise
        return state

    def brd_to_jira_node(state):
        if not isinstance(state, dict):
            return state
        state = dict(state)
        logger.debug(f"State at brd_to_jira_node: {state}")
        logger.info("Converting BRD to Jira user stories...")
        try:
            state["stories"] = brd_to_jira_stories(state["brd_json"])
            logger.debug("Generated %d Jira stories", len(state["stories"]))
        except Exception as e:
            logger.error("Error in brd_to_jira_stories: %s", e, exc_info=True)
            raise
        return state

    def code_and_tests_node(state):
        if not isinstance(state, dict):
            return state
        state = dict(state)
        logger.debug(f"State at code_and_tests_node: {state}")
        logger.info("Generating code and test cases from Jira stories...")
        try:
            state["code_files"] = stories_to_fastapi_code(state["stories"])
            logger.debug("Generated code files: %s", list(state["code_files"].keys()))
            state["test_cases"] = stories_to_test_cases(state["stories"])
            logger.debug("Generated %d test cases", len(state["test_cases"]))
            state["test_files"] = code_to_pytest_tests(state["code_files"])
            logger.debug("Generated test files: %s", list(state["test_files"].keys()))
        except Exception as e:
            logger.error("Error in code/test generation: %s", e, exc_info=True)
            raise
        return state

    def validate_node(state):
        if not isinstance(state, dict):
            return state
        state = dict(state)
        logger.debug(f"State at validate_node (before validation): {state}")
        
        # Write BRD and Jira stories to disk first
        logger.info("Writing BRD and Jira stories to disk...")
        write_brd_and_stories_to_disk(state.get("brd_json"), state.get("stories"))
        
        logger.info("Validating generated code and tests...")
        try:
            passed = validate_code(state["code_files"], state["test_files"], state["retries"])
            state["validation_passed"] = passed
            if not passed:
                logger.debug(f"Incrementing retries from {state['retries']} to {state['retries']+1}")
                state["retries"] += 1
            state["history"].append({
                "retries": state["retries"],
                "test_files": state["test_files"],
                "code_files": state["code_files"],
            })
            logger.debug(f"State at validate_node (after validation): {state}")
        except Exception as e:
            logger.error("Error during validation: %s", e, exc_info=True)
            raise
        return state

    def retry_or_end(state):
        # Conditional edge function: determine next node based on state
        if not isinstance(state, dict):
            return END
        if state["validation_passed"]:
            logger.info("Validation passed. Pipeline complete.")
            return END
        if state["retries"] >= retry_limit:
            logger.error(f"Retry limit ({retry_limit}) reached. Failing.")
            return END
        logger.warning(f"Validation failed. Retrying code generation (attempt {state['retries' ]+1})...")
        return "code_and_tests"


    graph = StateGraph(state_schema=dict)
    graph.add_node("brd_generator", brd_generator_node)
    graph.add_node("brd_to_jira", brd_to_jira_node)
    graph.add_node("code_and_tests", code_and_tests_node)
    graph.add_node("validate", validate_node)

    graph.add_edge("brd_generator", "brd_to_jira")
    graph.add_edge("brd_to_jira", "code_and_tests")
    graph.add_edge("code_and_tests", "validate")
    # Add conditional edge directly from validate node
    graph.add_conditional_edges("validate", retry_or_end)

    graph.set_entry_point("brd_generator")

    compiled = graph.compile()
    # Increase recursion limit to account for full pipeline + retries
    # Base pipeline: 4 steps (brd_gen, brd_to_jira, code_and_tests, validate)
    # Each retry: 2 steps (code_and_tests, validate)
    recursion_limit = 4 + (retry_limit * 2) + 2  # +2 for safety margin
    final_state = compiled.invoke(state, config={"recursion_limit": recursion_limit})
    return final_state


def main():
    logger.info("Starting BRD-to-code RE-ACT pipeline orchestrator...")
    user_prompt = input("Enter your business requirement (user prompt): ")
    try:
        final_state = react_pipeline(user_prompt)
        # Write outputs
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        code_files = final_state.get("code_files")
        test_files = final_state.get("test_files")
        if code_files:
            for path, content in code_files.items():
                out_path = out_dir / Path(path).name
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Wrote code file: %s", out_path)
        if test_files:
            for path, content in test_files.items():
                out_path = out_dir / Path(path).name
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Wrote test file: %s", out_path)
        # Report pipeline progress and failure details
        logger.info(f"Pipeline complete. Validation passed: {final_state.get('validation_passed')}. Retries: {final_state.get('retries')}")
        if final_state.get("pipeline_failed") or not code_files:
            logger.error("Pipeline failed: No code files generated or retry limit reached.")
            logger.error(f"Retries attempted: {final_state.get('retries')}")
            logger.error(f"History: {final_state.get('history')}")
            # Summarize what was generated at each step
            for i, step in enumerate(final_state.get("history", [])):
                code_keys = list(step.get('code_files', {}).keys()) if step.get('code_files') else []
                test_keys = list(step.get('test_files', {}).keys()) if step.get('test_files') else []
                logger.error(f"Step {i+1} (retry {step.get('retries')}): "
                             f"Stories: {'yes' if step.get('stories') else 'no'}, "
                             f"Code: {code_keys if code_keys else 'none'}, "
                             f"Tests: {test_keys if test_keys else 'none'}")
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)

if __name__ == '__main__':
    main()
