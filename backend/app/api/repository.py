from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.repository_service import repository_service

router = APIRouter(prefix="/repositories", tags=["repositories"])


class ImportRepositoryRequest(BaseModel):
    source: Optional[str] = None
    value: Optional[str] = None
    repo_url: Optional[str] = None
    repo_path: Optional[str] = None
    source_path: Optional[str] = None


@router.get("")
def list_repositories() -> dict:
    repositories = repository_service.list_repositories()
    return {"repositories": repositories}


@router.post("/import")
def import_repository(payload: ImportRepositoryRequest) -> dict:
    repo_url = payload.repo_url
    repo_path = payload.repo_path
    source_path = payload.source_path

    if payload.source and payload.value:
        if payload.source.lower() == "github":
            repo_url = payload.value
        elif payload.source.lower() == "local":
            repo_path = payload.value
        else:
            raise HTTPException(status_code=400, detail="Invalid source; use 'github' or 'local'.")

    if not repo_url and not repo_path:
        raise HTTPException(status_code=400, detail="Either repo_url or repo_path must be provided.")

    try:
        return repository_service.import_repository(repo_url, source_path, repo_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


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
