# 🎯 BRD Generator Agent - Setup Checklist

Use this checklist to track your progress in setting up and testing the new BRD Generator Agent.

## 📦 Phase 1: Prerequisites

### Copy Agent Base Library
- [ ] Locate the `mylibs/agent_base/` directory from your existing project
- [ ] Copy entire `mylibs/` folder to BRD-to-code project root
- [ ] Verify these files exist:
  - [ ] `mylibs/agent_base/__init__.py`
  - [ ] `mylibs/agent_base/agent.py`
  - [ ] `mylibs/agent_base/tools.py`
  - [ ] `mylibs/agent_base/memory.py`
  - [ ] `mylibs/agent_base/types.py`
  - [ ] `mylibs/agent_base/a2a_server.py` (if available)

### Install & Start Redis
- [ ] Choose installation method:
  - [ ] Option A: Docker: `docker run -d -p 6379:6379 --name redis redis:7-alpine`
  - [ ] Option B: WSL: `wsl` then `sudo service redis-server start`
  - [ ] Option C: Native Windows (download from Redis.io)
- [ ] Test Redis connection: `docker exec -it redis redis-cli PING`
- [ ] Expected result: `PONG`
- [ ] Redis accessible at: `redis://localhost:6379`

## 🔧 Phase 2: Configuration

### Install Python Dependencies
- [ ] Navigate to project root: `cd "d:\OneDrive - WinWire\Task\BRD-to-code"`
- [ ] Create virtual environment (optional but recommended):
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify key packages installed:
  - [ ] `pip show a2a-sdk` → version >= 0.3.11
  - [ ] `pip show langchain-core` → version >= 0.1.0
  - [ ] `pip show redis` → version == 6.2.0
  - [ ] `pip show pydantic` → version >= 2.5.0
  - [ ] `pip show azure-search-documents` → installed

### Configure Environment Variables
- [ ] Copy `.env.example` to `.env`: `cp .env.example .env`
- [ ] Edit `.env` with your values:
  - [ ] `AZURE_OPENAI_ENDPOINT` = Your Azure OpenAI endpoint URL
  - [ ] `AZURE_OPENAI_KEY` = Your Azure OpenAI API key
  - [ ] `AZURE_OPENAI_DEPLOYMENT` = Your deployment name (e.g., gpt4o_mktgenai)
  - [ ] `REDIS_URL` = redis://localhost:6379
  - [ ] `ENABLE_CACHING` = false (for initial testing)
  - [ ] `ENABLE_POLICY` = false (for initial testing)
- [ ] Save `.env` file
- [ ] Verify `.env` is in `.gitignore` (it should already be)

### Test Azure OpenAI Connection
- [ ] Run quick test:
  ```python
  from openai import AzureOpenAI
  import os
  from dotenv import load_dotenv
  
  load_dotenv()
  client = AzureOpenAI(
      azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
      api_key=os.getenv("AZURE_OPENAI_KEY"),
      api_version="2024-08-01-preview"
  )
  response = client.chat.completions.create(
      model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
      messages=[{"role": "user", "content": "Say 'test successful'"}],
      max_tokens=10
  )
  print(response.choices[0].message.content)
  ```
- [ ] Expected output: "test successful" or similar

## 🧪 Phase 3: Testing

### Test 1: Standalone Mode
- [ ] Run standalone test:
  ```bash
  python -m src.agents.brd_generator.agent_executor --mode test
  ```
- [ ] Check for successful initialization logs:
  - [ ] `BRDRedisDataManager initialized`
  - [ ] `Memory Manager initialized`
  - [ ] `BRD Generator Agent fully initialized`
- [ ] Check for successful generation logs:
  - [ ] `Generating BRD from test prompt...`
  - [ ] `Successfully generated BRD JSON`
  - [ ] `Successfully generated BRD markdown`
  - [ ] `✅ Test completed successfully!`
- [ ] Verify output files created:
  - [ ] `output/brd_test/test_brd.json` exists
  - [ ] `output/brd_test/test_brd.md` exists
  - [ ] JSON file contains valid BRD structure
  - [ ] Markdown file is readable

