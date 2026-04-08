# BRD Generator vs BRD to JIRA - Architecture Pattern Comparison

## 🏗️ Same Architecture Pattern

Both agents follow the identical enterprise A2A pattern:

```
Agent Structure Pattern
├── Agent Class (extends AgentClass)
├── Task Manager (extends InMemoryTaskManager)
├── Memory Manager (custom persistence)
├── Tool (LangChain tool wrapper)
└── Agent Executor (entry point & configuration)
```

## 📋 Component Mapping

| Component | BRD Generator | BRD to JIRA |
|-----------|---------------|------------|
| **Main Agent** | `BRDGeneratorAgent` | `BRDToJiraAgent` |
| **Task Manager** | `BRDTaskManager` | `JiraTaskManager` |
| **Memory Manager** | `BRDMemoryManager` | `JiraMemoryManager` |
| **Status Model** | `BRDAgentStatus` | `JiraAgentStatus` |
| **Tool Factory** | `create_brd_generation_tool()` | `create_brd_to_jira_tool()` |
| **Executor** | `create_brd_agent()` | `create_brd_to_jira_agent()` |

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────┐
│  BRD Generator Workflow                             │
├─────────────────────────────────────────────────────┤
│ Input: User requirement (text)                      │
│ ↓                                                    │
│ BRDGeneratorAgent.generate_brd()                    │
│ ↓                                                    │
│ LLM: Generate comprehensive BRD                     │
│ ↓                                                    │
│ Output: BRD (JSON) + Markdown                       │
│ ↓ (via A2A SendTaskResponse)                        │
│ Cache in Redis                                      │
└─────────────────────────────────────────────────────┘

        ↓ (Next pipeline step)

┌─────────────────────────────────────────────────────┐
│  BRD to JIRA Workflow                               │
├─────────────────────────────────────────────────────┤
│ Input: BRD (JSON) from BRD Generator                │
│ ↓                                                    │
│ BRDToJiraAgent.convert_brd_to_jira()                │
│ ↓                                                    │
│ LLM: Parse BRD & generate JIRA tickets              │
│ ↓                                                    │
│ Output: JIRA tickets with story points              │
│ ↓ (via A2A SendTaskResponse)                        │
│ Cache in Redis                                      │
└─────────────────────────────────────────────────────┘
```

## 📦 File Structure Comparison

### BRD Generator
```
src/agents/brd_generator/
├── __init__.py
├── agent_executor.py
├── brd_generator_agent.py (Main agent)
├── brd_generator_tool.py  (Tool implementation)
├── memory_manager.py      (BRDMemoryManager)
├── policy_manager.py      (PolicyManager - optional)
├── README.md
└── data/
    ├── policy_types.json
└── prompts/
    └── brd_generation.prompt
```

### BRD to JIRA (Following Same Pattern)
```
src/agents/brd_to_jira/
├── __init__.py
├── agent_executor.py
├── brd_to_jira_agent.py   (Main agent)
├── brd_to_jira_tool.py    (Tool implementation)
├── jira_memory_manager.py (Memory manager)
├── README.md
└── (Optional for v2: policy_manager.py)
```

## 🔑 Key Similarities

### 1. **Agent Initialization**
```python
# BRD Generator Pattern
agent = BRDGeneratorAgent(
    session_id=session_id,
    redis_url=redis_url,
    azure_openai_endpoint=endpoint,
    azure_openai_key=key,
    azure_openai_deployment=deployment,
    enable_caching=True
)

# BRD to JIRA Pattern (Same structure)
agent = BRDToJiraAgent(
    session_id=session_id,
    redis_url=redis_url,
    azure_openai_endpoint=endpoint,
    azure_openai_key=key,
    azure_openai_deployment=deployment,
    enable_caching=True
)
```

### 2. **Task Manager Protocol**
```python
# Both implement: async def on_send_task(request: SendTaskRequest) -> SendTaskResponse
# - Extract input from request.params.message
# - Initialize status with agent's memory_manager
# - Call main conversion method
# - Update status on completion/failure
# - Return SendTaskResponse with Task result
```

### 3. **Memory Manager Pattern**
```python
# Both implement:
- push_{item}_status()      # Save to Redis
- pull_{item}_status()      # Retrieve from Redis
- cache_{operation}()       # Cache results
- get_cached_{operation}()  # Retrieve cached results
- clear_task_data()         # Clean up
- get_session_tasks()       # Query by session
```

### 4. **Tool Creation**
```python
# Both use LangChain tool decorator
@tool
async def {operation}(input_schema) -> Dict[str, Any]:
    # Process input
    # Check cache
    # Call LLM if needed
    # Cache result
    # Return structured output
