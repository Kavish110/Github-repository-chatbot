from __future__ import annotations

from typing import Any


class FolderService:
    def __init__(self) -> None:
        self._folders: dict[str, dict[str, Any]] = {}
        self._next_folder_id = 1

    def list_folders(self) -> list[dict[str, Any]]:
        return sorted(self._folders.values(), key=lambda item: item["name"])

    def create_folder(self, name: str, color: str = "blue") -> dict[str, Any]:
        folder_id = f"folder-{self._next_folder_id}"
        self._next_folder_id += 1
        folder = {
            "id": folder_id,
            "name": name,
            "color": color,
            "created_at": "2026-07-26T00:00:00Z",
        }
        self._folders[folder_id] = folder
        return folder

    def update_folder(self, folder_id: str, **updates: Any) -> dict[str, Any] | None:
        folder = self._folders.get(folder_id)
        if not folder:
            return None
        folder.update(updates)
        return folder

    def delete_folder(self, folder_id: str) -> bool:
        if folder_id in self._folders:
            del self._folders[folder_id]
            return True
        return False


folder_service = FolderService()
