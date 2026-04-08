"""FastAPI server for Jira To Code Agent

Exposes the JiraToCodeAgent as HTTP endpoints for easy integration and testing.
Run with: uvicorn src.agents.jira_to_code.main:app --host 0.0.0.0 --port 8010 --reload
"""

import os
import json
import logging
from typing import Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.agents.jira_to_code.agent_executor import create_jira_agent

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Jira To Code Agent",
    description="Convert Jira issue descriptions into starter code and tests",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Request/Response models
class JiraIssueRequest(BaseModel):
    issue_text: str = Field(..., description="Jira issue description", min_length=1)
    task_id: Optional[str] = Field(None, description="Optional task identifier")
    include_tests: bool = Field(default=True, description="Include test code in generation")


class CodeGenerationResponse(BaseModel):
    code_snippet: str = Field(..., description="Generated code snippet")
    explanation: Optional[str] = Field(None, description="Explanation of the generated code")
    task_id: str = Field(..., description="Task identifier")
    from_cache: bool = Field(default=False, description="Whether result was from cache")


class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Health status")
    agent: str = Field("jira-to-code", description="Agent name")
    version: str = Field("1.0.0", description="Agent version")


# Global agent instance
_agent = None


def get_agent():
    """Get or create the global agent instance"""
    global _agent
    if _agent is None:
        logger.info("Initializing JiraToCodeAgent...")
        _agent = create_jira_agent()
        logger.info("✅ JiraToCodeAgent ready")
    return _agent


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    logger.info("🚀 Starting Jira To Code Agent Server")
    get_agent()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        agent = get_agent()
        return HealthResponse(status="healthy", agent="jira-to-code", version="1.0.0")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Agent not available")


@app.post("/convert", response_model=CodeGenerationResponse)
async def convert_jira_to_code(request: JiraIssueRequest) -> CodeGenerationResponse:
    """
    Convert a Jira issue description into code
    
    Args:
        request: JiraIssueRequest with issue_text
        
    Returns:
        CodeGenerationResponse with generated code
    """
    task_id = request.task_id or str(uuid4())
    
    try:
        logger.info(f"Converting Jira issue (task_id={task_id})")
        
        agent = get_agent()
        result = await agent.convert_issue(
            issue_text=request.issue_text,
            task_id=task_id
        )
        
        code_snippet = result.get("code") or result.get("code_snippet") or ""
        explanation = result.get("explanation")
        
        logger.info(f"✅ Code generation completed (task_id={task_id})")
        
        return CodeGenerationResponse(
            code_snippet=code_snippet,
            explanation=explanation,
            task_id=task_id,
            from_cache=False
        )
        
    except Exception as e:
        logger.error(f"Code generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate code: {str(e)}")


@app.post("/batch-convert")
async def batch_convert(issues: list[JiraIssueRequest]) -> list[CodeGenerationResponse]:
    """
    Convert multiple Jira issues in batch
    
    Args:
        issues: List of JiraIssueRequest objects
        
    Returns:
        List of CodeGenerationResponse objects
    """
    results = []
    
    logger.info(f"Processing batch of {len(issues)} issues")
    
    try:
        agent = get_agent()
        
        for issue in issues:
            task_id = issue.task_id or str(uuid4())
            try:
                result = await agent.convert_issue(
                    issue_text=issue.issue_text,
                    task_id=task_id
                )
                
                code_snippet = result.get("code") or result.get("code_snippet") or ""
                explanation = result.get("explanation")
                
                results.append(CodeGenerationResponse(
                    code_snippet=code_snippet,
                    explanation=explanation,
                    task_id=task_id,
                    from_cache=False
                ))
            except Exception as e:
                logger.error(f"Failed to convert issue {task_id}: {e}")
                results.append(CodeGenerationResponse(
                    code_snippet="# Error generating code",
                    explanation=f"Error: {str(e)}",
                    task_id=task_id,
                    from_cache=False
                ))
        
        logger.info(f"✅ Batch processing completed: {len(results)}/{len(issues)} successful")
        return results
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@app.get("/info")
async def agent_info():
    """Get agent information"""
    try:
        agent = get_agent()
        return {
            "name": "Jira To Code Agent",
            "version": "1.0.0",
            "description": "Convert Jira issues into starter code and tests",
            "capabilities": [
                "Convert Jira issue descriptions to code",
                "Generate test stubs",
                "Support for multiple programming languages",
                "Batch processing"
            ],
            "endpoints": [
                "/health - Health check",
                "/convert - Single issue conversion",
                "/batch-convert - Batch issue conversion",
                "/info - Agent information",
                "/docs - Swagger UI",
                "/redoc - ReDoc documentation"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get agent info: {e}")
        raise HTTPException(status_code=500, detail="Unable to retrieve agent info")


@app.get("/")
async def root():
    """Root endpoint with welcome message"""
    return {
        "message": "Welcome to Jira To Code Agent API",
        "docs": "/docs",
        "endpoints": {
            "convert": "POST /convert - Convert single Jira issue to code",
            "batch": "POST /batch-convert - Convert multiple issues",
            "health": "GET /health - Health check",
            "info": "GET /info - Agent information"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with: python -m uvicorn src.agents.jira_to_code.main:app --host 0.0.0.0 --port 8010 --reload
    uvicorn.run(
        "src.agents.jira_to_code.main:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )
