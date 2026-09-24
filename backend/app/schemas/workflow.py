from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.api.auth import validate_password_strength
        errors = validate_password_strength(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    plan: str
    api_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from app.api.auth import validate_password_strength
        errors = validate_password_strength(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    definition: dict


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[dict] = None
    schedule: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    definition: dict
    compiled_code: Optional[str]
    version: int
    is_active: bool
    schedule: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NodeDefinitionResponse(BaseModel):
    id: int
    node_type: str
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    icon: Optional[str]
    category: str
    is_premium: bool

    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    status: str
    trigger: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_log: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyResponse(BaseModel):
    id: int
    email: str
    plan: str
    api_key: str
    created_at: datetime
    message: str

    class Config:
        from_attributes = True


class WorkflowRunRequest(BaseModel):
    input_data: Optional[dict] = None
    idempotency_key: Optional[str] = Field(None, max_length=255)


class ExecutionHistoryResponse(BaseModel):
    id: int
    workflow_id: int
    status: str
    trigger: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_log: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExecutionNodeDetailResponse(BaseModel):
    id: int
    execution_id: int
    node_ref: Optional[str] = None
    node_type: Optional[str] = None
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_log: Optional[str]
    duration_ms: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WorkflowVersionCreate(BaseModel):
    change_summary: Optional[str] = Field(None, max_length=500)


class WorkflowVersionResponse(BaseModel):
    id: int
    workflow_id: int
    version: int
    definition: dict
    change_summary: Optional[str]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowVersionDiff(BaseModel):
    version_a: WorkflowVersionResponse
    version_b: WorkflowVersionResponse
    added_nodes: List[str]
    removed_nodes: List[str]
    modified_nodes: List[str]
    added_edges: List[str]
    removed_edges: List[str]
