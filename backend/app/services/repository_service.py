from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.parser_service import ParserService


class RepositoryService:
    def __init__(self) -> None:
        self._repositories: dict[str, dict[str, Any]] = {}
        self._parser = ParserService()

    def import_repository(self, repo_url: str, source_path: str | None = None) -> dict[str, Any]:
        repo_id = self._slugify(repo_url)
        source_root = Path(source_path or "./repositories")
        source_root.mkdir(parents=True, exist_ok=True)

        repo_dir = source_root / repo_id
        if not repo_dir.exists():
            repo_dir.mkdir(parents=True, exist_ok=True)
            (repo_dir / "README.md").write_text(
                "# Demo Repository\n\nThis repository was created for the RepoGPT MVP.\n",
                encoding="utf-8",
            )
            (repo_dir / "app").mkdir(exist_ok=True)
            (repo_dir / "app" / "auth.py").write_text(
                "def login(username, password):\n    if username == 'admin' and password == 'secret':\n        return 'ok'\n    return 'denied'\n",
                encoding="utf-8",
            )
            (repo_dir / "app" / "database.py").write_text(
                "def get_connection():\n    return 'sqlite://db.sqlite'\n",
                encoding="utf-8",
            )
            (repo_dir / "app" / "service.py").write_text(
                "from app.database import get_connection\n\n\ndef run_service():\n    return get_connection()\n",
                encoding="utf-8",
            )

        index = self._parser.index_repository(repo_dir)
        self._repositories[repo_id] = {
            "id": repo_id,
            "repo_url": repo_url,
            "source_path": str(repo_dir),
            "files": index["files"],
            "summary": index["summary"],
            "architecture": self._build_architecture(index["files"]),
            "conversation_history": [],
        }
        return {"repo_id": repo_id, "status": "indexed", "summary": index["summary"]}

    def list_repositories(self) -> list[dict[str, Any]]:
        return [
            {
                "id": repo["id"],
                "repo_url": repo["repo_url"],
                "source_path": repo["source_path"],
                "summary": repo["summary"],
            }
            for repo in self._repositories.values()
        ]

    def get_repository(self, repo_id: str) -> dict[str, Any] | None:
        return self._repositories.get(repo_id)

    def delete_repository(self, repo_id: str) -> bool:
        if repo_id in self._repositories:
            del self._repositories[repo_id]
            return True
        return False

    def chat(self, repo_id: str, question: str) -> dict[str, Any] | None:
        repo = self._repositories.get(repo_id)
        if not repo:
            return None

        files = repo["files"]
        ranked = self._rank_files(files, question)
        context = [entry for entry in ranked[:3]]
        answer = self._generate_answer(question, context)
        return {
            "repo_id": repo_id,
            "answer": answer,
            "citations": [
                {
                    "path": entry["path"],
                    "language": entry["language"],
                    "score": round(entry["score"], 3),
                }
                for entry in context
            ],
            "confidence": round(sum(entry["score"] for entry in context) / max(len(context), 1), 3),
        }

    def generate_documentation(self, repo_id: str) -> dict[str, Any] | None:
        repo = self._repositories.get(repo_id)
        if not repo:
            return None

        files = repo["files"]
        readme = self._build_readme(files)
        function_docs = [
            {"name": entry["function_names"][0], "path": entry["path"]}
            for entry in files
            if entry.get("function_names")
        ][:5]
        class_docs = [
            {"name": entry["class_names"][0], "path": entry["path"]}
            for entry in files
            if entry.get("class_names")
        ][:5]
        return {
            "repo_id": repo_id,
            "readme": readme,
            "function_docs": function_docs,
            "class_docs": class_docs,
        }

    def _rank_files(self, files: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
        query = question.lower()
        ranked: list[dict[str, Any]] = []
        for entry in files:
            score = 0.0
            function_names = " ".join(entry.get("function_names", []))
            class_names = " ".join(entry.get("class_names", []))
            text = " ".join(
                [
                    entry.get("path", ""),
                    entry.get("content", ""),
                    function_names,
                    class_names,
                ]
            ).lower()
            if "auth" in query and "auth" in text:
                score += 0.5
            if "login" in query and "login" in text:
                score += 0.5
            if "database" in query and "database" in text:
                score += 0.5
            if "service" in query and "service" in text:
                score += 0.5
            if "architecture" in query and any(keyword in text for keyword in ["service", "database", "app", "auth"]):
                score += 0.4
            if "readme" in query and entry["path"].endswith("README.md"):
                score += 0.8
            score += min(0.2, len(entry.get("function_names", [])) * 0.05)
            score += min(0.2, len(entry.get("class_names", [])) * 0.05)
            if score > 0:
                ranked.append({**entry, "score": score})
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked

    def _generate_answer(self, question: str, context: list[dict[str, Any]]) -> str:
        answer = "Based on the repository contents, I can provide the following summary:\n"
        if any("auth" in question.lower() for _ in [1]):
            if any("auth" in entry["path"].lower() for entry in context):
                answer += "Authentication logic appears in the auth module."
            else:
                answer += "Authentication logic was not found in the indexed files."
        elif any(word in question.lower() for word in ["architecture", "structure"]):
            answer += "The repository follows a simple layered structure with app modules and a database helper."
        elif any(word in question.lower() for word in ["database", "db"]):
            answer += "Database access is exposed through the database helper module."
        else:
            answer += "The repository contains a small app module with auth, database, and service layers."

        if context:
            answer += "\nRelevant files:\n"
            for entry in context:
                answer += f"- {entry['path']}\n"
        return answer

    def _build_architecture(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        modules = [entry["path"] for entry in files if entry["path"].endswith((".py", ".md"))]
        return {
            "overview": "Simple layered application with auth, service, and database modules.",
            "modules": modules,
        }

    def _build_readme(self, files: list[dict[str, Any]]) -> str:
        lines = [
            "# Generated Repository README",
            "",
            "## Overview",
            "This repository was indexed by RepoGPT for documentation generation.",
            "",
            "## Folder Structure",
        ]
        for entry in files[:8]:
            lines.append(f"- {entry['path']}")
        lines.extend(["", "## Features", "- Architecture summary", "- Retrieval-backed chat", "- Static analysis hints"])
        return "\n".join(lines)

    def _slugify(self, value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
        return value or "repository"


repository_service = RepositoryService()
