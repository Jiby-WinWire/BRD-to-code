# 🧠 Mem0 AI Integration Guide

Complete guide for using conversation memory in your BRD-to-Code AI agents.

## 📋 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The Mem0 AI integration adds **conversation memory** to your AI agents, enabling:

- 📝 **Persistent Conversation History**: Remember all user interactions
- 🔍 **Semantic Search**: Retrieve relevant context from past conversations
- 👤 **User Preferences**: Store and recall user-specific settings
- 🔄 **Cross-Session Context**: Use learnings from previous sessions
- 📊 **Agent Interaction Tracking**: Monitor all agent activities
- 🎯 **Context-Aware Responses**: Enhanced prompts with relevant history

### Why Mem0?

Without memory, your AI agents treat each request as isolated. With Mem0, they remember:

- What applications you've built before
- Your preferred programming language and frameworks
- Common patterns in your requirements
- Past successes and failures
- User feedback and preferences

This leads to **faster, more accurate, and personalized** code generation.

---

## 📦 Installation

### Step 1: Install Dependencies

The `mem0ai` package is already in your `requirements.txt`. Install it:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install mem0ai
```

### Step 2: Configure API Keys

Your mem0 API key is already configured in `.env`:

```env
mem0_key="m0-WK246Jb13fjXkp3zAfj07w6DGzxTHemOUk0AcdtD"
```

⚠️ **Important**: Keep this key secret! Do not commit to version control.

**Note**: Mem0 uses OpenAI for embeddings and semantic search. Your Azure OpenAI configuration is already set up:

```env
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
AZURE_OPENAI_MODEL_DEPLOYMENT=gpt4o_mktgenai
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

The system automatically uses Azure OpenAI for mem0 operations.

### Step 3: Verify Installation

Test the installation:

```bash
# Test the memory manager
python src/agents/mem0_manager.py

# Test supervisor integration
python src/agents/supervisor_mem0_integration.py
```

---

## 🚀 Quick Start

### Option 1: Using Memory-Enhanced Supervisor

The easiest way to add memory to your workflow:

```python
from supervisor import Supervisor
from src.agents.supervisor_mem0_integration import add_memory_to_supervisor

# Create supervisor
supervisor = Supervisor()

# Add memory capabilities
supervisor = add_memory_to_supervisor(supervisor, user_id="john_doe")

# Run workflow (memory automatically tracked)
result = await supervisor.run_full_workflow(
    requirement="Create a todo application",
    language="python"
)
```

### Option 2: Using the Integrated Script

Run the integrated supervisor with memory:

```bash
# Interactive mode
python supervisor_with_memory.py

# Quick run
python supervisor_with_memory.py quick "Create a todo app" python

# Demo mode
python supervisor_with_memory.py demo
```

### Option 3: Direct Memory Manager Usage

For custom implementations:

```python
from src.agents.mem0_manager import create_memory_manager

# Create manager
manager = create_memory_manager(user_id="john_doe", session_id="session_001")

# Add conversations
manager.add_conversation(
    role="user",
    content="I want to create a todo list",
    agent_name="brd_generator"
)

# Search memories
memories = manager.get_relevant_memories(
    query="todo application",
    limit=5
)

# Get statistics
stats = manager.get_memory_stats()
```

---

## 🏗️ Architecture

### Components

```
BRD-to-Code/
├── src/agents/
│   ├── mem0_manager.py                      # Core memory management
│   └── supervisor_mem0_integration.py       # Supervisor integration
├── supervisor_with_memory.py                # Memory-enhanced supervisor
├── memory_utils.py                          # CLI utilities
└── MEM0_INTEGRATION_GUIDE.md               # This file
```

### Data Flow

```
User Request
    ↓
Supervisor (with memory)
    ↓
Check relevant memories ──→ Enhance prompt with context
    ↓
Execute workflow
    ↓
Store results in memory ──→ Available for future requests
```

### Memory Structure

Each memory stores:

```json
{
  "content": "User requested: Create a todo application",
  "metadata": {
    "agent": "supervisor",
    "session_id": "supervisor-20260428-144000",
    "timestamp": "2026-04-28T14:40:00",
    "type": "user_requirement",
    "language": "python"
  }
}
```

---

## 📚 Usage Examples

### Example 1: Basic Workflow with Memory

