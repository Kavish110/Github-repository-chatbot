import os
import re
from pathlib import Path

import streamlit as st
import requests

API_BASE = "http://127.0.0.1:8000"

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None


def _browse_local_repo() -> str:
    if not tk:
        return ""
    try:
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        folder = filedialog.askdirectory()
        root.destroy()
        return folder or ""
    except Exception:
        return ""


def _load_saved_api_key() -> str:
    secrets_path = Path.home() / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return ""

    try:
        content = secrets_path.read_text(encoding="utf-8")
    except OSError:
        return ""

    match = re.search(r'\[llm\]\s*api_key\s*=\s*"([^"]*)"', content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    return ""


def _save_api_key(api_key: str) -> None:
    if not api_key:
        return

    secrets_path = Path.home() / ".streamlit" / "secrets.toml"
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    escaped = api_key.replace("\\", "\\\\").replace('"', '\\"')
    secrets_path.write_text(f'[llm]\napi_key = "{escaped}"\n', encoding="utf-8")
    os.chmod(secrets_path, 0o600)

st.set_page_config(page_title="RepoGPT UI", page_icon="🧠", layout="wide")

st.title("GitHub Repository Chatbot")
st.caption("Local-first repository Q&A with conversation history and documentation tools")

if "repo_id" not in st.session_state:
    st.session_state.repo_id = ""
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ""
if "llm_api_key" not in st.session_state:
    st.session_state.llm_api_key = _load_saved_api_key()
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = "openai"

with st.sidebar:
    st.header("LLM setup")
    llm_provider = st.selectbox(
        "Provider",
        ["openai", "gemini", "gemma3:12b (Ollama)", "qwen2.5-coder:14b (Ollama)"],
        index=0,
        key="llm_provider",
    )

    # Ollama-based models run locally and don't need an API key
    _is_ollama = "ollama" in (st.session_state.llm_provider or "").lower()
    if _is_ollama:
        st.info("🦙 This model runs locally via Ollama — no API key required.")
    else:
        llm_api_key = st.text_input("API key", type="password", value=st.session_state.llm_api_key, key="llm_api_key_input")
        if st.button("Save API key"):
            _save_api_key(llm_api_key)
            st.session_state.llm_api_key = llm_api_key
            st.success("API key saved locally in your Streamlit secrets file")

    if "show_add_repo" not in st.session_state:
        st.session_state.show_add_repo = False
    if "selected_local_repo_folder" not in st.session_state:
        st.session_state.selected_local_repo_folder = ""

    st.header("Repositories")
    repo_response = requests.get(f"{API_BASE}/repositories", timeout=30)
    repos = []
    if repo_response.ok:
        repos = repo_response.json().get("repositories", [])
    elif not repo_response.ok:
        st.info("Repository service unavailable")

    if repos:
        for repo in repos:
            status = repo.get("status", "indexed")
            status_icon = "🟡" if status == "indexing" else "🔴" if status == "failed" else "●"
            if repo["id"] == st.session_state.repo_id:
                label = f"✓ {repo['name']} {status_icon}"
            else:
                label = f"{repo['name']} {status_icon}"
            if st.button(label, key=f"repo-{repo['id']}"):
                st.session_state.repo_id = repo["id"]
                st.session_state.conversation_id = ""
                st.rerun()
    else:
        st.info("No repositories added.")

    with st.expander("Add repository", expanded=False):
        source = st.radio("Source", ["GitHub", "Local"], index=0, key="add_repo_source")
        if source == "GitHub":
            github_repo_url = st.text_input("Repository URL", placeholder="https://github.com/example/demo", key="github_repo_url")
        else:
            st.write("Repository Folder")
            local_repo_path = st.text_input(
                "Local repository path",
                value=st.session_state.selected_local_repo_folder,
                placeholder="/Users/you/projects/my-repo",
                key="local_repo_path",
            )
            st.session_state.selected_local_repo_folder = local_repo_path
            if tk:
                if st.button("Browse...", key="browse_local"):
                    selected = _browse_local_repo()
                    if selected:
                        st.session_state.selected_local_repo_folder = selected
                        st.experimental_rerun()
                    else:
                        st.warning("Unable to open folder browser. Please paste the path manually.")
            else:
                st.info("Native folder browsing is unavailable in this deployment; paste the path above.")

        if st.button("Add", key="add_repo"):
            if source == "GitHub":
                if not github_repo_url.strip():
                    st.error("Enter a GitHub repository URL.")
                else:
                    response = requests.post(
                        f"{API_BASE}/repositories/import",
                        json={"source": "github", "value": github_repo_url.strip()},
                        timeout=30,
                    )
                    if response.ok:
                        payload = response.json()
                        st.session_state.repo_id = payload["repo_id"]
                        st.success(f"Imported repository {payload['repo_id']}")
                    else:
                        st.error("Import failed")
            else:
                if not st.session_state.selected_local_repo_folder:
                    st.error("Select a local repository folder first.")
                else:
                    response = requests.post(
                        f"{API_BASE}/repositories/import",
                        json={"source": "local", "value": st.session_state.selected_local_repo_folder},
                        timeout=30,
                    )
                    if response.ok:
                        payload = response.json()
                        st.session_state.repo_id = payload["repo_id"]
                        st.success(f"Imported repository {payload['repo_id']}")
                    else:
                        st.error("Import failed")

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

    # Strip display suffixes like "(Ollama)" before sending to backend
    _provider_for_api = re.sub(r"\s*\(.*?\)\s*$", "", st.session_state.llm_provider or "")

    response = requests.post(
        f"{API_BASE}/chat",
        json={
            "repo_id": st.session_state.repo_id,
            "question": prompt,
            "conversation_id": st.session_state.conversation_id,
            "api_key": st.session_state.llm_api_key,
            "llm_provider": _provider_for_api,
        },
        timeout=120,
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
