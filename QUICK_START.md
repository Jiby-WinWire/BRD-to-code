# Quick Start Guide - BRD Generator Agent

Get the BRD Generator agent running in 5 minutes!

## Step 1: Prerequisites (2 minutes)

### Install Redis
```bash
# Option A: Docker (Recommended)
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Option B: Windows (via WSL)
wsl
sudo service redis-server start

# Verify Redis is running
docker exec -it redis redis-cli PING
# Should return: PONG
```

### Copy Agent Base Library
```bash
# You need to copy mylibs/agent_base/ from the winmind project
# to your BRD-to-code project root

# Example structure:
# BRD-to-code/
# ├── mylibs/
# │   └── agent_base/
# │       ├── __init__.py
# │       ├── agent.py
# │       ├── tools.py
# │       ├── memory.py
# │       └── types.py
# └── src/
```

## Step 2: Install Dependencies (1 minute)

```bash
# Navigate to project root
cd "d:\OneDrive - WinWire\Task\BRD-to-code"

# Install all dependencies
pip install -r requirements.txt

# Verify key packages
pip list | grep -E "a2a-sdk|langchain|redis|azure-search"
```

## Step 3: Configure Environment (1 minute)

### Create `.env` file
```bash
# Copy template
cp .env.example .env

# Edit .env with your credentials
notepad .env
```

### Minimum Required Configuration
```bash
# REQUIRED - Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_KEY=your_api_key_here
AZURE_OPENAI_DEPLOYMENT=gpt4o_mktgenai

# REQUIRED - Redis
REDIS_URL=redis://localhost:6379

# OPTIONAL - Disable features for quick start
ENABLE_CACHING=false
ENABLE_POLICY=false
```

**Important**: Update `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, and `AZURE_OPENAI_DEPLOYMENT` with your actual values!

## Step 4: Run Standalone Test (1 minute)

```bash
# Run the test
python -m src.agents.brd_generator.agent_executor --mode test
```

### Expected Output
```
INFO - BRDRedisDataManager initialized
INFO - Memory Manager initialized
INFO - Policy validation disabled
INFO - BRD Generator Agent fully initialized
INFO - Generating BRD from test prompt...
INFO - Successfully generated BRD JSON with keys: ['title', 'description', ...]
INFO - Successfully generated BRD markdown
================================================================================
BRD GENERATION RESULT
================================================================================
From Cache: False
Similarity Score: 1.000
BRD Title: Customer Relationship Management System
================================================================================
MARKDOWN OUTPUT:
================================================================================
# Customer Relationship Management System
...
================================================================================
INFO - BRD saved to: d:\OneDrive - WinWire\Task\BRD-to-code\output\brd_test
✅ Test completed successfully!
```

### Check Output Files
```bash
# Navigate to output directory
cd output/brd_test

# View JSON
cat test_brd.json

# View Markdown
cat test_brd.md
```

## Step 5: Verify Redis State
```bash
# Connect to Redis CLI
docker exec -it redis redis-cli

# Check BRD keys
KEYS "brd:*"

# View a task status
GET "brd:task:test-<uuid>"

# Exit Redis CLI
exit
```

## 🎯 Quick Test Commands

### Test Different Prompts
```python
# Create quick_test.py
import asyncio
import os
from dotenv import load_dotenv
from src.agents.brd_generator import BRDGeneratorAgent

load_dotenv()

async def test():
    agent = BRDGeneratorAgent(
        session_id="quick-test",
        redis_url="redis://localhost:6379",
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        enable_caching=False,
        enable_policy=False
    )
    
    result = await agent.generate_brd(
        user_prompt="Build a simple todo list app with user authentication",
        task_id="quick-test-001"
    )
    
    print(result['brd_markdown'])

asyncio.run(test())
```

Run it:
```bash
python quick_test.py
```

## 🚀 Start A2A Server

### Run Server
```bash
python -m src.agents.brd_generator.agent_executor --mode server --port 8001
```

### Test with curl
```bash
# Send SendTaskRequest
curl -X POST http://localhost:8001/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "curl-test-001",
    "params": {
      "message": {
        "parts": [
          {
            "type": "text",
            "text": "Create a BRD for an e-commerce platform"
          }
        ]
      }
    }
  }'
```

### Test with Python
```python
import httpx
import asyncio

async def test_a2a():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/tasks/send",
            json={
                "id": "python-test-001",
                "params": {
                    "message": {
                        "parts": [
                            {
                                "type": "text",
                                "text": "Create a BRD for a mobile fitness app"
                            }
                        ]
                    }
                }
            }
        )
        print(response.json())

asyncio.run(test_a2a())
```

## 🐛 Troubleshooting

### Error: Redis Connection Refused
```bash
# Check Redis is running
docker ps | grep redis

# Start Redis if not running
docker start redis

# Or create new container
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Error: Module 'mylibs' not found
```bash
# Ensure mylibs/agent_base is in project root
ls mylibs/agent_base/

# If missing, copy from your winmind project
# OR create a symlink
```

### Error: Azure OpenAI Authentication Failed
```bash
# Check .env file has correct values
cat .env | grep AZURE_OPENAI

# Test Azure OpenAI directly
curl -X POST "$AZURE_OPENAI_ENDPOINT/openai/deployments/$AZURE_OPENAI_DEPLOYMENT/chat/completions?api-version=2024-08-01-preview" \
  -H "api-key: $AZURE_OPENAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

### Error: Import Error for A2A SDK
```bash
# Reinstall a2a-sdk
pip install --upgrade "a2a-sdk[http-server]>=0.3.11"

# Verify installation
python -c "from a2a_sdk.task_mgmt import InMemoryTaskManager; print('OK')"
```

## ✅ Success Checklist

- [ ] Redis running on port 6379
- [ ] `mylibs/agent_base/` copied to project
- [ ] Dependencies installed (`pip list | grep a2a-sdk`)
- [ ] `.env` configured with Azure OpenAI credentials
- [ ] Standalone test passes
- [ ] Output files generated in `output/brd_test/`
- [ ] Redis keys visible (`KEYS "brd:*"`)
- [ ] A2A server starts on port 8001
- [ ] curl test returns valid JSON response

## 📚 Next Steps

Once the Quick Start works:

1. **Enable Caching** (Optional)
   - Set up Azure Search
   - Configure `AZURE_SEARCH_ENDPOINT` and `AZURE_SEARCH_KEY`
   - Set `ENABLE_CACHING=true`

2. **Enable Policy** (Optional)
   - Deploy Discovery Service
   - Configure `DISCOVERY_API_URL`
   - Set `ENABLE_POLICY=true`

3. **Integrate with UI**
   - Update Streamlit app to use new agent
   - Replace old `brd_generator.py` calls

4. **Convert Other Agents**
   - Story Generator
   - Code Generator
   - Test Generator

5. **Build Supervisor**
   - Coordinate all agents
   - A2A task delegation

## 🎓 Learning Resources

- [Agent Base README](mylibs/agent_base/README.md)
- [BRD Generator README](src/agents/brd_generator/README.md)
- [Conversion Plan](AGENT_CONVERSION_PLAN.md)
- [Implementation Summary](BRD_GENERATOR_IMPLEMENTATION_SUMMARY.md)

---

**Need Help?**
- Check logs for detailed error messages
- Verify all environment variables are set
- Ensure Redis connection is working
- Test Azure OpenAI credentials separately

**Ready to go? Start with Step 1!** 🚀
