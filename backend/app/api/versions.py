"""Version management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import rate_limiter
from app.models.workflow import User, Workflow, WorkflowVersion
from app.schemas.workflow import (
    WorkflowVersionCreate,
    WorkflowVersionResponse,
    WorkflowVersionDiff,
)

router = APIRouter()


def _get_next_version_number(db: Session, workflow_id: int) -> int:
    """Get next version number with row-level lock to prevent race conditions."""
    last_version = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
        .with_for_update()
        .first()
    )
    return (last_version.version + 1) if last_version else 1


@router.get("/workflows/{workflow_id}/versions", response_model=List[WorkflowVersionResponse])
def list_versions(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all versions of a workflow."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    versions = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
        .all()
    )
    return versions


@router.post("/workflows/{workflow_id}/versions", response_model=WorkflowVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    workflow_id: int,
    version_data: WorkflowVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new version of a workflow."""
    # Rate limit check
    rate_key = f"{current_user.id}:version_create"
    if not rate_limiter.is_allowed(rate_key, limit=20, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Get next version number with lock
    next_version = _get_next_version_number(db, workflow_id)

    # Create version
    workflow_version = WorkflowVersion(
        workflow_id=workflow_id,
        version=next_version,
        definition=workflow.definition,
        change_summary=version_data.change_summary,
        created_by=current_user.id,
    )
    db.add(workflow_version)

    # Update workflow version number
    workflow.version = next_version
    db.commit()
    db.refresh(workflow_version)

    return workflow_version


@router.get("/workflows/{workflow_id}/versions/{version}", response_model=WorkflowVersionResponse)
def get_version(
    workflow_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific version of a workflow."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    workflow_version = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id, WorkflowVersion.version == version)
        .first()
    )
    if not workflow_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    return workflow_version


@router.post("/workflows/{workflow_id}/versions/{version}/rollback", response_model=WorkflowVersionResponse)
def rollback_version(
    workflow_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rollback workflow to a specific version."""
    # Rate limit check
    rate_key = f"{current_user.id}:version_rollback"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    workflow_version = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id, WorkflowVersion.version == version)
        .first()
    )
    if not workflow_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    # Restore definition
    workflow.definition = workflow_version.definition

    # Create new version for rollback with lock
    next_version = _get_next_version_number(db, workflow_id)

    rollback_version = WorkflowVersion(
        workflow_id=workflow_id,
        version=next_version,
        definition=workflow_version.definition,
        change_summary=f"Rollback to version {version}",
        created_by=current_user.id,
    )
    db.add(rollback_version)

    workflow.version = next_version
    db.commit()
    db.refresh(rollback_version)

    return rollback_version


@router.get("/workflows/{workflow_id}/versions/diff", response_model=WorkflowVersionDiff)
def diff_versions(
    workflow_id: int,
    version_a: int,
    version_b: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare two versions of a workflow."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    ver_a = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id, WorkflowVersion.version == version_a)
        .first()
    )
    ver_b = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id, WorkflowVersion.version == version_b)
        .first()
    )

    if not ver_a or not ver_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    # Compare definitions with error handling
    try:
        def_a = ver_a.definition or {"nodes": [], "edges": []}
        def_b = ver_b.definition or {"nodes": [], "edges": []}

        nodes_a = {n["id"]: n for n in def_a.get("nodes", []) if isinstance(n, dict) and "id" in n}
        nodes_b = {n["id"]: n for n in def_b.get("nodes", []) if isinstance(n, dict) and "id" in n}

        edges_a = {e["id"]: e for e in def_a.get("edges", []) if isinstance(e, dict) and "id" in e}
        edges_b = {e["id"]: e for e in def_b.get("edges", []) if isinstance(e, dict) and "id" in e}
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow definition structure: {str(e)}",
        )

    added_nodes = [nid for nid in nodes_b if nid not in nodes_a]
    removed_nodes = [nid for nid in nodes_a if nid not in nodes_b]
    modified_nodes = [
        nid for nid in nodes_a
        if nid in nodes_b and nodes_a[nid] != nodes_b[nid]
    ]

    added_edges = [eid for eid in edges_b if eid not in edges_a]
    removed_edges = [eid for eid in edges_a if eid not in edges_b]

    return WorkflowVersionDiff(
        version_a=ver_a,
        version_b=ver_b,
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        modified_nodes=modified_nodes,
        added_edges=added_edges,
        removed_edges=removed_edges,
    )
