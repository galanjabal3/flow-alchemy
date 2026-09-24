from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    plan = Column(String(50), default="free")
    api_key_hash = Column(String(255), unique=True)
    api_key_prefix = Column(String(20))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workflows = relationship("Workflow", back_populates="user")
    executions = relationship("Execution", back_populates="user")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    definition = Column(JSON, nullable=False)
    compiled_code = Column(Text)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    schedule = Column(String(100))
    webhook_key = Column(String(255), unique=True, nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="workflows")
    nodes = relationship("WorkflowNode", back_populates="workflow")
    edges = relationship("WorkflowEdge", back_populates="workflow")
    executions = relationship("Execution", back_populates="workflow")
    versions = relationship("WorkflowVersion", back_populates="workflow", order_by="WorkflowVersion.version.desc()")


class NodeDefinition(Base):
    __tablename__ = "node_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_type = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=False)
    icon = Column(String(50))
    category = Column(String(100), nullable=False)
    is_premium = Column(Boolean, default=False)


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    node_definition_id = Column(Integer, ForeignKey("node_definitions.id"), nullable=False)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workflow = relationship("Workflow", back_populates="nodes")
    node_definition = relationship("NodeDefinition")


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    source_node_id = Column(Integer, ForeignKey("workflow_nodes.id"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("workflow_nodes.id"), nullable=False)
    condition = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workflow = relationship("Workflow", back_populates="edges")
    source_node = relationship("WorkflowNode", foreign_keys=[source_node_id])
    target_node = relationship("WorkflowNode", foreign_keys=[target_node_id])


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="pending")
    trigger = Column(String(50), nullable=False)
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_log = Column(Text)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Snapshot: immutable workflow definition at time of execution
    definition_snapshot = Column(JSON, nullable=True)

    # Async runtime fields
    idempotency_key = Column(String(255), unique=True, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    worker_id = Column(String(100), nullable=True)
    queued_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("Workflow", back_populates="executions")
    user = relationship("User", back_populates="executions")
    node_executions = relationship("NodeExecution", back_populates="execution")


class NodeExecution(Base):
    __tablename__ = "node_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    # node_id references workflow_nodes.id when the workflow has a relational
    # node row (seeded demo workflows). Other workflows store runtime
    # per-node history via node_ref (React Flow node id) instead.
    node_id = Column(Integer, ForeignKey("workflow_nodes.id"), nullable=True)
    node_ref = Column(String(100), nullable=True)
    node_type = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_log = Column(Text)
    duration_ms = Column(Integer)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True))

    execution = relationship("Execution", back_populates="node_executions")
    node = relationship("WorkflowNode")


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    version = Column(Integer, nullable=False)
    definition = Column(JSON, nullable=False)
    change_summary = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    workflow = relationship("Workflow", back_populates="versions")
    creator = relationship("User")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    credential_type = Column(String(50), nullable=False)
    encrypted_value = Column(Text, nullable=False)
    encryption_version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="credentials")


# Add credentials relationship to User
User.credentials = relationship("Credential", back_populates="user")
