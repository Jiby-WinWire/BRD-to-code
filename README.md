# 🤖 BRD-to-Code AI Agent Pipeline

> Automated transformation of business requirements into production-ready code using AI

## Overview

This project implements an intelligent AI-driven pipeline that transforms natural language requirements into:
- ✅ **Structured BRD** (Business Requirements Document)
- ✅ **Jira User Stories** (JSON format, ready for import)
- ✅ **Production FastAPI Code** (models, services, routes)
- ✅ **Comprehensive Tests** (pytest with full coverage)
- ✅ **Validated Output** (automatically tested and verified)

The pipeline uses **Azure OpenAI** (GPT-4) and **LangGraph** for intelligent orchestration with a RE-ACT (Reason-Act-Observe) pattern.

## 🏗️ Architecture

The pipeline consists of **5 integrated agents** working in a LangGraph state machine:

### 1. **BRD Generator Agent** (`brd_generator.py`)
   - **Input**: Natural language prompt (e.g., "build a blog API")
   - **Process**: Uses Azure OpenAI to analyze requirements and generate structured BRD
   - **Output**: Comprehensive BRD JSON with:
     - Business goals and objectives
     - Functional requirements (FR1, FR2, etc.)
     - Non-functional requirements (NFR1, NFR2, etc.)
     - Stakeholders and acceptance criteria

### 2. **Jira Story Generator Agent** (`brd_to_jira.py`)
   - **Input**: BRD JSON from previous step
   - **Process**: Converts requirements into user stories following Jira schema
   - **Output**: Array of Jira-compatible user stories with:
     - Summary, description, priority
     - Labels (functional/non-functional)
     - Acceptance criteria
     - Story type (Story, Epic, Task)

### 3. **Code Generator Agent** (`story_to_code.py`)
   - **Input**: Jira user stories
   - **Process**: Generates production-ready FastAPI application using GPT-4
   - **Output**: Three code files:
     - `models.py` - Pydantic models with validation
     - `services.py` - Business logic with in-memory storage + singleton export
     - `main.py` - FastAPI routes using the service singleton

### 4. **Test Generator Agent** (`test_generator.py`)
   - **Input**: Generated code files + user stories
   - **Process**: Creates comprehensive pytest test suite
   - **Output**: 
     - Test case descriptions
     - `test_api.py` - Full pytest suite with:
       - Valid/invalid input tests
       - CRUD operation tests
       - End-to-end workflow tests
       - Proper test isolation fixtures

### 5. **Validation Agent** (`orchestrator.py`)
   - **Input**: Generated code + tests
   - **Process**: 
     - Writes all files to `output/` directory
     - Runs pytest validation
     - Checks exit codes
     - Retries on failure (up to 3 times)
   - **Output**: 
     - Validation status (pass/fail)
     - Test execution logs
     - Helper files (run.py, README.md, requirements.txt)

## 🔄 LangGraph Orchestration

The pipeline uses **LangGraph StateGraph** with conditional routing:

```python
Workflow:
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│ BRD Generator│────▶│Jira Stories │
│   Prompt    │     └──────────────┘     └─────────────┘
└─────────────┘                                 │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Complete   │◀────│  Validation  │◀────│    Code     │
│             │     │   + Retry    │     │ Generator   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     │
                           │                     ▼
                           │              ┌─────────────┐
                           └──────────────│    Test     │
                              (on fail)   │ Generator   │
                                          └─────────────┘
```

**RE-ACT Pattern**: The validation node can loop back to regenerate code/tests if validation fails (max 3 retries).

## Expected Workflow

### Interactive Mode (Recommended)

```bash
# Start the interactive pipeline
python src/main.py
```

The interactive CLI will:
1. Load environment configuration from `.env`
2. Prompt you to enter your API requirements (e.g., "build a task management API")
3. Run the full pipeline automatically
4. Generate all code, tests, and documentation
5. Display results and next steps

### Programmatic Mode

```python
from agents.orchestrator import react_pipeline

# Run pipeline with a prompt
result = react_pipeline("build a blog API with CRUD operations")

# Access generated artifacts
print(result["brd_json"])         # Business requirements
print(result["stories"])          # Jira user stories
print(result["code_files"])       # Generated code
print(result["validation_passed"]) # Test results
```

### Generated Output

After running, check the `output/` directory:

```
output/
├── src/api/
│   ├── models.py       # Pydantic models
│   ├── services.py     # Business logic + singleton
│   └── main.py         # FastAPI application
├── tests/
│   └── test_api.py     # Pytest test suite
├── run.py              # Server launcher
├── requirements.txt    # Dependencies
└── README.md          # API documentation
```

## Project Structure

```
BRD-to-code/
├── src/
│   ├── agents/
│   │   ├── brd_generator.py      # Generates BRD from natural language
│   │   ├── brd_to_jira.py        # Converts BRD to Jira stories
│   │   ├── story_to_code.py      # Generates FastAPI code from stories
│   │   ├── test_generator.py     # Creates pytest test suites
│   │   └── orchestrator.py       # LangGraph pipeline orchestrator
│   ├── infrastructure/
│   │   └── azure_clients.py      # Azure OpenAI client setup
│   └── main.py                   # Interactive CLI entry point
├── output/                       # Generated code output directory
├── .env                          # Azure OpenAI credentials
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Setup & Installation

### Prerequisites

- Python 3.11 or higher
- Azure OpenAI API access
- Git (optional)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BRD-to-code
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Azure OpenAI**
   
   Create a `.env` file in the project root:
   ```env
   AZURE_OPENAI_API_KEY=your-api-key-here
   AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=model_deployment_name
   AZURE_OPENAI_API_VERSION=2024-08-01-preview
   ```

5. **Run the pipeline**
   ```bash
   python src/main.py
   ```

## Usage Examples

### Example 1: Blog API
```
Enter your API requirements: build a simple blog API with create post, list posts, get post by id, and delete post