### Test 2: Redis State Verification
- [ ] Connect to Redis CLI: `docker exec -it redis redis-cli`
- [ ] Check for BRD keys: `KEYS "brd:*"`
- [ ] Expected: At least one key like `brd:task:test-<uuid>`
- [ ] View task status: `GET "brd:task:test-<uuid>"`
- [ ] Expected: JSON string with status, user_prompt, brd_json, etc.
- [ ] Exit Redis CLI: `exit`

### Test 3: A2A Server Mode
- [ ] Start A2A server:
  ```bash
  python -m src.agents.brd_generator.agent_executor --mode server --port 8001
  ```
- [ ] Check startup logs:
  - [ ] `BRD Generator Agent fully initialized`
  - [ ] `Starting A2A server on port 8001`
  - [ ] No error messages
- [ ] Test health endpoint (in new terminal):
  ```bash
  curl http://localhost:8001/health
  ```
- [ ] Expected: `{"status": "healthy"}` or similar
- [ ] Test SendTaskRequest:
  ```bash
  curl -X POST http://localhost:8001/tasks/send \
    -H "Content-Type: application/json" \
    -d '{
      "id": "curl-test-001",
      "params": {
        "message": {
          "parts": [{"type": "text", "text": "Create a BRD for a mobile app"}]
        }
      }
    }'
  ```
- [ ] Expected: JSON response with `result.status` = `COMPLETED`
- [ ] Stop server: `Ctrl+C`

### Test 4: Custom Prompt
- [ ] Create custom test script `test_custom_brd.py`:
  ```python
  import asyncio
  import os
  from dotenv import load_dotenv
  from src.agents.brd_generator import BRDGeneratorAgent
  
  load_dotenv()
  
  async def test():
      agent = BRDGeneratorAgent(
          session_id="custom-test",
          redis_url="redis://localhost:6379",
          azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
          azure_openai_key=os.getenv("AZURE_OPENAI_KEY"),
          azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
      )
      
      # YOUR CUSTOM PROMPT
      result = await agent.generate_brd(
          user_prompt="Build a real-time chat application with WebSockets",
          task_id="custom-001"
      )
      
      print("\n=== BRD Generated ===")
      print(f"Title: {result['brd_json']['title']}")
      print(f"From Cache: {result['from_cache']}")
      print("\n" + result['brd_markdown'])
  
  asyncio.run(test())
  ```
- [ ] Run script: `python test_custom_brd.py`
- [ ] Verify BRD generated successfully
- [ ] Try running again with same prompt
- [ ] Expected: Second run might use cache (if caching enabled)

## 🚀 Phase 4: Optional Features

### Enable Semantic Caching (Optional)
- [ ] Set up Azure Search resource in Azure Portal
- [ ] Create search index: `brd-cache-index`
- [ ] Get Azure Search endpoint and key
- [ ] Update `.env`:
  - [ ] `AZURE_SEARCH_ENDPOINT` = Your search endpoint
  - [ ] `AZURE_SEARCH_KEY` = Your search key
  - [ ] `AZURE_SEARCH_INDEX` = brd-cache-index
  - [ ] `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` = text-embedding-ada-002
  - [ ] `ENABLE_CACHING` = true
- [ ] Restart agent and test caching:
  - [ ] Generate BRD with prompt A → from_cache=False
  - [ ] Generate BRD with similar prompt → from_cache=True
- [ ] Check Azure Search index has documents

### Enable Policy Management (Optional)
- [ ] Deploy Discovery Service (from DiscoveryServiceAPI project)
- [ ] Start Discovery Service on port 8090
- [ ] Update `.env`:
  - [ ] `DISCOVERY_API_URL` = http://localhost:8090
  - [ ] `CLIENT_ID` = brd-generator-client
  - [ ] `ENABLE_POLICY` = true
- [ ] Restart agent and test policy validation:
  - [ ] Check logs for "Policy validation complete"
  - [ ] Verify agent/resource/task policies checked

