import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="RepoGPT UI", page_icon="🧠", layout="wide")

st.title("GitHub Repository Chatbot")
st.caption("Local-first repository Q&A with conversation history and documentation tools")

if "repo_id" not in st.session_state:
    st.session_state.repo_id = ""
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ""

with st.sidebar:
    st.header("Repository")
    repo_url = st.text_input("GitHub URL", placeholder="https://github.com/example/demo")
    source_path = st.text_input("Source path", value="./repositories")
    if st.button("Import repository"):
        response = requests.post(
            f"{API_BASE}/repositories/import",
            json={"repo_url": repo_url, "source_path": source_path},
            timeout=30,
        )
        if response.ok:
            payload = response.json()
            st.session_state.repo_id = payload["repo_id"]
            st.success(f"Imported repository {payload['repo_id']}")
        else:
            st.error("Import failed")

    if st.button("Create conversation"):
        payload = {"title": "New conversation", "repository_id": st.session_state.repo_id or None}
        response = requests.post(f"{API_BASE}/conversations", json=payload, timeout=30)
        if response.ok:
            conversation = response.json()
            st.session_state.conversation_id = conversation["id"]
            st.success("Conversation created")
        else:
            st.error("Unable to create conversation")

    st.header("Available repositories")
    repo_response = requests.get(f"{API_BASE}/repositories", timeout=30)
    if repo_response.ok:
        repos = repo_response.json().get("repositories", [])
        if repos:
            for repo in repos:
                if st.button(repo["id"], key=f"repo-{repo['id']}"):
                    st.session_state.repo_id = repo["id"]
                    st.session_state.conversation_id = ""
                    st.rerun()
        else:
            st.info("No repositories indexed yet")
    else:
        st.info("Repository service unavailable")

st.subheader("Chat")
if st.session_state.repo_id:
    st.write(f"Active repository: {st.session_state.repo_id}")
else:
    st.info("Import a repository to start chatting")

if st.session_state.conversation_id:
    messages_response = requests.get(f"{API_BASE}/messages/{st.session_state.conversation_id}", timeout=30)
    if messages_response.ok:
        messages = messages_response.json().get("messages", [])
        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

prompt = st.chat_input("Ask about the repository")
if prompt and st.session_state.repo_id:
    if not st.session_state.conversation_id:
        conv_response = requests.post(
            f"{API_BASE}/conversations",
            json={"title": prompt[:40], "repository_id": st.session_state.repo_id},
            timeout=30,
        )
        if conv_response.ok:
            st.session_state.conversation_id = conv_response.json()["id"]
        else:
            st.error("Could not create conversation")
            st.stop()

    response = requests.post(
        f"{API_BASE}/chat",
        json={"repo_id": st.session_state.repo_id, "question": prompt, "conversation_id": st.session_state.conversation_id},
        timeout=30,
    )
    if response.ok:
        payload = response.json()
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            st.write(payload["answer"])
            if payload.get("citations"):
                with st.expander("Sources"):
                    for citation in payload["citations"]:
                        st.write(f"- {citation['path']} ({citation['score']})")
    else:
        st.error("Chat request failed")