✅ Generated:
   - 4 functional requirements
   - 5 non-functional requirements
   - 8 Jira user stories
   - 3 code files (models, services, main)
   - 1 test file with 9 tests (all passing)
```

### Example 2: Task Management API
```
Enter your API requirements: create a task management system with users, projects, and tasks with priorities

✅ Generated:
   - Complete BRD with relationships
   - User stories for all entities
   - Multi-model FastAPI code
   - Comprehensive test coverage
```

### Example 3: E-commerce Products API
```
Enter your API requirements: product catalog API with categories, inventory tracking, and search

✅ Generated:
   - Domain-specific models
   - Search and filter logic
   - Inventory management
   - End-to-end tests
```


## Key Features

### 🎯 Intelligent Code Generation
- **Domain-Specific**: Generates code tailored to your specific requirements (not templates)
- **Production-Ready**: Includes proper validation, error handling, and structure
- **Best Practices**: Follows FastAPI conventions and Python standards

### 🔄 Self-Healing Pipeline
- **Automatic Retry**: If tests fail, regenerates code/tests (up to 3 attempts)
- **Error Analysis**: Uses pytest output to understand and fix issues
- **Validation**: Ensures all generated code is tested and working

### 🧪 Comprehensive Testing
- **Full Coverage**: Tests all endpoints with valid/invalid inputs
- **Test Isolation**: Proper fixtures reset state between tests
- **Edge Cases**: Includes boundary conditions and error scenarios

### 📝 Complete Documentation
- **Auto-Generated**: README, API docs, and inline comments
- **Swagger/OpenAPI**: Interactive API documentation at `/docs`
- **Usage Examples**: Helper files and quick start guides

### 🛠️ Developer Experience
- **Interactive CLI**: User-friendly prompts and feedback
- **Instant Feedback**: Real-time status updates during generation
- **Easy to Run**: Single command to generate complete application

## Technical Stack

- **AI/ML**: Azure OpenAI GPT-4
- **Orchestration**: LangGraph 1.1.6 (StateGraph with conditional edges)
- **Web Framework**: FastAPI 0.115.12
- **Testing**: Pytest 9.0.2 with fixtures
- **Validation**: Pydantic 2.10.6
- **Server**: Uvicorn with auto-reload
- **Environment**: Python 3.11+

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key | `abc123...` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://xxx.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | `gpt4o_mktgenai` |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-08-01-preview` |

### Pipeline Configuration

Edit `orchestrator.py` to customize:
- `RETRY_LIMIT`: Max retries on test failure (default: 3)
- `recursion_limit`: LangGraph recursion depth (default: 10)
- Temperature settings for each agent (0.2-0.3 for deterministic output)

## Troubleshooting

### Issue: Tests Fail During Generation

**Cause**: Service singleton import mismatch  
**Solution**: Automatically fixed by retry mechanism. The pipeline will regenerate code with correct imports.

### Issue: Azure OpenAI Rate Limit

**Cause**: Too many requests too quickly  
**Solution**: Pipeline includes automatic rate limit handling. Wait a moment and retry.

### Issue: Generated Code Quality

**Cause**: LLM output varies between runs  
**Solution**: Run pipeline again with more specific requirements. The more detailed your prompt, the better the output.

### Issue: Import Errors in Generated Code

**Cause**: Missing dependencies  
**Solution**: Check `output/requirements.txt` and install: `pip install -r output/requirements.txt`

## Extending the Pipeline

### Adding New Agents

1. Create agent file in `src/agents/`
2. Define agent function that takes state dict and returns updates
3. Add node to LangGraph in `orchestrator.py`
4. Define routing logic with `add_conditional_edges`

### Customizing Code Templates

Edit prompt templates in:
- `brd_generator.py` - BRD structure
- `story_to_code.py` - Code generation patterns
- `test_generator.py` - Test structure

### Adding New Validations

Modify `orchestrator.py` validation logic:
```python
def validate_node(state):
    # Add custom validation logic
    if custom_check_failed:
        state["validation_passed"] = False
    return state
```

## Roadmap

- [ ] Support for multiple frameworks (Django, Flask, Express.js)
- [ ] Database integration generation (PostgreSQL, MongoDB)
- [ ] Authentication/authorization code generation
- [ ] Deployment configuration (Docker, Kubernetes)
- [ ] CI/CD pipeline generation (GitHub Actions, Azure Pipelines)
- [ ] OpenAPI spec import support
- [ ] Direct Jira API integration
- [ ] Multi-language support (Node.js, Go, Java)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

[Your License Here]

## Changelog

### v1.0.0 (April 2026)
- ✅ LangGraph orchestration with RE-ACT pattern
- ✅ Azure OpenAI GPT-4 integration
- ✅ Interactive CLI interface
- ✅ Self-healing retry mechanism
- ✅ Comprehensive test generation
- ✅ Service singleton pattern fix
- ✅ Dynamic attribute name detection
- ✅ Helper file auto-generation

---

**Made with ❤️ using Azure OpenAI and LangGraph**
