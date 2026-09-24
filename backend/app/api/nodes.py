from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.workflow import NodeDefinition
from app.schemas.workflow import NodeDefinitionResponse

router = APIRouter()


@router.get("/", response_model=List[NodeDefinitionResponse])
def list_node_definitions(db: Session = Depends(get_db)):
    return db.query(NodeDefinition).all()


@router.get("/{node_type}", response_model=NodeDefinitionResponse)
def get_node_definition(node_type: str, db: Session = Depends(get_db)):
    node_def = db.query(NodeDefinition).filter(NodeDefinition.node_type == node_type).first()
    if not node_def:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node type '{node_type}' not found",
        )
    return node_def
