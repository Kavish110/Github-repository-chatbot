from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.parser_service import ParserService
import requests
import subprocess
import json

OLLAMA_DEFAULT_HOST = "http://localhost:11434"


class LLMProvider:
    def __init__(self, provider: str | None = None, api_key: str | None = None) -> None:
        self.provider_raw = (provider or os.getenv("LLM_PROVIDER", "openai")).strip()
        self.provider = self._normalize_provider(self.provider_raw)
        self.model = self._extract_model_name(self.provider_raw)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")

    def _normalize_provider(self, provider: str | None) -> str:
        if not provider:
            return "openai"
        normalized = provider.strip().lower()
        if normalized.startswith("ollama:") or normalized == "ollama":
            return "ollama"
        # Treat bare model:tag patterns (e.g. "gemma:3b") as Ollama models
        if ":" in normalized and not normalized.startswith(("gemma3", "qwen", "gemini", "openai")):
            return "ollama"
        if normalized.startswith("gemma3"):
            return "gemma3"
        if normalized.startswith("qwen"):
            return "qwen"
        if normalized.startswith("gemini"):
            return "gemini"
        if normalized.startswith("openai"):
            return "openai"
        return normalized

    def _extract_model_name(self, provider: str | None) -> str | None:
        if not provider:
            return None
        normalized = provider.strip().lower()
        # "ollama:gemma:3b" → "gemma:3b"
        if normalized.startswith("ollama:"):
            remainder = normalized[len("ollama:"):]
            return remainder if remainder else "gemma:3b"
        if ":" in normalized:
            return normalized
        if normalized.startswith("gemma3"):
            return "gemma3:12b"
        if normalized.startswith("qwen"):
            return "qwen2.5-coder:14b"
        if normalized == "ollama":
            return "gemma:3b"
        return None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if self.provider == "ollama":
            return self._call_ollama(prompt, system_prompt)
        if self.provider == "gemini":
            return self._call_gemini(prompt, system_prompt)
        if self.provider == "gemma3":
            return self._call_gemma3(prompt, system_prompt)
        if self.provider == "qwen":
            return self._call_qwen(prompt, system_prompt)
        return self._call_openai(prompt, system_prompt)

    def _call_openai(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            import openai
        except Exception:
            return ""

        client = openai.OpenAI(api_key=self.api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = client.responses.create(model="gpt-4o-mini", input=messages)
        return getattr(response, "output_text", "") or ""

    def _call_gemini(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            import google.generativeai as genai
        except Exception:
            return ""

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        return getattr(response, "text", "") or ""

    def _call_ollama(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call a locally running Ollama instance via its REST API."""
        host = os.getenv("OLLAMA_HOST", OLLAMA_DEFAULT_HOST).rstrip("/")
        model = self.model or "gemma:3b"
        url = f"{host}/api/generate"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            resp = requests.post(url, json=payload, timeout=120)
            if resp.ok:
                data = resp.json()
                return data.get("response", "").strip()
            return f"Ollama request failed ({resp.status_code}): {resp.text[:200]}"
        except requests.ConnectionError:
            return (
                f"Could not connect to Ollama at {host}. "
                "Make sure Ollama is running (try: ollama serve) and the model is pulled (try: ollama pull " + model + ")."
            )
        except Exception as exc:
            return f"Ollama request error: {exc}"

    def _extract_model_text(self, data: Any) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            if text := data.get("text"):
                return text
            if output := data.get("output"):
                return output
            if result := data.get("result"):
                return result
            if generations := data.get("generations"):
                if isinstance(generations, list) and generations:
                    first = generations[0]
                    if isinstance(first, dict):
                        return self._extract_model_text(first)
            if choices := data.get("choices"):
                if isinstance(choices, list) and choices:
                    first = choices[0]
                    return self._extract_model_text(first)
            if content := data.get("content"):
                return self._extract_model_text(content)
            if output := data.get("outputs"):
                if isinstance(output, list) and output:
                    return self._extract_model_text(output[0])
        return ""

    def _call_gemma3(self, prompt: str, system_prompt: str | None = None) -> str:
        url = os.getenv("GEMMA3_URL") or os.getenv("GEMMA3_SERVER_URL")
        cmd = os.getenv("GEMMA3_CMD")
        model = self.model or os.getenv("GEMMA3_MODEL", "gemma3:12b")
        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        payload = {
            "prompt": full_prompt,
            "input": full_prompt,
            "model": model,
        }
        if url:
            try:
                resp = requests.post(url, json=payload, timeout=30)
                if resp.ok:
                    return self._extract_model_text(resp.json())
                return f"gemma3 request failed: {resp.status_code} {resp.text}"
            except Exception as exc:
                return f"gemma3 request error: {exc}"
        if cmd:
            try:
                cmd_args = cmd.split()
                if "{model}" in cmd:
                    cmd_args = cmd.format(model=model).split()
                p = subprocess.Popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = p.communicate(full_prompt.encode("utf-8"), timeout=60)
                if out:
                    return out.decode("utf-8").strip()
                if err:
                    err_text = err.decode("utf-8").strip()
                    if err_text:
                        return f"gemma3 subprocess error: {err_text}"
            except Exception as exc:
                return f"gemma3 subprocess error: {exc}"
        # Fall back to Ollama if available
        return self._call_ollama(prompt, system_prompt)

    def _call_qwen(self, prompt: str, system_prompt: str | None = None) -> str:
        url = os.getenv("QWEN12B_URL") or os.getenv("QWEN_URL")
        cmd = os.getenv("QWEN12B_CMD") or os.getenv("QWEN_CMD")
        model = self.model or os.getenv("QWEN_MODEL", "qwen2.5-coder:14b")
        full_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        payload = {
            "prompt": full_prompt,
            "input": full_prompt,
            "model": model,
        }
        if url:
            try:
                resp = requests.post(url, json=payload, timeout=30)
                if resp.ok:
                    return self._extract_model_text(resp.json())
                return f"qwen request failed: {resp.status_code} {resp.text}"
            except Exception as exc:
                return f"qwen request error: {exc}"
        if cmd:
            try:
                cmd_args = cmd.split()
                if "{model}" in cmd:
                    cmd_args = cmd.format(model=model).split()
                p = subprocess.Popen(cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = p.communicate(full_prompt.encode("utf-8"), timeout=60)
                if out:
                    return out.decode("utf-8").strip()
                if err:
                    err_text = err.decode("utf-8").strip()
                    if err_text:
                        return f"qwen subprocess error: {err_text}"
            except Exception as exc:
                return f"qwen subprocess error: {exc}"
        # Fall back to Ollama if available
        return self._call_ollama(prompt, system_prompt)


class RepositoryService:
    def __init__(self) -> None:
        self._repositories: dict[str, dict[str, Any]] = {}
        self._parser = ParserService()
        self._llm = LLMProvider()

    def import_repository(self, repo_url: str | None = None, source_path: str | None = None, repo_path: str | None = None) -> dict[str, Any]:
        if repo_path:
            repo_dir = Path(repo_path).expanduser().resolve()
            if not repo_dir.exists() or not repo_dir.is_dir():
                raise FileNotFoundError(f"Local repository not found: {repo_path}")
            repo_id = self._slugify(repo_dir.name)
        else:
            repo_id = self._slugify(repo_url or "repository")
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

        self._repositories[repo_id] = {
            "id": repo_id,
            "repo_url": repo_url,
            "source_path": str(repo_dir),
            "files": [],
            "summary": "",
            "architecture": {},
            "conversation_history": [],
            "status": "indexing",
        }

        index = self._parser.index_repository(repo_dir)
        self._repositories[repo_id].update(
            {
                "files": index["files"],
                "summary": index["summary"],
                "architecture": self._build_architecture(index["files"]),
                "status": "indexed",
            }
        )

        return {"repo_id": repo_id, "status": "indexed", "summary": index["summary"]}

    def list_repositories(self) -> list[dict[str, Any]]:
        return [
            {
                "id": repo["id"],
                "name": Path(repo["source_path"]).name,
                "repo_url": repo["repo_url"],
                "source_path": repo["source_path"],
                "summary": repo["summary"],
                "status": repo.get("status", "indexed"),
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

    def chat(self, repo_id: str, question: str, conversation_history: list[dict[str, Any]] | None = None, api_key: str | None = None, llm_provider: str | None = None) -> dict[str, Any] | None:
        repo = self._repositories.get(repo_id)
        if not repo:
            alternate_repo_id = self._slugify(repo_id)
            repo = self._repositories.get(alternate_repo_id)
        if not repo:
            return None

        files = repo["files"]
        ranked = self._rank_files(files, question)
        context = [entry for entry in ranked[:3]]
        answer = self._generate_answer(question, context, conversation_history)
        llm = getattr(self, "_llm", None)
        use_llm = False
        if api_key:
            use_llm = True
        elif llm_provider:
            normalized_provider = llm_provider.strip().lower()
            # Ollama models run locally — no API key needed
            if normalized_provider.startswith("ollama") or (
                ":" in normalized_provider
                and not normalized_provider.startswith(("gemma3", "qwen", "gemini", "openai"))
            ):
                use_llm = True
            elif normalized_provider.startswith("gemma3") or normalized_provider.startswith("qwen"):
                use_llm = True
            elif normalized_provider == "gemini" and api_key:
                use_llm = True
            elif normalized_provider == "openai" and api_key:
                use_llm = True
        elif llm is not None and not isinstance(llm, LLMProvider):
            use_llm = True
        elif isinstance(llm, LLMProvider):
            if llm.provider == "ollama":
                use_llm = True
            elif llm.provider in {"gemma3", "qwen"}:
                use_llm = True
            elif llm.provider in {"gemini", "openai"}:
                use_llm = bool(llm.api_key)

        if use_llm:
            llm_answer = self._generate_llm_answer(question, context, conversation_history, api_key=api_key, llm_provider=llm_provider)
            if llm_answer:
                answer = llm_answer
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

    def _generate_answer(self, question: str, context: list[dict[str, Any]], conversation_history: list[dict[str, Any]] | None = None) -> str:
        normalized_question = question.lower().strip()
        answer = "Based on the repository contents, I can provide the following summary:\n"

        prior_user_messages = []
        if conversation_history:
            for entry in conversation_history:
                if entry.get("role") == "user":
                    content = entry.get("content") or entry.get("message")
                    if content:
                        prior_user_messages.append(content)

        if any(word in normalized_question for word in ["hello", "hi", "hey", "how are you", "what can you do"]):
            if prior_user_messages:
                last_topic = prior_user_messages[-1]
                answer += f"Thanks for checking in. I can continue helping with '{last_topic}' or explore a new repository question."
            else:
                answer += "I can help you explore the repository, explain its structure, and point you to relevant files."
        elif any(word in normalized_question for word in ["explain", "describe", "overview", "what is this repo", "what does this repo"]):
            answer += "This repository appears to be a small application with auth, database, and service modules that work together as a simple layered app."
        elif any(word in normalized_question for word in ["auth", "login", "password", "token"]):
            if any("auth" in entry["path"].lower() for entry in context):
                answer += "Authentication logic appears in the auth module and is a good place to start for login behavior."
            else:
                answer += "Authentication logic was not found in the indexed files."
        elif any(word in normalized_question for word in ["architecture", "structure", "overview"]):
            answer += "The repository follows a simple layered structure with app modules, a database helper, and a service layer."
        elif any(word in normalized_question for word in ["database", "db", "connection"]):
            answer += "Database access is exposed through the database helper module."
        elif any(word in normalized_question for word in ["service", "workflow", "run"]):
            answer += "The service layer wires together the app modules and exposes the main execution flow."
        elif any(word in normalized_question for word in ["readme", "documentation", "docs"]):
            answer += "Documentation can be generated from the indexed repository files and will summarize the key modules."
        else:
            if prior_user_messages:
                last_topic = prior_user_messages[-1]
                answer += f"Following up on your earlier note about '{last_topic}', I can help you dig deeper into the repository."
            else:
                answer += f"I can help you understand the repository around '{question}' by inspecting the indexed files and relevant modules."

        if context:
            answer += "\nRelevant files:\n"
            for entry in context:
                answer += f"- {entry['path']}\n"
        return answer

    def _generate_llm_answer(self, question: str, context: list[dict[str, Any]], conversation_history: list[dict[str, Any]] | None = None, api_key: str | None = None, llm_provider: str | None = None) -> str:
        if llm_provider:
            llm = LLMProvider(provider=llm_provider, api_key=api_key)
        else:
            llm = self._llm
        if not llm:
            return ""

        context_summary = "\n".join(f"- {entry['path']}: {entry.get('content', '')[:400]}" for entry in context)
        history_summary = ""
        if conversation_history:
            history_summary = "\n".join(
                f"{entry.get('role', 'user')}: {entry.get('content') or entry.get('message', '')}" for entry in conversation_history[-4:]
            )

        prompt = (
            f"User question: {question}\n"
            f"Repository context:\n{context_summary or 'No relevant files found.'}\n"
            f"Conversation history:\n{history_summary or 'No prior messages.'}"
        )
        system_prompt = "You are RepoGPT, a helpful repository assistant. Answer the user's question clearly and concisely using the provided repository context."
        return llm.generate(prompt, system_prompt=system_prompt).strip()

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
