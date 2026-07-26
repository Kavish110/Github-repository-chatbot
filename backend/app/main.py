from fastapi import FastAPI

from app.api.analysis import router as analysis_router
from app.api.chat import router as chat_router
from app.api.conversation import router as conversation_router
from app.api.documentation import router as documentation_router
from app.api.folder import router as folder_router
from app.api.health import router as health_router
from app.api.messages import router as messages_router
from app.api.repository import router as repository_router

app = FastAPI(title="GitHub Repository Chatbot", version="0.1.0")

app.include_router(health_router)
app.include_router(repository_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(messages_router)
app.include_router(folder_router)
app.include_router(documentation_router)
app.include_router(analysis_router)
