from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.folder_service import folder_service

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderCreateRequest(BaseModel):
    name: str
    color: str | None = None


class FolderUpdateRequest(BaseModel):
    name: str | None = None
    color: str | None = None


@router.get("")
def list_folders() -> dict:
    return {"folders": folder_service.list_folders()}


@router.post("")
def create_folder(payload: FolderCreateRequest) -> dict:
    return folder_service.create_folder(payload.name, payload.color or "blue")


@router.patch("/{folder_id}")
def update_folder(folder_id: str, payload: FolderUpdateRequest) -> dict:
    updated = folder_service.update_folder(folder_id, **payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Folder not found")
    return updated


@router.delete("/{folder_id}")
def delete_folder(folder_id: str) -> dict:
    deleted = folder_service.delete_folder(folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"deleted": True, "folder_id": folder_id}