## 🔄 Phase 5: Integration

### Integrate with Existing Streamlit UI
- [ ] Update `src/ui/app.py` to use new BRDGeneratorAgent
- [ ] Replace old `brd_generator.generate_brd_from_prompt()` calls
- [ ] Test UI BRD generation flow
- [ ] Verify Redis state updates during UI usage

### Test with Existing Pipeline
- [ ] Update `src/agents/orchestrator.py` to use new agent
- [ ] Run full pipeline: BRD → Stories → Code → Tests
- [ ] Verify all stages complete successfully

## 📊 Phase 6: Monitoring & Validation

### Verify Logs
- [ ] Check logs for INFO messages (not errors)
- [ ] Verify Redis operations logged
- [ ] Check Azure OpenAI calls logged
- [ ] Verify token usage tracked

### Verify Redis Data
- [ ] Check Redis for task keys: `KEYS "brd:task:*"`
- [ ] Check Redis for session keys: `KEYS "brd:session:*"`
- [ ] Verify TTL is set: `TTL "brd:task:<some-task-id>"`
- [ ] Expected TTL: ~86400 seconds (24 hours)

### Performance Metrics
- [ ] Measure BRD generation time (typical: 5-15 seconds)
- [ ] Check token usage (typical: 500-2000 tokens)
- [ ] Test cache performance (cache hit should be <1 second)

## 🐛 Troubleshooting

### Issue: Module not found errors
- [ ] Solution: Verify `mylibs/agent_base/` is in project root
- [ ] Add project root to PYTHONPATH if needed
- [ ] Check all `__init__.py` files exist

### Issue: Redis connection errors
- [ ] Solution: Verify Redis is running: `docker ps`
- [ ] Test connection: `docker exec -it redis redis-cli PING`
- [ ] Check firewall/port 6379 is accessible

### Issue: Azure OpenAI authentication errors
- [ ] Solution: Verify `.env` credentials are correct
- [ ] Test credentials with curl or Python script
- [ ] Check endpoint URL includes trailing slash

### Issue: Import errors for a2a-sdk
- [ ] Solution: Reinstall with http-server extras:
  ```bash
  pip install --upgrade "a2a-sdk[http-server]>=0.3.11"
  ```

## ✅ Final Validation

- [ ] All 8 components created and in place:
  1. [ ] `brd_generator_agent.py`
  2. [ ] `brd_generator_tool.py`
  3. [ ] `memory_manager.py`
  4. [ ] `policy_manager.py`
  5. [ ] `agent_executor.py`
  6. [ ] `data/policy_types.json`
  7. [ ] `prompts/brd_generation.prompt`
  8. [ ] `README.md`

- [ ] All tests passing:
  - [ ] Standalone test
  - [ ] Redis verification
  - [ ] A2A server test
  - [ ] Custom prompt test

- [ ] Documentation reviewed:
  - [ ] `AGENT_CONVERSION_PLAN.md`
  - [ ] `BRD_GENERATOR_IMPLEMENTATION_SUMMARY.md`
  - [ ] `QUICK_START.md`
  - [ ] `src/agents/brd_generator/README.md`

## 📝 Next Steps After BRD Generator Works

Once all checkboxes above are complete:

1. [ ] Convert Story Generator Agent (brd_to_jira)
2. [ ] Convert Code Generator Agent (story_to_code)
3. [ ] Convert Test Generator Agent (test_generator)
4. [ ] Build Supervisor Agent (orchestrator replacement)
5. [ ] End-to-end integration testing
6. [ ] Production deployment planning

---

**Progress Tracker:**
- Prerequisites: __ / 6 items
- Configuration: __ / 9 items
- Testing: __ / 23 items
- Optional Features: __ / 10 items
- Integration: __ / 4 items
- Monitoring: __ / 8 items
- Final Validation: __ / 13 items

**Total Progress: __ / 73 items complete**

---

**Last Updated:** Created on agent implementation
**Status:** Ready for setup and testing
**Blockers:** Need mylibs/agent_base from existing project
