import os
import asyncio
from pathlib import Path
from collections import defaultdict
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import BaseMessage

_session_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

def get_session_lock(session_id: str) -> asyncio.Lock:
    return _session_locks[session_id]

def _sessions_dir() -> Path:
    base = os.environ.get("DATA_FOLDER_PATH", ".")
    path = Path(base) / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_session_history(session_id: str) -> FileChatMessageHistory:
    return FileChatMessageHistory(str(_sessions_dir() / f"{session_id}.json"))

def load_messages_from_disk(session_id: str) -> list[BaseMessage]:
    """Zwraca listę wiadomości z pliku (pusta lista dla nowej sesji)."""
    return get_session_history(session_id).messages
