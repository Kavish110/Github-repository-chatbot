from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_repository_import_and_chat_flow():
    response = client.post(
        "/repositories/import",
        json={"repo_url": "https://github.com/example/demo", "source_path": "./repositories"},
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
    assert history[-1]["message"] == "Explain authentication"
