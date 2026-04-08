# Validation Agent

Enterprise-grade agent for validating Business Requirements Documents (BRDs) and requirements specifications.

## 🏗️ Architecture

The Validation Agent follows the **Agent Base Pattern** with:

```
┌─────────────────────────────────────────────────────────────┐
│                    Validation Agent                          │
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
│  │              Validation Tool                      │      │
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

### 1. **LLM-Powered Document Validation**
- Validates BRDs and requirements specifications
- Comprehensive quality assessment
- Detailed issue identification and categorization
- Actionable improvement suggestions
- Structured JSON and readable output

### 2. **Multi-Dimensional Analysis**
- **Completeness**: All required sections present
- **Consistency**: No contradictions or conflicts
- **Clarity**: Language clarity and precision
- **Measurability**: SMART requirements verification
- **Traceability**: Business goal alignment
- **Feasibility**: Technical achievability assessment

### 3. **Semantic Caching**
- Azure Search vector similarity search
- Reuses similar validation results (configurable threshold: 0.85)
- Reduces LLM calls and costs
- Azure OpenAI embeddings for semantic matching

### 4. **State Management**
- Redis-based task tracking
- ValidationAgentStatus Pydantic model
- Token usage monitoring
- Session management
- 24-hour TTL for tasks

### 5. **Policy-Based Access Control**
- Discovery Service integration
- Three-tier validation:
  - **Agent Policy**: Can this agent run?
  - **Resource Policy**: Can access Azure OpenAI/Redis?
  - **Task Policy**: Can validate documents?
- Parallel policy checks for performance

### 6. **A2A Protocol Support**
- SendTaskRequest/SendTaskResponse
- Task lifecycle management
- Compatible with Supervisor/Planner agents
- RESTful A2A server mode

## 📦 Components

### Files

```
validation/
├── __init__.py                    # Package exports
├── agent_executor.py              # Entry point & CLI
├── validation_agent.py            # Main agent class
├── validation_tool.py             # Tool wrapper
├── memory_manager.py              # Redis & Azure Search
├── policy_manager.py              # Discovery Service client
├── data/
│   └── validation_types.json      # Policy configuration
├── prompts/
│   └── validation.prompt          # Validation guidelines
└── README.md                      # This file
```

### Key Classes

#### **ValidationAgent**
Main agent class extending AgentClass.

```python
agent = ValidationAgent(
    session_id="user-123",
    redis_url="redis://localhost:6379",
    azure_openai_endpoint="https://xxx.openai.azure.com/",
    azure_openai_key="key",
    azure_openai_deployment="gpt4o",
    enable_caching=True,
    enable_policy=False
)

result = await agent.validate_document(
    document_content="BRD or requirements text...",
    task_id="task-001"
)
```

#### **ValidationMemoryManager**
Manages state persistence and caching.

```python
memory_manager = ValidationMemoryManager(
    redis_client=redis_client,
    azure_search_endpoint="https://xxx.search.windows.net",
    azure_search_key="key",
    azure_openai_endpoint="https://xxx.openai.azure.com/"
)

# Cache check
cached = await memory_manager.search_cached_validation(
    document_content="...",
    similarity_threshold=0.85
)

# Save status
await memory_manager.push_validation_status(task_id, status)
```

#### **PolicyManager**
Validates execution against policies.

```python
policy_manager = PolicyManager(
    discovery_app_url="http://discovery:8090",
    client_id="validation-client",
    agent_url="http://localhost:8002"
)

result = policy_manager.validate_all_policies(
    session_id="user-123",
    task_data={...},
    resources=["azure_openai", "redis"],
    task_type="validation"
)

if result.all_passed:
    # Execute task
    pass
```

#### **ValidationAgentStatus**
Pydantic model for state tracking.

```python
status = ValidationAgentStatus(
    status="completed",
    document_title="CRM System BRD",
    is_valid=True,
    validation_score=87.5,
    issue_count=3,
    critical_issues=0,
    validation_result={...},
    task_id="task-001"
)
```

## 🚀 Usage

### Standalone Mode

Run a single document validation test:

```bash
python -m src.agents.validation.agent_executor --mode test
```

Output saved to `output/validation_test/`:
- `test_validation.json` - Structured validation results

### A2A Server Mode

Start as HTTP server for agent-to-agent communication:

```bash
python -m src.agents.validation.agent_executor --mode server --port 8002
```

The agent will:
- Start listening on `http://localhost:8002`
- Accept A2A requests (`SendTaskRequest`)
- Process document validation
- Return detailed results (`SendTaskResponse`)

