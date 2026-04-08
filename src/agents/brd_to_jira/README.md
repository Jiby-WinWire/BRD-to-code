# BRD to JIRA Agent

Enterprise-grade agent for converting Business Requirements Documents to JIRA tickets.
Follows the same A2A architecture as the BRD Generator agent.

## 🏗️ Architecture

The BRD to JIRA Agent follows the **Agent Base Pattern** with:

```
┌─────────────────────────────────────────────────────────────┐
│              BRD to JIRA Agent                               │
│           (extends AgentClass)                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Memory     │  │    JIRA      │  │    Task      │      │
│  │   Manager    │  │  Config      │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│        │                  │                  │               │
│        ▼                  ▼                  ▼               │
│  ┌──────────────────────────────────────────────────┐      │
│  │         BRD to JIRA Conversion Tool              │      │
│  │         (ToolClass wrapper)                       │      │
│  └──────────────────────────────────────────────────┘      │
│                        │                                     │
│                        ▼                                     │
│              Azure OpenAI (GPT-4)                           │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    ┌────────┐      ┌──────────────┐   ┌──────────────┐
    │ Redis  │      │    JIRA      │   │   Azure      │
    │ Cache  │      │   Server     │   │  OpenAI      │
    └────────┘      └──────────────┘   └──────────────┘
```

## 🎯 Features

### 1. **Intelligent BRD to JIRA Conversion**
- Converts comprehensive BRDs to well-structured JIRA tickets
- Automatic issue type mapping:
  - Business Goals → Epics
  - Functional Requirements → Stories
  - Non-Functional Requirements → Tasks
- Includes acceptance criteria, story points, and priorities
- Maintains semantic relationships between tickets

### 2. **Flexible Configuration**
- Configurable JIRA project key
- Custom story point estimation (Fibonacci scale)
- Customizable priority levels
- Optional acceptance criteria generation
- Support for custom labels and tags

### 3. **State Management**
- Redis-based task tracking
- JiraAgentStatus Pydantic model
- Token usage monitoring
- Session management
- 24-hour TTL for tasks

### 4. **Result Caching**
- Redis-based conversion result caching
- Avoid re-converting similar requirements
- Fast retrieval for repeated requests
- Configurable TTL and caching strategy

### 5. **A2A Protocol Support**
- SendTaskRequest/SendTaskResponse handling
- Task lifecycle management
- Compatible with Supervisor/Planner agents
- RESTful A2A server mode

## 📦 Components

### Files

```
brd_to_jira/
├── __init__.py                 # Package exports
├── agent_executor.py           # Entry point & CLI
├── brd_to_jira_agent.py        # Main agent class
├── brd_to_jira_tool.py         # Tool wrapper
├── jira_memory_manager.py      # Redis state management
└── README.md                   # This file
```

### Key Classes

#### **BRDToJiraAgent**
Main agent class extending AgentClass.

```python
agent = BRDToJiraAgent(
    session_id="user-123",
    redis_url="redis://localhost:6379",
    azure_openai_endpoint="https://xxx.openai.azure.com/",
    azure_openai_key="key",
    azure_openai_deployment="gpt4o",
    jira_server_url="http://jira.example.com",
    jira_project_key="PROJ",
    enable_caching=True
)

result = await agent.convert_brd_to_jira(
    brd_json={...},
    task_id="task-001"
)
```

#### **JiraMemoryManager**
Manages state persistence and conversion caching.

```python
memory_manager = JiraMemoryManager(
    redis_client=redis_client,
    enable_caching=True,
    ttl_seconds=86400  # 24 hours
)

# Cache conversion result
await memory_manager.cache_conversion(
    cache_key="brd_to_jira:task-001",
    conversion_data={...}
)

# Save status
await memory_manager.push_jira_status(task_id, status)
```

#### **JiraTaskManager**
Handles A2A protocol requests.

```python
task_manager = JiraTaskManager(agent)

# Auto-invoked by A2A server
response = await task_manager.on_send_task(request)
```

## 🔗 Integration with BRD Generator

The BRD to JIRA agent is designed to work seamlessly with the BRD Generator:

```
User Request
    ↓
BRD Generator Agent → Generates BRD (JSON)
    ↓
BRD to JIRA Agent → Converts to JIRA Tickets
    ↓
JIRA Server → Creates Tickets
```

## 🚀 Quick Start

### 1. Initialize Agent

```python
from src.agents.brd_to_jira.agent_executor import create_brd_to_jira_agent

agent = create_brd_to_jira_agent(
    session_id="user-123",
    agent_url="http://localhost:8002"
)
```

### 2. Convert BRD to JIRA

```python
brd = {
    "title": "Customer Portal",
    "functional_requirements": [
        "User authentication",
        "Dashboard with analytics",
        "Export reports to PDF"
    ],
    "business_goals": [
        "Improve user engagement",
        "Reduce support tickets"
    ]
}

result = await agent.convert_brd_to_jira(brd_json=brd)
```

### 3. Access Generated Tickets

```python
for ticket in result.get("jira_tickets", []):
    print(f"{ticket['key']}: {ticket['summary']}")
    print(f"Type: {ticket['issue_type']}, Points: {ticket['story_points']}")
```

## 🔧 Configuration

### Environment Variables

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt4o

# Redis
REDIS_URL=redis://localhost:6379
USE_FAKE_REDIS=auto  # auto, true, false

# JIRA
JIRA_SERVER_URL=http://jira.example.com
JIRA_USERNAME=your-username
JIRA_API_TOKEN=your-token
JIRA_PROJECT_KEY=PROJ

# Agent
AGENT_URL=http://localhost:8002
ENABLE_CACHING=true
```

## 📊 Output Format

The agent generates JIRA tickets with the following structure:

```json
{
  "jira_tickets": [
    {
      "key": "PROJ-1",
      "summary": "Implement user authentication",
      "description": "Enable SSO and multi-factor authentication...",
      "issue_type": "Story",
      "story_points": 8,
      "priority": "High",
      "acceptance_criteria": [
        "Users can login with SSO",
        "MFA is enabled",
        "Session timeout is 30 minutes"
      ],
      "labels": ["authentication", "security"]
    }
  ],
  "metadata": {
    "source_brd_title": "Customer Portal",
    "num_tickets": 5,
    "project_key": "PROJ"
  }
}
```

## 🔄 Caching Strategy

Conversions are cached with:
- **Key**: `brd_to_jira:{task_id}`
- **TTL**: 24 hours (configurable)
- **Retrieval**: Automatic on subsequent requests

Disable caching:
```python
agent = BRDToJiraAgent(..., enable_caching=False)
```

## 🤝 A2A Protocol Integration

The agent implements the A2A SendTask protocol:

```python
# Incoming request
{
  "id": "req-123",
  "method": "tasks/send",
  "params": {
    "message": {
      "parts": [
        {"text": "{\"title\": \"...\", \"requirements\": [...]}"}
      ]
    }
  }
}

# Response
{
  "id": "req-123",
  "result": {
    "id": "task-456",
    "status": "COMPLETED",
    "message": {
      "parts": [
        {"text": "Generated 5 JIRA tickets..."}
      ]
    }
  }
}
```

## 📝 Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Running Agent

```bash
python src/agents/brd_to_jira/agent_executor.py
```

### Integration with Orchestrator

```python
from src.agents.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator(
    brd_generator_config={...},
    brd_to_jira_config={...},
    jira_to_code_config={...}
)

result = await orchestrator.run_pipeline(user_requirement)
```

## 📄 License

Same as BRD-to-Code project
