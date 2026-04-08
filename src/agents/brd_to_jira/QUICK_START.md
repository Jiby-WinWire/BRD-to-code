# BRD to JIRA Agent - Quick Reference Guide

## 🚀 Quick Start (5 minutes)

### Installation & Setup
```bash
# 1. Install dependencies (already in requirements.txt)
pip install -r requirements.txt

# 2. Set environment variables
export AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
export AZURE_OPENAI_KEY=your-key
export AZURE_OPENAI_DEPLOYMENT=gpt4o
export REDIS_URL=redis://localhost:6379
export JIRA_PROJECT_KEY=PROJ
```

### Basic Usage
```python
from src.agents.brd_to_jira import create_brd_to_jira_agent
import asyncio

async def main():
    # Create agent
    agent = create_brd_to_jira_agent(session_id="user-123")
    
    # BRD from BRD Generator
    brd = {
        "title": "E-Commerce Platform",
        "functional_requirements": [
            "User authentication",
            "Product catalog",
            "Shopping cart",
            "Payment processing"
        ]
    }
    
    # Convert to JIRA
    result = await agent.convert_brd_to_jira(brd_json=brd)
    
    # Print tickets
    for ticket in result["jira_tickets"]:
        print(f"✅ {ticket['key']}: {ticket['summary']}")
        print(f"   Type: {ticket['issue_type']}, Points: {ticket['story_points']}\n")

asyncio.run(main())
```

## 📚 Common Tasks

### Task 1: Create Agent with Custom JIRA Config
```python
from src.agents.brd_to_jira import BRDToJiraAgent

agent = BRDToJiraAgent(
    session_id="user-456",
    redis_url="redis://localhost:6379",
    azure_openai_endpoint="https://xxx.openai.azure.com/",
    azure_openai_key="key",
    azure_openai_deployment="gpt4o",
    jira_server_url="http://jira.mycompany.com",
    jira_project_key="CRM",  # Custom project
    enable_caching=True
)
```

### Task 2: Convert BRD and Handle Errors
```python
async def safe_convert(agent, brd):
    try:
        result = await agent.convert_brd_to_jira(
            brd_json=brd,
            task_id="task-001"
        )
        return result
    except ValueError as e:
        print(f"❌ Validation error: {e}")
        return None
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return None
```

### Task 3: Access Task Status from Redis
```python
async def check_task_status(agent, task_id):
    status = await agent.memory_manager.pull_jira_status(task_id)
    if status:
        print(f"Status: {status.status}")
        print(f"Tickets: {len(status.jira_tickets or [])}")
        if status.error_message:
            print(f"Error: {status.error_message}")
    else:
        print(f"Task {task_id} not found")
```

### Task 4: Cache Conversion Result
```python
async def cache_result(agent, task_id, result):
    cache_key = f"brd_to_jira:{task_id}"
    await agent.memory_manager.cache_conversion(
        cache_key=cache_key,
        conversion_data={
            "jira_tickets": [t.dict() for t in result["jira_tickets"]],
            "metadata": result["metadata"]
        }
    )
    print(f"✅ Result cached for {task_id}")
```

### Task 5: Query All Tasks for a Session
```python
async def get_session_history(agent, session_id):
    task_ids = await agent.memory_manager.get_session_tasks(session_id)
    print(f"Found {len(task_ids)} tasks for session {session_id}")
    
    for task_id in task_ids:
        status = await agent.memory_manager.pull_jira_status(task_id)
        if status:
            print(f"- {task_id}: {status.status}")
```

## 🔧 Configuration Reference

### Environment Variables

**Required:**
```bash
AZURE_OPENAI_ENDPOINT    # Azure OpenAI endpoint URL
AZURE_OPENAI_KEY         # Azure OpenAI API key
AZURE_OPENAI_DEPLOYMENT  # Model deployment name (e.g., gpt4o)
REDIS_URL                # Redis connection URL
```

**Optional:**
```bash
USE_FAKE_REDIS=auto      # auto|true|false (auto = try real Redis, fallback to FakeRedis)
JIRA_SERVER_URL=http://localhost:8080
JIRA_USERNAME            # Only if auth required
JIRA_API_TOKEN           # Only if auth required
JIRA_PROJECT_KEY=PROJ    # Default project key
AGENT_URL=http://localhost:8002
ENABLE_CACHING=true      # Enable/disable result caching
AZURE_OPENAI_API_VERSION=2023-05-15
```

### Programmatic Configuration
```python
# Via constructor
agent = BRDToJiraAgent(
    session_id="user-123",
    redis_url="redis://localhost",
    azure_openai_endpoint="...",
    azure_openai_key="...",
    azure_openai_deployment="gpt4o",
    jira_server_url="http://jira.example.com",
    jira_username="admin",
    jira_api_token="token",
    jira_project_key="PROJ",
    enable_caching=True
)

# Or via factory function (uses env vars)
from src.agents.brd_to_jira import create_brd_to_jira_agent
agent = create_brd_to_jira_agent()
```

