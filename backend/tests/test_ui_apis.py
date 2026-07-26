from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_repository_listing_and_conversation_workflow():
    import_response = client.post(
        "/repositories/import",
        json={"repo_url": "https://github.com/example/demo-ui", "source_path": "./repositories"},
    )
    assert import_response.status_code == 200
    repo_id = import_response.json()["repo_id"]

    list_response = client.get("/repositories")
    assert list_response.status_code == 200
    repositories = list_response.json()["repositories"]
    assert any(item["id"] == repo_id for item in repositories)

    conversation_response = client.post(
        "/conversations",
        json={"title": "UI workflow", "repository_id": repo_id},
    )
    assert conversation_response.status_code == 200
    conversation_id = conversation_response.json()["id"]

    chat_response = client.post(
        "/chat",
        json={"repo_id": repo_id, "question": "Explain authentication", "conversation_id": conversation_id},
    )
    assert chat_response.status_code == 200
    assert chat_response.json()["conversation_id"] == conversation_id

    messages_response = client.get(f"/messages/{conversation_id}")
    assert messages_response.status_code == 200
    assert len(messages_response.json()["messages"]) >= 2
