from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class ParserService:
    def index_repository(self, repo_dir: Path) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for path in sorted(repo_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(part in {".git", "node_modules", "__pycache__", "dist", "build", ".venv"} for part in path.parts):
                continue
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".pyc"}:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            language = self._detect_language(path)
            function_names, class_names = self._extract_symbols(content, language)
            files.append(
                {
                    "path": str(path.relative_to(repo_dir)),
                    "language": language,
                    "content": content,
                    "function_names": function_names,
                    "class_names": class_names,
                }
            )

        summary = {
            "file_count": len(files),
            "languages": sorted({entry["language"] for entry in files}),
            "top_files": [entry["path"] for entry in files[:5]],
        }
        return {"files": files, "summary": summary}

    def _detect_language(self, path: Path) -> str:
        suffix = path.suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".rs": "rust",
            ".md": "markdown",
        }
        return mapping.get(suffix, "text")

    def _extract_symbols(self, content: str, language: str) -> tuple[list[str], list[str]]:
        if language == "python":
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return [], []
            functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
            return functions, classes
        return [], []
