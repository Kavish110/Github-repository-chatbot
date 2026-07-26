from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.repository_service import repository_service

router = APIRouter(prefix="/repositories", tags=["repositories"])


class ImportRepositoryRequest(BaseModel):
    repo_url: str
    source_path: Optional[str] = None


@router.get("")
def list_repositories() -> dict:
    repositories = repository_service.list_repositories()
    return {"repositories": repositories}


@router.post("/import")
def import_repository(payload: ImportRepositoryRequest) -> dict:
    return repository_service.import_repository(payload.repo_url, payload.source_path)


@router.get("/{repo_id}")
def get_repository(repo_id: str) -> dict:
    repository = repository_service.get_repository(repo_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repository


@router.delete("/{repo_id}")
def delete_repository(repo_id: str) -> dict:
    deleted = repository_service.delete_repository(repo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"deleted": True, "repo_id": repo_id}
