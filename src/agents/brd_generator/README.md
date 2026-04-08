# BRD Generator Agent

Enterprise-grade agent for generating comprehensive Business Requirements Documents (BRDs) from natural language prompts.

## 🏗️ Architecture

The BRD Generator follows the **Agent Base Pattern** with:

```
┌─────────────────────────────────────────────────────────────┐
│                    BRD Generator Agent                       │
│                 (extends AgentClass)                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Memory     │  │   Policy     │  │    Task      │      │
│  │   Manager    │  │   Manager    │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│        │                  │                  │               │
│        ▼                  ▼                  ▼               │
│  ┌──────────────────────────────────────────────────┐      │
│  │              BRD Generation Tool                  │      │
│  │         (ToolClass wrapper)                       │      │
│  └──────────────────────────────────────────────────┘      │
│                        │                                     │
│                        ▼                                     │
│              Azure OpenAI (GPT-4)                           │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    ┌────────┐      ┌──────────────┐   ┌──────────────┐
    │ Redis  │      │ Azure Search │   │  Discovery   │
    │ Cache  │      │   (Caching)  │   │   Service    │
    └────────┘      └──────────────┘   └──────────────┘
```

## 🎯 Features

### 1. **LLM-Powered BRD Generation**
- Generates comprehensive BRDs from natural language
- Structured JSON output with markdown formatting
- Includes all standard BRD sections:
  - Title & Description
  - Business Goals
  - Functional Requirements
  - Non-Functional Requirements
  - Stakeholders
  - Acceptance Criteria
  - Assumptions & Constraints
  - Risk Analysis

### 2. **Semantic Caching**
- Azure Search vector similarity search
- Reuses similar BRDs (configurable threshold: 0.85)
- Reduces LLM costs and latency
- Azure OpenAI embeddings for semantic matching

### 3. **State Management**
- Redis-based task tracking
- BRDAgentStatus Pydantic model
- Token usage monitoring
- Session management
- 24-hour TTL for tasks

### 4. **Policy-Based Access Control**
- Discovery Service integration
- Three-tier validation:
  - **Agent Policy**: Can this agent run?
  - **Resource Policy**: Can access Azure OpenAI/Redis?
  - **Task Policy**: Can generate BRD for this request?
- Parallel policy checks for performance

### 5. **A2A Protocol Support**
- SendTaskRequest/SendTaskResponse
- Task lifecycle management
- Compatible with Supervisor/Planner agents
- RESTful A2A server mode

## 📦 Components

### Files

```
brd_generator/
├── __init__.py                 # Package exports
├── agent_executor.py           # Entry point & CLI
├── brd_generator_agent.py      # Main agent class
├── brd_generator_tool.py       # Tool wrapper
├── memory_manager.py           # Redis & Azure Search
├── policy_manager.py           # Discovery Service client
├── data/
│   └── policy_types.json       # Policy configuration
├── prompts/
│   └── brd_generation.prompt   # System prompts (future)
└── README.md                   # This file
```

### Key Classes

#### **BRDGeneratorAgent**
Main agent class extending AgentClass.

```python
agent = BRDGeneratorAgent(
    session_id="user-123",
    redis_url="redis://localhost:6379",
    azure_openai_endpoint="https://xxx.openai.azure.com/",
    azure_openai_key="key",
    azure_openai_deployment="gpt4o",
    enable_caching=True,
    enable_policy=False
)

result = await agent.generate_brd(
    user_prompt="Create a CRM system...",
    task_id="task-001"
)
```

#### **BRDMemoryManager**
Manages state persistence and caching.

```python
memory_manager = BRDMemoryManager(
    redis_client=redis_client,
    azure_search_endpoint="https://xxx.search.windows.net",
    azure_search_key="key",
    azure_openai_endpoint="https://xxx.openai.azure.com/"
)

# Cache check
cached = await memory_manager.search_cached_brd(
    user_prompt="...",
    similarity_threshold=0.85
)

# Save status
await memory_manager.push_brd_status(task_id, status)
```

#### **PolicyManager**
Validates execution against policies.

```python
policy_manager = PolicyManager(
    discovery_app_url="http://discovery:8090",
    client_id="brd-generator",
    agent_url="http://localhost:8001"
)

result = policy_manager.validate_all_policies(
    session_id="user-123",
    task_data={"query": "..."},
    resources=["azure_openai", "redis"],
    task_type="brd_generation"
)

if result.all_passed:
    # Execute task
    pass
```

#### **BRDAgentStatus**
Pydantic model for state tracking.

```python
status = BRDAgentStatus(
    status="completed",
    user_prompt="Create a CRM system...",
    brd_json={...},
    brd_markdown="# CRM System\n...",
    input_tokens=500,
    output_tokens=1500,
    total_tokens=2000,
    cache_hit=False,
    task_id="task-001"
)
```

## 🚀 Usage

### Standalone Mode

Run a single BRD generation test:

```bash
python -m src.agents.brd_generator.agent_executor --mode test
```

Output saved to `output/brd_test/`:
- `test_brd.json` - Structured JSON
- `test_brd.md` - Markdown format