## 🔧 Configuration

### Environment Variables

Required:
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI service endpoint
- `AZURE_OPENAI_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_DEPLOYMENT` - Model deployment name

Optional:
- `REDIS_URL` - Redis connection (default: `redis://localhost:6379`)
- `USE_FAKE_REDIS` - Use in-memory Redis (default: `auto`)
- `AZURE_SEARCH_ENDPOINT` - Azure Search endpoint (for caching)
- `AZURE_SEARCH_KEY` - Azure Search API key
- `AZURE_SEARCH_INDEX` - Search index name (default: `validation-cache-index`)
- `DISCOVERY_API_URL` - Discovery Service URL (for policies)
- `ENABLE_POLICY` - Enable policy validation (default: `false`)
- `ENABLE_CACHING` - Enable semantic caching (default: `true`)
- `VALIDATION_AGENT_URL` - This agent's URL (default: `http://localhost:8002`)

### Sample .env File

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt4o_mktgenai

# Redis
REDIS_URL=redis://localhost:6379
USE_FAKE_REDIS=auto

# Azure Search (optional for caching)
AZURE_SEARCH_ENDPOINT=https://your-search-instance.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX=validation-cache-index

# Discovery Service (optional for policies)
DISCOVERY_API_URL=http://discovery:8090
ENABLE_POLICY=false

# Caching
ENABLE_CACHING=true

# Agent
VALIDATION_AGENT_URL=http://localhost:8002
```

## 📋 Validation Criteria

### Document Completeness
✓ All required sections present  
✓ No critical omissions  
✓ Proper document structure  

### Consistency
✓ No contradictions between sections  
✓ Consistent terminology usage  
✓ Related items properly aligned  

### Clarity
✓ Language is clear and unambiguous  
✓ Technical jargon is defined  
✓ Ideas are expressed concisely  

### Measurability
✓ Requirements are SMART  
✓ Success criteria are quantifiable  
✓ Needs are objectively verifiable  

### Traceability
✓ Requirements link to business goals  
✓ Dependencies are clear  
✓ Impact analysis is possible  

### Feasibility
✓ Requirements are technically achievable  
✓ Constraints are realistic  
✓ Resources appear adequate  

## 💡 Example Output

### Validation Result
```json
{
  "document_title": "Customer Relationship Management System",
  "is_valid": true,
  "validation_score": 87.5,
  "issues": [
    {
      "severity": "warning",
      "category": "completeness",
      "description": "Missing integration requirements for SMS notifications",
      "location": "Functional Requirements section",
      "suggestion": "Add specific requirements for SMS gateway integration"
    }
  ],
  "summary": "Overall, this is a well-structured BRD with good coverage of functional and non-functional requirements. Some sections could benefit from additional detail around integrations."
}
```

### Issue Categorization
- **Critical** (Severity 0): Blocks project progress
- **Warning** (Severity 1): Should be addressed
- **Info** (Severity 2): Nice-to-have improvements

## 🔗 Integration with Other Agents

The Validation Agent integrates with:

### BRD Generator Agent
- Validates generated BRDs
- Provides feedback for iteration
- Ensures quality before handoff

### Code Generation Agents
- Validates requirements before code generation
- Identifies missing specifications
- Improves code generation quality

### Supervisor/Planner Agents
- Validates documents in orchestrated workflows
- Returns structured feedback
- Supports multi-agent orchestration

## 📊 Performance Metrics

- **Average Validation Time**: 5-15 seconds per document
- **Cache Hit Rate**: 10-30% (depends on document similarity)
- **Validation Score**: 0-100 (based on quality dimensions)
- **Throughput**: 100+ documents/hour on standard LLM

## 🛠️ Development

### Running Tests
```bash
python -m src.agents.validation.agent_executor --mode test
```

### Debugging
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Adding Custom Validation Rules
Extend `ValidationAgent` class and override validation logic in `validation_tool.py`.

## 📚 References

- [Agent Base Framework](../../../mylibs/agent_base/)
- [A2A Protocol](https://github.com/a2a-spec/)
- [Azure OpenAI](https://learn.microsoft.com/azure/cognitive-services/openai/)
- [Redis Documentation](https://redis.io/docs/)
