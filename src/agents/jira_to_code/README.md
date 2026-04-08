# Jira To Code Agent

This module mirrors the structure of the `brd_generator` agent and provides a lightweight
agent that converts Jira issue descriptions into starter code snippets and tests.

## Files

- `agent_executor.py` — runner for standalone tests and A2A server
- `jira_to_code_agent.py` — `JiraToCodeAgent` class
- `jira_to_code_tool.py` — tool implementing generation logic
- `memory_manager.py` — Redis-backed status storage
- `policy_manager.py` — policy validations (Discovery Service integration)
- `prompts/jira_to_code.prompt` — default prompt template

## Usage

Run a quick standalone test:

```powershell
Set-Location BRD-to-code
python -m src.agents.jira_to_code.agent_executor --mode test
```

Start A2A server on port 8010:

```powershell
Set-Location BRD-to-code
python -m src.agents.jira_to_code.agent_executor --mode server --port 8010
```