### A2A Server Mode

Start as HTTP server for agent-to-agent communication:

```bash
python -m src.agents.brd_generator.agent_executor --mode server --port 8001
```

Server endpoints:
- `POST /tasks/send` - SendTaskRequest
- `GET /tasks/{task_id}` - Get task status
- `GET /health` - Health check

### Programmatic Usage

```python
from src.agents.brd_generator import BRDGeneratorAgent

# Create agent
agent = BRDGeneratorAgent(
    session_id="user-session-123",
    redis_url="redis://localhost:6379",
    azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_openai_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_openai_deployment="gpt4o_mktgenai",
    enable_caching=True
)

# Generate BRD
result = await agent.generate_brd(
    user_prompt="Build a task management app...",
    task_id="task-001"
)

print(result['brd_json'])
print(result['brd_markdown'])
```

## ⚙️ Configuration

### Environment Variables

Required:
```bash
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt4o_mktgenai
REDIS_URL=redis://localhost:6379
```

Optional (for caching):
```bash
AZURE_SEARCH_ENDPOINT=https://xxx.search.windows.net
AZURE_SEARCH_KEY=your_search_key
AZURE_SEARCH_INDEX=brd-cache-index
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
ENABLE_CACHING=true
```

Optional (for policy):
```bash
DISCOVERY_API_URL=http://localhost:8090
CLIENT_ID=brd-generator-client
BRD_GENERATOR_URL=http://localhost:8001
ENABLE_POLICY=false
```

### Policy Configuration

Edit `data/policy_types.json`:

```json
{
  "agent_policy": true,
  "resource_policy": true,
  "task_policy": true,
  "required_resources": [
    "azure_openai",
    "redis_cache",
    "azure_search"
  ],
  "allowed_task_types": [
    "brd_generation",
    "brd_validation",
    "brd_caching"
  ]
}
```

## 📊 Monitoring

### Token Tracking

Token usage is automatically tracked in BRDAgentStatus:

```python
status = await memory_manager.pull_brd_status(task_id)
print(f"Input tokens: {status.input_tokens}")
print(f"Output tokens: {status.output_tokens}")
print(f"Total cost: ${status.total_tokens * 0.00002}")  # Example pricing
```

### Cache Performance

Monitor cache hit rates:

```python
if result['from_cache']:
    print(f"Cache hit! Similarity: {result['similarity_score']:.3f}")
else:
    print("Generated fresh BRD")
```

## 🔧 Development

### Running Tests

```bash
# Unit tests
pytest tests/agents/brd_generator/

# Integration test
python -m src.agents.brd_generator.agent_executor --mode test
```

### Adding Custom Prompts

Create prompt templates in `prompts/`:

```
prompts/
├── brd_generation.prompt      # Main BRD generation
├── brd_validation.prompt      # BRD validation
└── brd_refinement.prompt      # Iterative refinement
```

Load in agent:

```python
prompt_path = os.path.join(os.path.dirname(__file__), "prompts/brd_generation.prompt")
with open(prompt_path) as f:
    custom_prompt = f.read()

agent = BRDGeneratorAgent(..., custom_prompt=custom_prompt)
```

## 🐛 Troubleshooting

### Redis Connection Error

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution**: Ensure Redis is running:
```bash
# Windows (with WSL)
wsl redis-server

# Docker
docker run -p 6379:6379 redis:7-alpine
```

### Azure Search Not Configured

```
WARNING: Azure Search/OpenAI not configured - skipping cache check
```

**Solution**: This is normal if caching is disabled. To enable:
```bash
export ENABLE_CACHING=true
export AZURE_SEARCH_ENDPOINT=https://xxx.search.windows.net
export AZURE_SEARCH_KEY=your_key
```

### Policy Validation Failed

```
ERROR: Policy validation failed: agent=False, resource=True, task=True
```

**Solution**: Check Discovery Service is running or disable policy:
```bash
export ENABLE_POLICY=false
```

## 🔗 Integration

### With Supervisor Agent

The Supervisor can delegate BRD generation:

```python
# Supervisor sends task
request = SendTaskRequest(
    id="brd-task-001",
    params=SendTaskParams(
        message=Message(parts=[TextPart(text="Create a CRM BRD")])
    )
)

response = await brd_agent.task_manager.on_send_task(request)
```

### With Streamlit UI

The existing Streamlit UI can be updated to use the new agent:

```python
# In src/ui/app.py
from src.agents.brd_generator import BRDGeneratorAgent

agent = BRDGeneratorAgent(
    session_id=st.session_state.session_id,
    ...
)

result = await agent.generate_brd(user_prompt)
st.json(result['brd_json'])
st.markdown(result['brd_markdown'])
```

## 📝 Next Steps

1. **Copy `mylibs/agent_base`** to project root
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Configure `.env`**: Copy from `.env.example`
4. **Start Redis**: `docker run -p 6379:6379 redis:7-alpine`
5. **Run test**: `python -m src.agents.brd_generator.agent_executor --mode test`
6. **Convert other agents** (Story, Code, Test generators)

## 📄 License

Part of BRD-to-Code pipeline. See main project LICENSE.
