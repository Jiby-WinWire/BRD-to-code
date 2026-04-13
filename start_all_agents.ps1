# PowerShell script to start all 5 A2A agents
# Each agent runs in a separate terminal window
# NOTE: Architecture Generator Agent (port 7000) must be started separately

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting All BRD-to-Code Agents" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Function to start an agent in a new window
function Start-Agent {
    param(
        [string]$Name,
        [int]$Port,
        [string]$Module
    )
    
    Write-Host "Starting $Name on port $Port..." -ForegroundColor Green
    
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "& {
            Write-Host '========================================' -ForegroundColor Cyan;
            Write-Host '  $Name (Port: $Port)' -ForegroundColor Cyan;
            Write-Host '========================================' -ForegroundColor Cyan;
            Write-Host '';
            .venv\Scripts\python.exe -m $Module --mode server --port $Port
        }"
    )
    
    Start-Sleep -Milliseconds 500
}

# Start all agents
Write-Host ""
Write-Host "Launching agents in separate windows..." -ForegroundColor Yellow
Write-Host ""

Start-Agent -Name "BRD Generator" -Port 8001 -Module "src.agents.brd_generator.agent_executor"
Start-Agent -Name "BRD to JIRA" -Port 8002 -Module "src.agents.brd_to_jira.agent_executor"
Start-Agent -Name "Code to Test" -Port 8003 -Module "src.agents.code_to_test_new.agent_executor"
Start-Agent -Name "Validation" -Port 8004 -Module "src.agents.validation.agent_executor"
Start-Agent -Name "JIRA to Code" -Port 8005 -Module "src.agents.jira_to_code.agent_executor"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All agents started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Agent URLs:" -ForegroundColor Yellow
Write-Host "  1. BRD Generator:         http://localhost:8001" -ForegroundColor White
Write-Host "  2. BRD to JIRA:           http://localhost:8002" -ForegroundColor White
Write-Host "  3. Code to Test:          http://localhost:8003" -ForegroundColor White
Write-Host "  4. Validation:            http://localhost:8004" -ForegroundColor White
Write-Host "  5. JIRA to Code:          http://localhost:8005" -ForegroundColor White
Write-Host ""
Write-Host "Additional Agents (start separately):" -ForegroundColor Yellow
Write-Host "  6. Architecture Generator: http://localhost:7000" -ForegroundColor Gray
Write-Host "     (Run: python path\to\arch_generator_agent.py)" -ForegroundColor Gray
Write-Host ""
Write-Host "Wait 10-15 seconds for all agents to initialize..." -ForegroundColor Yellow
Write-Host ""
Write-Host "To verify agents are ready, run:" -ForegroundColor Cyan
Write-Host "  python test_all_agents.py" -ForegroundColor White
Write-Host ""
Write-Host "To run the demo, run:" -ForegroundColor Cyan
Write-Host "  python demo.py" -ForegroundColor White
Write-Host ""
Write-Host "To stop all agents, close all the terminal windows" -ForegroundColor Yellow
Write-Host ""
