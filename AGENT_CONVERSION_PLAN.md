# Agent Conversion Plan: BRD-to-Code Pipeline

## 📋 Overview
Convert existing BRD-to-Code agents to follow the enterprise agent pattern with A2A SDK, memory management, and policy controls.

## 🏗️ Standard Agent Architecture

### **Core Components**
1. **Agent Base** (`agent_base.AgentClass`)
   - LangGraph create_react_agent
   - Azure OpenAI LLM
   - Tool integration
   - A2A Server (optional)

2. **Memory Manager**
   - Redis for state/session management
   - Azure Search for semantic caching
   - Azure OpenAI for embeddings
   - Status tracking with Pydantic models

3. **Policy Manager**
   - Agent policy (can agent run?)
   - Resource policy (can use resources?)
   - Task policy (can perform task?)
   - Discovery Service integration

4. **Task Manager**
   - A2A protocol handler
   - SendTaskRequest → SendTaskResponse
   - Task state management

5. **Tools**
   - ToolClass wrapper
   - Async support
   - Schema validation

## 🎯 Conversion Sequence

### **Phase 1: BRD Generator Agent** ✅ START HERE
**Current**: `src/agents/brd_generator.py` (simple function)
**Target**: Full agent with memory & policy

**Features**:
- Generate BRD from natural language
- Cache BRD templates in Redis
- Validate against policy
- Track token usage
- A2A communication ready

### **Phase 2: Story Generator Agent**
**Current**: `src/agents/brd_to_jira.py` (simple transformation)
**Target**: Agent that consumes BRD, generates stories

**Features**:
- Receive BRD from Planner/Supervisor
- Generate Jira stories
- Cache story templates
- Track story generation patterns

### **Phase 3: Code Generator Agent**
**Current**: `src/agents/story_to_code.py` (LLM-based generation)
**Target**: Agent that generates production code

**Features**:
- Receive stories from Story Generator
- Generate FastAPI code
- Cache code patterns
- Validate code quality

### **Phase 4: Test Generator Agent**
**Current**: `src/agents/test_generator.py` (test generation)
**Target**: Agent that generates comprehensive tests

**Features**:
- Receive code from Code Generator
- Generate pytest tests
- Validate test coverage
- Execute tests

### **Phase 5: Orchestrator Refactor**
**Current**: LangGraph StateGraph
**Target**: Supervisor Agent pattern

**Features**:
- Use A2A protocol to coordinate agents
- Task routing and delegation
- Aggregate results
- Error handling and recovery

## 📁 Folder Structure (New)

```
BRD-to-code/
├── src/
│   ├── agents/
│   │   ├── brd_generator/
│   │   │   ├── brd_generator_agent.py
│   │   │   ├── brd_generator_tool.py
│   │   │   ├── memory_manager.py
│   │   │   ├── policy_manager.py
│   │   │   ├── agent_executor.py
│   │   │   ├── data/
│   │   │   │   └── policy_types.json
│   │   │   └── prompts/
│   │   │       └── brd_generation.prompt
│   │   ├── story_generator/
│   │   │   └── ... (similar structure)
│   │   ├── code_generator/
│   │   │   └── ... (similar structure)
│   │   ├── test_generator/
│   │   │   └── ... (similar structure)
│   │   └── supervisor/
│   │       └── ... (orchestration)
│   ├── infrastructure/
│   │   ├── azure_clients.py
│   │   ├── secret_loader.py
│   │   └── redis_utils.py
│   └── shared/
│       ├── types.py
│       └── utils.py
├── mylibs/  # Copied from winmind
│   └── agent_base/
│       ├── agent.py
│       ├── tools.py
│       ├── memory.py
│       ├── types.py
│       └── a2a_server.py
├── requirements.txt
└── .env.example
```

## 🔑 Key Patterns

### **1. Agent Class Structure**
```python
class BRDGeneratorAgent(AgentClass):
    def __init__(self, session_id, redis_url, azure_openai_config, ...):
        # 1. Initialize infrastructure
        self.redis_client = self._get_redis_client(redis_url)
        
        # 2. Initialize memory manager
        self.memory_manager = BRDMemoryManager(
            redis_client=self.redis_client,
            azure_search_config=...,
            azure_openai_config=...
        )
        
        # 3. Initialize policy manager
        self.policy_manager = PolicyManager(
            discovery_app_url=...,
            client_id=...,
            agent_url=...,
            policy_types=["agent", "resource", "task"]
        )
        
        # 4. Call parent with tools
        super().__init__(
            agent_name="brd-generator",
            tools=[generate_brd_tool],
            config=llm_config,
            memory_backend=None
        )
        
        # 5. Custom task manager
        self.task_manager = BRDTaskManager(self)
```

