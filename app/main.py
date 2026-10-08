from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.database.database import (
    Base,
    engine
)

from app.routers import (
    auth,
    users,
    conversations
)

from app.websocket.chat import router as websocket_router
Base.metadata.create_all(
    bind=engine
)

app = FastAPI(
    title="FastAPI Chat Application",
    version="1.0.0"
)

app.include_router(
    auth.router
)

app.include_router(
    users.router
)

app.include_router(
    conversations.router
)

app.include_router(
    websocket_router
)

@app.get("/")
async def home():

    return FileResponse(
        "app/templates/login.html"
    )

@app.get("/register")
async def register_page():

    return FileResponse(
        "app/templates/register.html"
    )

@app.get("/chat")
async def chat_page():

    return FileResponse(
        "app/templates/chat.html"
    )

@app.get("/chat.html")
async def old_chat_page():

    return FileResponse(
        "app/templates/chat.html"
    )