```python
import asyncio
from supervisor import Supervisor
from src.agents.supervisor_mem0_integration import add_memory_to_supervisor

async def main():
    # Initialize
    supervisor = Supervisor()
    supervisor = add_memory_to_supervisor(supervisor, user_id="demo_user")
    
    # Store user requirement
    supervisor.remember_user_requirement(
        requirement="Create a REST API for inventory management",
        language="python"
    )
    
    # Run workflow
    result = await supervisor.run_full_workflow(
        requirement="Create a REST API for inventory management",
        language="python"
    )
    
    # Store workflow completion
    supervisor.remember_workflow_step(
        step_number=1,
        step_name="BRD Generation",
        result=result
    )

asyncio.run(main())
```

### Example 2: Leveraging Past Context

```python
# First request
supervisor.remember_user_requirement(
    requirement="Create a todo app with user auth",
    language="python"
)

# Second request - memory enhances the prompt
context = supervisor.get_relevant_context(
    "Add task categories to my app"
)
# Returns: "Previous context: todo app with user auth..."

enhanced_requirement = supervisor.enhance_requirement_with_memory(
    "Add task categories to my app"
)
# Now includes context about the existing todo app!
```

### Example 3: Storing User Preferences

```python
manager = create_memory_manager(user_id="john_doe")

# Store preferences
manager.store_user_preference("preferred_language", "python")
manager.store_user_preference("framework", "FastAPI")
manager.store_user_preference("database", "PostgreSQL")

# Retrieve later
prefs = manager.get_user_preferences()
# Returns: {"preferred_language": "python", "framework": "FastAPI", ...}
```

### Example 4: Tracking Agent Performance

```python
# After each agent execution
supervisor.remember_agent_interaction(
    agent_name="brd_generator",
    input_data="Create todo app",
    output_data="Generated BRD with 5 requirements",
    success=True,
    metadata={
        "tokens_used": 1500,
        "duration_seconds": 12.5
    }
)

# Analyze later
stats = supervisor.get_memory_stats()
print(f"Agents used: {stats['agents']}")
print(f"Total interactions: {stats['total_memories']}")
```

---

## 🛠️ API Reference

### Mem0Manager

Core memory management class.

#### Constructor

```python
Mem0Manager(user_id: Optional[str] = None)
```

#### Methods

##### `set_session(session_id: str)`
Set the current session ID for memory tracking.

##### `add_conversation(role, content, agent_name, metadata)`
Store a conversation message.

**Parameters:**
- `role` (str): Speaker role (user, assistant, system)
- `content` (str): Message content
- `agent_name` (str): Name of the agent
- `metadata` (dict): Additional metadata

**Returns:** Dictionary with success status and memory ID

##### `get_relevant_memories(query, limit, agent_filter)`
Retrieve relevant memories using semantic search.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Max results (default: 5)
- `agent_filter` (str): Filter by agent name

**Returns:** List of relevant memory items

##### `get_all_memories(limit)`
Get all memories for the user.

##### `store_user_preference(preference_key, preference_value)`
Store a user preference.

##### `store_agent_output(agent_name, input_data, output_data, metadata)`
Store agent input/output for reference.

##### `get_conversation_history(limit)`
Get recent conversation messages.

##### `build_context_prompt(current_input, memory_limit)`
Build enhanced prompt with memory context.

##### `get_memory_stats()`
Get statistics about stored memories.

##### `delete_memory(memory_id)`
Delete a specific memory.

### SupervisorWithMemory Methods

Additional methods added to Supervisor when using memory:

##### `remember_user_requirement(requirement, language, template_id)`
Store initial user requirement.

##### `remember_agent_interaction(agent_name, input_data, output_data, success, metadata)`
Store agent interaction.

##### `remember_workflow_step(step_number, step_name, result)`
Store workflow step completion.

##### `remember_generated_files(file_paths)`
Store information about generated files.

##### `get_relevant_context(query, limit)`
Get relevant context from previous conversations.

##### `enhance_requirement_with_memory(requirement)`
Enhance requirement with memory context.

##### `get_memory_stats()`
Get memory statistics.

---

## 🔧 Command-Line Utilities

Use `memory_utils.py` for querying and managing memories:

### Search Memories

```bash
python memory_utils.py search "todo application" --user john_doe --limit 10
```

### List All Memories

```bash
python memory_utils.py list --user john_doe
```

### Get Statistics

```bash
python memory_utils.py stats --user john_doe
```

### View Conversation History

```bash
python memory_utils.py history --user john_doe --session supervisor-20260428-144000
```

### Export Memories

```bash
python memory_utils.py export memories.json --user john_doe
```

### Delete a Memory

```bash
python memory_utils.py delete mem_12345 --user john_doe
```

---

## ✅ Best Practices

### 1. Use Unique User IDs

Always use meaningful user identifiers:

