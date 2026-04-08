from typing import Optional, Dict, Any, Literal, AsyncIterable
from pydantic import BaseModel, Field

from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    MessageSendParams,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent
)

# Compatibility types for old API
class JSONRPCRequest(BaseModel):
    """Base JSONRPC request"""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: Any = None

class JSONRPCResponse(BaseModel):
    """Base JSONRPC response"""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error: Any = None

class TaskSendParams(MessageSendParams):
    """Compatibility alias for MessageSendParams"""
    pass

class SendTaskStreamingRequest(JSONRPCRequest):
    """Streaming request type for compatibility"""
    method: Literal['tasks/sendSubscribe'] = 'tasks/sendSubscribe'
    params: TaskSendParams

class SendTaskStreamingResponse(JSONRPCResponse):
    """Streaming response type for compatibility"""
    result: TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None = None

class SendTaskRequest(JSONRPCRequest):
    """Send task request type for compatibility"""
    method: Literal['tasks/send'] = 'tasks/send'
    params: TaskSendParams

class SendTaskResponse(JSONRPCResponse):
    """Send task response type for compatibility"""  
    result: Any = None

class DocumentMetadata(BaseModel):
    """Document metadata for file upload integration"""
    original_filename: Optional[str] = None
    original_file_type: Optional[str] = None
    original_file_size: Optional[int] = None
    drive_file_id: Optional[str] = None
    drive_file_name: Optional[str] = None
    drive_web_view_link: Optional[str] = None
    drive_download_link: Optional[str] = None
    upload_timestamp: Optional[int] = None
    upload_status: Optional[str] = None

class BaseAgentSkill(AgentSkill):
    """Extended AgentSkill with input/output schemas for agent planning"""    
    description: str # Mandatory detailed description of the skill
    examples: list[str] # Mandatory list of example use cases
    tags: list[str] # Mandatory list of tags for categorization
    input_schema: Dict[str, Any] # Mandatory detailed input schema for agent planning
    output_schema: Optional[Dict[str, Any]] = None # Optional detailed output schema for agent planning

class BaseAgentCapabilities(AgentCapabilities):
    pass

class AgentAccess(BaseModel):
    accessGroup: str # Team Group name
    vnet: str # VPN details for ecosystem connection
    authentication_required: bool # Define if token authentication required else Access Group


class BaseAgentAuthentication(BaseModel):
    """Authentication configuration for agents"""
    schemes: list[str] # Mandatory list of authentication schemes
    credentials: str | None = None # Mandatory credentials information

class ServiceAuthentication(BaseModel):
    url : str
    token : str

class BaseAgentcard(AgentCard):
    description: str # Mandatory short description of the agent
    visibility: AgentAccess # Mandatory field for defining Authentication
    services: Optional[ServiceAuthentication] = None  # Additonal Service Authentication
    authentication: BaseAgentAuthentication # Mandatory authentication configuration
    owner_email: str # Mandatory field for agent owner contact
    skills: list['BaseAgentSkill']  # Override to use BaseAgentSkill instead of AgentSkill
    # Override to make these optional with defaults (they're required in AgentCard but we specify in skills)
    default_input_modes: Optional[list[str]] = ["text"]
    default_output_modes: Optional[list[str]] = ["text"]

class authenticationConfig(BaseModel):
    scheme: str | None = None # Jwt or Okta or API
    credentials: str  | None = None # Token or Key
    usergroup: str  | None = None # Group of the user

class BaseTaskSendParams(TaskSendParams):
    # iss : str # Sender Agent
    # aud : str # Receiver Agent
    authentication: authenticationConfig
    document: Optional[DocumentMetadata] = None  # Document metadata for file processing


class TokenRequest(BaseModel):
    sender_agent: str
    token: str