```

### 5. **Environment Configuration**
```bash
# Common variables
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_DEPLOYMENT=...
REDIS_URL=...
USE_FAKE_REDIS=auto
AGENT_URL=...
ENABLE_CACHING=true

# Specific variables
BRD Generator: AZURE_SEARCH_ENDPOINT (for semantic caching)
BRD to JIRA: JIRA_SERVER_URL, JIRA_PROJECT_KEY (for conversion config)
```

## 🚀 Usage Pattern Consistency

### Creation & Initialization
```python
# BRD Generator
from src.agents.brd_generator.agent_executor import create_brd_agent
agent = create_brd_agent(session_id="user-123")

# BRD to JIRA (Same pattern)
from src.agents.brd_to_jira.agent_executor import create_brd_to_jira_agent
agent = create_brd_to_jira_agent(session_id="user-123")
```

### A2A Integration
```python
# Both support identical task manager pattern
# Integrate with Orchestrator via task_manager
orchestrator.register_agent_task_manager(
    agent_name="brd-generator",
    task_manager=brd_gen_agent.task_manager
)
orchestrator.register_agent_task_manager(
    agent_name="brd-to-jira",
    task_manager=brd_to_jira_agent.task_manager
)
```

## 📊 Status Models Comparison

### BRDAgentStatus Fields
- status, user_prompt, brd_json, brd_markdown
- input_tokens, output_tokens, total_tokens
- task_id, session_id, start_time, end_time

### JiraAgentStatus Fields (Similar)
- status, brd_json (input), jira_tickets (output), conversion_metadata
- input_tokens, output_tokens, total_tokens
- task_id, session_id, start_time, end_time, duration_seconds
- error_message (for tracking failures)

## ✅ Differences (By Design)

| Aspect | BRD Generator | BRD to JIRA |
|--------|---------------|------------|
| **Tool Purpose** | Generate BRD | Convert BRD to JIRA |
| **Output Format** | BRD (JSON + Markdown) | JIRA Tickets (Structured) |
| **Caching Strategy** | Azure Search (semantic) | Redis (simple) |
| **Policy Manager** | Optional + Discovery Service | Not implemented (v1) |
| **Extra Config** | Search indices | JIRA project settings |

## 🔗 Pipeline Integration

```
User Story
    ↓
┌─────────────────────────────────┐
│ Orchestrator (Supervisor Agent) │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ BRD Generator Agent             │ ← A2A Protocol
│ (TaskManager: BRDTaskManager)   │
└─────────────────────────────────┘
    ↓ (BRD JSON)
┌─────────────────────────────────┐
│ BRD to JIRA Agent               │ ← A2A Protocol
│ (TaskManager: JiraTaskManager)  │
└─────────────────────────────────┘
    ↓ (JIRA Tickets)
┌─────────────────────────────────┐
│ JIRA Server                     │ (Future: API calls)
└─────────────────────────────────┘
```

## 🎯 Key Takeaways

1. **Same Foundation**: Both use `AgentClass` as base
2. **Same Protocol**: Both use A2A `SendTask`/`SendTaskResponse`
3. **Same Patterns**: Task manager, memory manager, tool factory
4. **Same Lifecycle**: Initialize → Configure → Register → Receive Tasks
5. **Easy to Extend**: New agents can follow identical pattern
6. **Enterprise Ready**: Logging, error handling, caching built-in

## 🔮 Future Enhancements (Same Approach)

- Add **Policy Manager** to BRD to JIRA (like BRD Generator)
- Add **Azure Search** semantic caching option
- Add **Batch Processing** support
- Add **Webhook** callbacks
- All following the established pattern
