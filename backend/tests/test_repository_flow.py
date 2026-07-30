from fastapi.testclient import TestClient

from app.main import app
from app.services.repository_service import RepositoryService


client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_repository_import_and_chat_flow():
    response = client.post(
        "/repositories/import",
        json={"source": "github", "value": "https://github.com/example/demo", "source_path": "./repositories"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "indexed"

    repo_id = body["repo_id"]
    chat_response = client.post(
        "/chat",
        json={"repo_id": repo_id, "question": "Explain authentication"},
    )
    assert chat_response.status_code == 200
    chat_body = chat_response.json()
    assert "auth" in chat_body["answer"].lower() or "repository" in chat_body["answer"].lower()

    docs_response = client.post(
        "/docs/project",
        json={"repo_id": repo_id},
    )
    assert docs_response.status_code == 200
    assert "Generated Repository README" in docs_response.json()["readme"]


def test_repository_listing_and_conversation_history():
    response = client.post(
        "/repositories/import",
        json={"repo_url": "https://github.com/example/demo-2", "source_path": "./repositories"},
    )
    repo_id = response.json()["repo_id"]

    list_response = client.get("/repositories")
    assert list_response.status_code == 200
    repositories = list_response.json()["repositories"]
    assert any(item["id"] == repo_id for item in repositories)

    conversation_response = client.post(
        "/conversations",
        json={"repo_id": repo_id, "message": "Explain authentication"},
    )
    assert conversation_response.status_code == 200
    history = conversation_response.json()["history"]
    assert history[-1]["message"].startswith("Based on the repository contents")


def test_follow_up_prompts_receive_distinct_answers():
    response = client.post(
        "/repositories/import",
        json={"repo_url": "https://github.com/example/demo-followup", "source_path": "./repositories"},
    )
    repo_id = response.json()["repo_id"]

    conversation_response = client.post(
        "/conversations",
        json={"title": "Follow-up chat", "repository_id": repo_id},
    )
    assert conversation_response.status_code == 200
    conversation_id = conversation_response.json()["id"]

    first_response = client.post(
        "/chat",
        json={"repo_id": repo_id, "question": "Hello there", "conversation_id": conversation_id},
    )
    second_response = client.post(
        "/chat",
        json={"repo_id": repo_id, "question": "How are you today?", "conversation_id": conversation_id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["answer"] != second_response.json()["answer"]


def test_imports_local_repository_directory(tmp_path):
    repo_dir = tmp_path / "demo-local"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Local repo\n", encoding="utf-8")
    (repo_dir / "app").mkdir()
    (repo_dir / "app" / "service.py").write_text("def run(): pass\n", encoding="utf-8")

    service = RepositoryService()
    result = service.import_repository(repo_path=str(repo_dir))

    assert result["repo_id"] == "demo-local"
    assert service.get_repository("demo-local") is not None


def test_chat_uses_llm_answer_when_available(monkeypatch):
    service = RepositoryService()
    service._repositories["demo-llm"] = {
        "id": "demo-llm",
        "files": [
            {
                "path": "app/auth.py",
                "language": "python",
                "content": "def login(username, password): return ok",
                "function_names": ["login"],
                "class_names": [],
            }
        ],
        "summary": "",
        "architecture": {},
        "conversation_history": [],
    }

    class StubLLM:
        def generate(self, prompt: str, system_prompt: str | None = None) -> str:
            return "LLM-generated answer"

    monkeypatch.setattr(service, "_llm", StubLLM())

    result = service.chat("demo-llm", "Explain the repo")

    assert result is not None
    assert result["answer"] == "LLM-generated answer"


def test_gemma3_model_resolution_and_defaults():
    from app.services.repository_service import LLMProvider
    # Test normalization and model extraction
    llm = LLMProvider(provider="gemma3:12b")
    assert llm.provider == "gemma3"
    assert llm.model == "gemma3:12b"

    # Test that gemma3 enables use_llm in RepositoryService without URL/CMD env vars
    service = RepositoryService()
    service._repositories["demo-gemma"] = {
        "id": "demo-gemma",
        "files": [],
        "summary": "",
        "architecture": {},
        "conversation_history": [],
    }

    called_ollama = False

    def mock_call_ollama(prompt, system_prompt=None):
        nonlocal called_ollama
        called_ollama = True
        return "Gemma3 local response"

    gemma_llm = LLMProvider(provider="gemma3:12b")
    gemma_llm._call_ollama = mock_call_ollama
    service._llm = gemma_llm

    result = service.chat("demo-gemma", "Explain the repo")
    assert result is not None
    assert result["answer"] == "Gemma3 local response"
    assert called_ollama is True