```python
# Good
supervisor = add_memory_to_supervisor(supervisor, user_id="john_doe")

# Avoid
supervisor = add_memory_to_supervisor(supervisor, user_id="user1")
```

### 2. Store Rich Metadata

Include helpful metadata for better retrieval:

```python
manager.add_conversation(
    role="user",
    content="Create API",
    agent_name="brd_generator",
    metadata={
        "project_type": "api",
        "domain": "inventory",
        "complexity": "medium",
        "deadline": "2026-05-01"
    }
)
```

### 3. Regular Memory Checks

Before starting workflows, check for relevant context:

```python
context = supervisor.get_relevant_context(user_requirement)
if context:
    print(f"Found relevant context: {context}")
    enhanced_requirement = supervisor.enhance_requirement_with_memory(user_requirement)
```

### 4. Track Feedback

Store user feedback for continuous improvement:

```python
supervisor.remember_user_feedback(
    feedback="The generated code worked perfectly!",
    rating=5
)
```

### 5. Export Regularly

Backup memories periodically:

```bash
python memory_utils.py export backups/memories_$(date +%Y%m%d).json --user john_doe
```

### 6. Clean Up Old Sessions

For new unrelated projects, consider using a new user_id or clearing old memories.

---

## 🐛 Troubleshooting

### Issue: "mem0_key not found"

**Solution:** Check your `.env` file has:
```env
mem0_key="your-actual-key-here"
```

### Issue: "OPENAI_API_KEY environment variable" or OpenAI errors

**Cause:** Mem0 uses OpenAI for embeddings and semantic search.

**Solution:** Your Azure OpenAI is already configured! The system automatically uses it. If you see this error, verify in `.env`:
```env
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=your-endpoint
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

The mem0_manager automatically configures mem0 to use Azure OpenAI instead of regular OpenAI.

### Issue: No memories retrieved

**Causes:**
1. Wrong user_id
2. No memories stored yet
3. Query doesn't match stored content

**Solution:**
```bash
# Check if memories exist
python memory_utils.py stats --user your_user_id

# List all memories
python memory_utils.py list --user your_user_id
```

### Issue: Memory search returns irrelevant results

**Solution:** Be more specific in queries and metadata:

```python
# Instead of
memories = manager.get_relevant_memories("app")

# Use
memories = manager.get_relevant_memories("todo application with authentication", limit=3)
```

### Issue: Import errors

**Solution:**
```bash
# Ensure you're in the project root
cd BRD-to-code

# Re-install dependencies
pip install -r requirements.txt

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Issue: Mem0 API rate limits

**Solution:**
- Check your Mem0 plan limits
- Implement caching for frequently accessed memories
- Batch memory operations where possible

---

## 🎓 Advanced Usage

### Custom Memory Filtering

```python
# Filter by specific agent
memories = manager.get_relevant_memories(
    query="error handling",
    agent_filter="code_generator"
)

# Filter by time period (using metadata)
all_memories = manager.get_all_memories()
recent = [m for m in all_memories 
          if m['metadata'].get('timestamp', '') > '2026-04-01']
```

### Multi-User Scenarios

```python
# Different users, isolated memories
user1_manager = create_memory_manager(user_id="alice")
user2_manager = create_memory_manager(user_id="bob")

# Team shared memory
team_manager = create_memory_manager(user_id="team_project_alpha")
```

### Memory-Driven Recommendations

```python
def recommend_next_feature(user_id):
    manager = create_memory_manager(user_id=user_id)
    
    # Get all past projects
    projects = manager.get_relevant_memories("application project", limit=20)
    
    # Analyze patterns
    # ... your logic here ...
    
    return recommendations
```

---

## 📞 Support

For issues or questions:

1. Check this guide
2. Review example files:
   - `supervisor_with_memory.py`
   - `src/agents/mem0_manager.py`
3. Check Mem0 documentation: https://docs.mem0.ai/
4. Review your API usage: https://app.mem0.ai/

---

## 📝 Summary

You now have a complete conversation memory system that:

✅ Tracks all user requirements and preferences  
✅ Remembers agent interactions and outputs  
✅ Provides semantic search across conversations  
✅ Enhances prompts with relevant context  
✅ Supports multi-user scenarios  
✅ Includes CLI tools for memory management  

**Next Steps:**

1. Run the interactive demo: `python supervisor_with_memory.py demo`
2. Try the memory utilities: `python memory_utils.py --help`
3. Integrate into your existing workflows
4. Start building with memory-enhanced AI! 🚀

---

*Last updated: April 28, 2026*