### **2. Memory Manager Pattern**
```python
class BRDMemoryManager:
    def __init__(self, redis_client, azure_search_config, azure_openai_config):
        self.redis_client = redis_client
        self.azure_search_client = SearchClient(...)
        self.azure_openai_client = AzureOpenAI(...)
        
    async def store_brd_status(self, status: BRDStatus):
        """Store BRD generation status in Redis"""
        key = f"brd:task:{status.task_id}"
        self.redis_client.set(key, status.json())
        
    async def get_cached_brd(self, normalized_query: str):
        """Check if similar BRD exists in cache"""
        # Use Azure Search for semantic similarity
        results = await self.azure_search_client.search(...)
        return results
```

### **3. Tool Pattern**
```python
from agent_base.tools import ToolClass

async def generate_brd_function(user_prompt: str, llm) -> dict:
    """Generate Business Requirements Document from user prompt"""
    # Implementation
    return brd_json

generate_brd_tool = ToolClass(
    name="generate_brd",
    description="Generate structured BRD from natural language requirements",
    func=generate_brd_function,
    args_schema=BRDInputSchema
)
```

### **4. Task Manager Pattern**
```python
class BRDTaskManager(InMemoryTaskManager):
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        # 1. Extract user query
        user_query = request.params.message.parts[0].text
        
        # 2. Policy validation
        if self.agent.policy_manager:
            # Check policies
            pass
        
        # 3. Process with agent
        result = await self.agent.generate_brd(user_query, task_id)
        
        # 4. Store in memory
        await self.agent.memory_manager.store_brd_status(result)
        
        # 5. Return response
        return SendTaskResponse(id=request.id, result=task)
```

## 🚀 Implementation Steps

### **Step 1: Setup**
1. Copy `mylibs/agent_base/` to project
2. Update `requirements.txt` with dependencies
3. Create folder structure for agents

### **Step 2: BRD Generator Agent**
1. Create `brd_generator_agent.py`
2. Create `brd_generator_tool.py`
3. Create `memory_manager.py`
4. Create `policy_manager.py`
5. Create `agent_executor.py`

### **Step 3: Integration**
1. Update `.env` with all required configs
2. Test standalone agent
3. Integrate with UI
4. Test end-to-end

### **Step 4: Repeat for Other Agents**
Follow same pattern for Story, Code, and Test generators

## 📦 Dependencies to Add

```txt
# A2A SDK
a2a-sdk[http-server]>=0.3.11

# Redis
redis==6.2.0
redis-cluster

# Azure
azure-search-documents
azure-storage-blob
azure-identity

# LangChain
langchain-core
langchain-openai
langchain-community
langgraph

# Policy
casbin
casbin-redis-adapter

# NLP
spacy
rapidfuzz

# Other
pydantic>=2.0.0
httpx
```

## ⚙️ Configuration (.env additions)

```bash
# Redis
REDIS_URL=redis://localhost:6379

# Azure Search (for semantic caching)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-key
AZURE_SEARCH_INDEX=brd-cache-index

# Discovery Service (for policy management)
DISCOVERY_API_URL=http://localhost:8090
CLIENT_ID=brd-to-code-client
CLIENT_SECRET=your-secret

# Agent URLs
BRD_GENERATOR_URL=http://localhost:8001
STORY_GENERATOR_URL=http://localhost:8002
CODE_GENERATOR_URL=http://localhost:8003
TEST_GENERATOR_URL=http://localhost:8004
SUPERVISOR_URL=http://localhost:8000
```

## ✅ Success Criteria

1. **BRD Generator** can be invoked via A2A protocol
2. **Memory** stores and retrieves BRD templates from Redis
3. **Policy** validates before execution
4. **Caching** reuses similar BRDs from Azure Search
5. **Monitoring** tracks token usage and performance
6. **Integration** works with Streamlit UI

---

**Next Steps**: Start with BRD Generator Agent implementation
