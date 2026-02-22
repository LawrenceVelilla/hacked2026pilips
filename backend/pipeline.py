"""Session management and orchestration: classify → generate → chat loop."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from backend.classifier import classify_image, update_description
from backend.config import SESSION_TTL_SECONDS
from backend.flux_tryon import generate_tryon
from backend.models import ClassificationResult


@dataclass
class Session:
    session_id: str
    user_photo_url: str
    original_image_url: str
    current_description: ClassificationResult
    current_result_url: str
    chat_history: list[dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


_sessions: dict[str, Session] = {}


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def _cleanup_expired() -> None:
    """Remove sessions older than TTL."""
    now = datetime.utcnow()
    expired = [
        sid for sid, s in _sessions.items()
        if (now - s.created_at).total_seconds() > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]


async def start_tryon(image_url: str, user_photo_url: str) -> Session:
    """Initial try-on: classify image → FLUX generate → create session."""
    _cleanup_expired()

    classification = await classify_image(image_url)

    result_url = await generate_tryon(
        user_photo_url=user_photo_url,
        outfit_description=classification.description,
        outfit_image_url=image_url,
    )

    session_id = uuid.uuid4().hex[:12]
    session = Session(
        session_id=session_id,
        user_photo_url=user_photo_url,
        original_image_url=image_url,
        current_description=classification,
        current_result_url=result_url,
    )
    _sessions[session_id] = session
    return session


async def chat_modify(
    session_id: str,
    message: str,
    new_image_url: str | None = None,
) -> Session:
    """Chat modification: update description → regenerate."""
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found or expired")

    updated = await update_description(
        current_description=session.current_description.description,
        user_message=message,
        new_image_url=new_image_url,
    )

    if new_image_url:
        # Layering: pass previous result + new item
        result_url = await generate_tryon(
            user_photo_url=session.user_photo_url,
            outfit_description=updated.description,
            outfit_image_url=session.original_image_url,
            previous_result_url=session.current_result_url,
            new_item_image_url=new_image_url,
        )
    else:
        # Text-only modification: user photo + previous result with new prompt
        result_url = await generate_tryon(
            user_photo_url=session.user_photo_url,
            outfit_description=updated.description,
            outfit_image_url=session.original_image_url,
            previous_result_url=session.current_result_url,
        )

    session.chat_history.append({"role": "user", "content": message})
    session.chat_history.append({"role": "assistant", "content": updated.description})
    session.current_description = updated
    session.current_result_url = result_url

    return session
