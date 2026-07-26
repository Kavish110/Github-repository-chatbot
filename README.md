# GitHub Repository Chatbot (RepoGPT)

This workspace contains a lightweight MVP for the PRD described in the project brief.

## What is included

- FastAPI backend with repository import, chat, documentation, and analysis endpoints
- Simple repository parser and in-memory indexing
- Retrieval-based chat responses with file citations
- Documentation generation and static-analysis-style suggestions

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt streamlit
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
streamlit run streamlit_app.py
```

## Test

```bash
cd backend
source .venv/bin/activate
pytest -q
```
