"""Compiler endpoints for workflow export."""

import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.compiler import PythonCompiler
from app.core.workflow_definition import WorkflowDefinition
from app.models.workflow import User, Workflow

router = APIRouter()

compiler = PythonCompiler()


def _sanitize_filename(name: str) -> str:
    """Sanitize filename for Content-Disposition header."""
    return re.sub(r'[^\w\-.]', '_', name)[:100]


@router.post("/workflows/{workflow_id}/compile")
def compile_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compile workflow to Python code."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    try:
        definition = WorkflowDefinition(**workflow.definition)
        code = compiler.compile(definition, workflow.name)
        return {"code": code, "workflow_name": workflow.name}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compile workflow. Please check your workflow definition.",
        )


@router.get("/workflows/{workflow_id}/export")
def export_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export workflow as downloadable Python file."""
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    try:
        definition = WorkflowDefinition(**workflow.definition)
        code = compiler.compile(definition, workflow.name)

        filename = _sanitize_filename(workflow.name) + ".py"
        return Response(
            content=code,
            media_type="text/x-python",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export workflow. Please check your workflow definition.",
        )
