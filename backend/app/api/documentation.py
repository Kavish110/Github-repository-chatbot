from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.repository_service import repository_service

router = APIRouter(prefix="/docs", tags=["documentation"])


class DocumentationRequest(BaseModel):
    repo_id: str


@router.post("/project")
def generate_project_docs(payload: DocumentationRequest) -> dict:
    docs = repository_service.generate_documentation(payload.repo_id)
    if not docs:
        raise HTTPException(status_code=404, detail="Repository not found")
    return docs


@router.post("/function")
def generate_function_docs(payload: DocumentationRequest) -> dict:
    docs = repository_service.generate_documentation(payload.repo_id)
    if not docs:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repo_id": payload.repo_id, "function_docs": docs["function_docs"]}


@router.post("/class")
def generate_class_docs(payload: DocumentationRequest) -> dict:
    docs = repository_service.generate_documentation(payload.repo_id)
    if not docs:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repo_id": payload.repo_id, "class_docs": docs["class_docs"]}
