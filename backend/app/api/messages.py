from fastapi import APIRouter, HTTPException

from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/{conversation_id}")
def list_messages(conversation_id: str) -> dict:
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "messages": conversation_service.get_messages(conversation_id)}
