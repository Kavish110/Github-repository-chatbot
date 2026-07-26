from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.conversation_service import conversation_service
from app.services.repository_service import repository_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    repo_id: str
    question: str
    conversation_id: str | None = None


@router.post("")
def chat(payload: ChatRequest) -> dict:
    result = repository_service.chat(payload.repo_id, payload.question)
    if not result:
        raise HTTPException(status_code=404, detail="Repository not found")

    conversation_id = payload.conversation_id
    if conversation_id:
        conversation = conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_service.add_message(conversation_id, "user", payload.question)
        conversation_service.add_message(conversation_id, "assistant", result["answer"], result.get("citations", []))
        result["conversation_id"] = conversation_id

    return result