## 📊 Output Formats

### JIRA Ticket Structure
```json
{
  "key": "PROJ-1",
  "summary": "Implement user authentication",
  "description": "Enable users to login with SSO and MFA...",
  "issue_type": "Story",
  "story_points": 8,
  "priority": "High",
  "acceptance_criteria": [
    "Users can login with SSO",
    "MFA is enabled",
    "Session timeout works"
  ],
  "labels": ["auth", "security"]
}
```

### Conversion Result
```json
{
  "jira_tickets": [...],
  "metadata": {
    "source_brd_title": "E-Commerce Platform",
    "num_tickets": 5,
    "project_key": "PROJ"
  },
  "from_cache": false
}
```

### Task Status
```json
{
  "status": "completed",
  "task_id": "task-001",
  "session_id": "user-123",
  "jira_tickets": [...],
  "conversion_metadata": {...},
  "start_time": "2024-01-15T10:00:00.000Z",
  "end_time": "2024-01-15T10:00:30.000Z",
  "duration_seconds": 30.5,
  "error_message": null
}
```

## 🔗 Integration Examples

### With BRD Generator
```python
from src.agents.brd_generator import create_brd_agent
from src.agents.brd_to_jira import create_brd_to_jira_agent

async def full_pipeline(user_requirement):
    # Step 1: Generate BRD
    brd_agent = create_brd_agent(session_id="pipeline-1")
    brd_result = await brd_agent.generate_brd(
        user_prompt=user_requirement
    )
    
    # Step 2: Convert to JIRA
    jira_agent = create_brd_to_jira_agent(session_id="pipeline-1")
    jira_result = await jira_agent.convert_brd_to_jira(
        brd_json=brd_result["brd_json"]
    )
    
    return jira_result["jira_tickets"]
```

### With A2A Orchestrator
```python
# The agent automatically integrates via task manager
agent = create_brd_to_jira_agent()

# Register with orchestrator
from src.agents.orchestrator import AgentOrchestrator
orchestrator = AgentOrchestrator()
orchestrator.register_agent(
    name="brd-to-jira",
    agent=agent,
    task_manager=agent.task_manager  # Already initialized
)

# Orchestrator will call agent.task_manager.on_send_task()
```

## 🐛 Debugging Tips

### Enable Detailed Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("src.agents.brd_to_jira")
```

### Check Agent Status
```python
async def debug_agent(agent):
    print(f"Session: {agent.session_id}")
    print(f"LLM: {agent.llm}")
    print(f"Redis: {agent.redis_client}")
    print(f"Memory Manager: {agent.memory_manager}")
    print(f"Task Manager: {agent.task_manager}")
```

### Verify Redis Connection
```python
from redis import StrictRedis
import fakeredis

# Real Redis
try:
    redis = StrictRedis.from_url("redis://localhost:6379")
    redis.ping()
    print("✅ Real Redis connected")
except:
    print("❌ Real Redis failed")
    redis = fakeredis.FakeStrictRedis()
    print("✅ Using FakeRedis")
```

### Test LLM
```python
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    azure_endpoint="https://xxx.openai.azure.com/",
    api_key="key",
    azure_deployment="gpt4o"
)

response = llm.predict("Say hello")
print(response)
```

## 📈 Performance Tips

### 1. Enable Caching
```python
# Avoid re-converting similar BRDs
agent = BRDToJiraAgent(..., enable_caching=True)
```

### 2. Use FakeRedis for Development
```bash
export USE_FAKE_REDIS=true
```

### 3. Batch Processing (Future)
```python
# Process multiple BRDs efficiently
for brd in brd_list:
    await agent.convert_brd_to_jira(brd_json=brd)
```

### 4. Monitor Token Usage
```python
status = await agent.memory_manager.pull_jira_status(task_id)
print(f"Tokens used: {status.total_tokens}")
```

## 🚨 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Redis connection refused | Set `USE_FAKE_REDIS=true` or ensure Redis is running |
| Azure OpenAI 401 error | Check `AZURE_OPENAI_KEY` and `AZURE_OPENAI_ENDPOINT` |
| LLM response parsing error | Check BRD format - ensure it's valid JSON |
| Memory error on large BRDs | Process in smaller batches |
| Slow conversion | Enable caching to avoid re-processing |

## 📞 Support Resources

- **README.md**: Feature overview and architecture
- **ARCHITECTURE_COMPARISON.md**: Pattern explanation
- **brd_generator/README.md**: Reference implementation
- **Code comments**: Detailed implementation notes
- **Error messages**: Structured error reporting

## ✅ Next Steps

1. ✅ Try basic example above
2. ✅ Test with your own BRD JSON
3. ✅ Enable caching for production use
4. ✅ Integrate with BRD Generator
5. ✅ Deploy to A2A orchestrator

---

**Happy converting! 🎉**
