# GitHub Repository Chatbot

## About the chatbot

This is a lightweight repository assistant that helps you explore an imported GitHub repository through natural-language questions. It indexes repository files, retrieves the most relevant code and documentation, and answers with file citations so you can quickly move from a question to the right source.

## Problem statement

Build a repository-aware chatbot for developers that can answer questions about a GitHub repository by reading its local files, summarizing its structure, and pointing users to the most relevant code locations. The chatbot should support natural-language queries, provide citations, and help users understand repository architecture quickly.

## Tools and frameworks

- Python 3.10+
- FastAPI for the backend API
- Streamlit for the local web UI
- pytest for automated tests
- httpx for API testing
- Uvicorn for running the FastAPI server
- OpenAI or Gemini APIs for LLM-backed responses

## Requirements

The backend dependencies are listed in [backend/requirements.txt](backend/requirements.txt):

```txt
fastapi
uvicorn
pytest
httpx
```

The frontend UI also uses Streamlit, which is included in the backend requirements file for convenience:

```bash
pip install -r requirements.txt
```

To enable LLM-generated answers, set one of the following environment variables before starting the backend:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-openai-key
```

Or with Gemini:

```bash
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=your-gemini-key
```

## What is included

- FastAPI backend with repository import, chat, documentation, and analysis endpoints
- Simple repository parser and in-memory indexing
- Retrieval-based chat responses with file citations
- Documentation generation and static-analysis-style suggestions



## Run locally

1. Create and activate a virtual environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the backend requirements (this includes Streamlit for the UI):

```bash
pip install -r requirements.txt
```

3. Start the backend API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. In a second terminal, activate the same virtual environment and start the frontend UI:

```bash
cd frontend
source ../backend/.venv/bin/activate
python -m streamlit run streamlit_app.py
```

5. Open the Streamlit UI in your browser and import a repository to start chatting.

## Test

```bash
cd backend
source .venv/bin/activate
pytest -q
```
/
