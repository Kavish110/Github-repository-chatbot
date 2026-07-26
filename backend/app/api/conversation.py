from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.conversation_service import conversation_service
from app.services.repository_service import repository_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationCreateRequest(BaseModel):
    title: str | None = None
    repository_id: str | None = None
    folder_id: str | None = None
    repo_id: str | None = None
    message: str | None = None


class ConversationUpdateRequest(BaseModel):
    title: str | None = None
    repository_id: str | None = None
    folder_id: str | None = None


@router.get("")
def list_conversations() -> dict:
    return {"conversations": conversation_service.list_conversations()}


@router.post("")
def create_conversation(payload: ConversationCreateRequest) -> dict:
    if payload.message:
        repo_id = payload.repo_id or payload.repository_id
        if not repo_id:
            return {"repo_id": None, "history": []}

        repo = repository_service.get_repository(repo_id)
        if not repo:
            return {"repo_id": repo_id, "history": []}

        history = repo.setdefault("conversation_history", [])
        history.append({"role": "user", "message": payload.message})
        response = repository_service.chat(repo_id, payload.message)
        if response:
            history.append({"role": "assistant", "message": response["answer"]})
        return {"repo_id": repo_id, "history": history}

    return conversation_service.create_conversation(payload.title or "New conversation", payload.repository_id, payload.folder_id)


@router.patch("/{conversation_id}")
def update_conversation(conversation_id: str, payload: ConversationUpdateRequest) -> dict:
    updated = conversation_service.update_conversation(conversation_id, **payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str) -> dict:
    deleted = conversation_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "conversation_id": conversation_id}
