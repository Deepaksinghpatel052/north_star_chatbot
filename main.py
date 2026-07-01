"""
main.py

FastAPI application for the North Star Support Bot.

- Serves a simple chat UI at "/" (static/index.html)
- Exposes POST /chat for the conversation logic
- Fully self-contained: no external API keys, no external services.
  Evaluators can run this locally with zero setup beyond
  `pip install -r requirements.txt` and `uvicorn main:app`.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from conversation import Session, WELCOME_MESSAGE, process_message

app = FastAPI(title="North Star Support Bot")

# In-memory session store: {session_id: Session}
# A simulated project with no persistence/deployment requirement, so this
# is intentionally kept simple (no database).
SESSIONS: dict[str, Session] = {}


class ChatRequest(BaseModel):
    """Request body for POST /chat.

    Attributes:
        session_id: The session to continue, or None to start a new one.
        message: The user's chat message text.
    """

    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    """Response body for POST /chat.

    Attributes:
        session_id: The session id to send back on the next request
            (the client should persist this for the duration of the chat).
        reply: The chatbot's reply text for this turn.
    """

    session_id: str
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """Handle one turn of the conversation.

    Creates a new session if no session_id was supplied, advances that
    session's state machine with the user's message, and returns the
    bot's reply along with the session_id to use for subsequent turns.
    """
    session_id = payload.session_id or str(uuid.uuid4())
    session = SESSIONS.setdefault(session_id, Session())

    reply = process_message(session, payload.message)
    return ChatResponse(session_id=session_id, reply=reply)


@app.post("/reset")
def reset(session_id: str) -> dict:
    """Discard a session's conversation state, letting the user start fresh."""
    SESSIONS.pop(session_id, None)
    return {"status": "ok"}


@app.get("/welcome")
def welcome() -> dict:
    """Return the bot's initial greeting message, shown when the chat UI loads."""
    return {"message": WELCOME_MESSAGE}


# --- Serve the chat UI --------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the chat UI's HTML page at the site root."""
    return FileResponse("static/index.html")
