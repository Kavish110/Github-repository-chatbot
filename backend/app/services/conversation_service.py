from __future__ import annotations

from typing import Any


class ConversationService:
    def __init__(self) -> None:
        self._conversations: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}
        self._next_conversation_id = 1
        self._next_message_id = 1

    def list_conversations(self) -> list[dict[str, Any]]:
        return sorted(self._conversations.values(), key=lambda item: item["created_at"], reverse=True)

    def create_conversation(self, title: str, repository_id: str | None = None, folder_id: str | None = None) -> dict[str, Any]:
        conversation_id = f"conv-{self._next_conversation_id}"
        self._next_conversation_id += 1
        conversation = {
            "id": conversation_id,
            "title": title or "New conversation",
            "repository_id": repository_id,
            "folder_id": folder_id,
            "created_at": self._timestamp(),
            "updated_at": self._timestamp(),
        }
        self._conversations[conversation_id] = conversation
        self._messages[conversation_id] = []
        return conversation

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        return self._conversations.get(conversation_id)

    def update_conversation(self, conversation_id: str, **updates: Any) -> dict[str, Any] | None:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        conversation.update(updates)
        conversation["updated_at"] = self._timestamp()
        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self._messages.pop(conversation_id, None)
            return True
        return False

    def add_message(self, conversation_id: str, role: str, content: str, citations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        message = {
            "id": f"msg-{self._next_message_id}",
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "citations": citations or [],
            "timestamp": self._timestamp(),
        }
        self._next_message_id += 1
        self._messages.setdefault(conversation_id, []).append(message)
        if conversation_id in self._conversations:
            self._conversations[conversation_id]["updated_at"] = self._timestamp()
        return message

    def get_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self._messages.get(conversation_id, []))

    def _timestamp(self) -> str:
        return "2026-07-26T00:00:00Z"


conversation_service = ConversationService()
