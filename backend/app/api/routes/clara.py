"""Clara, the help assistant. Public (no login), so it works on every page.

    GET  /api/clara/start   greeting + quick-reply chips
    POST /api/clara/ask     {"message": "..."} or {"faq_id": "..."} -> Clara's answer

Messages are never stored or logged. Simple rate limit per visitor: RATE_LIMIT messages per minute.
"""
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.clara import faq as clara

router = APIRouter(prefix="/api/clara", tags=["clara"])

RATE_LIMIT = 20             # messages per visitor per minute
NOT_SURE = ("I'm not sure about that one yet. You can send our team a message and we'll reply by email.")
_book = clara.load()        # read once at startup; restart the server after editing clara_faq.json
_recent: dict[str, deque] = defaultdict(deque)


class Chip(BaseModel):
    id: str
    label: str


class StartOut(BaseModel):
    name: str = "Clara"
    greeting: str
    chips: list[Chip]


class AskIn(BaseModel):
    message: str | None = Field(default=None, max_length=500)
    faq_id: str | None = Field(default=None, max_length=60)   # sent when a chip is tapped


class AskOut(BaseModel):
    answer: str
    source: Literal["faq", "ai", "none"]     # "ai" = worded by AI from our FAQ
    faq_id: str | None = None
    related: list[Chip] = []
    show_contact: bool = False


def _chip(f: clara.Faq) -> Chip:
    return Chip(id=f.id, label=f.question)


def _check_rate(request: Request) -> None:
    who = request.client.host if request.client else "unknown"
    now, window = time.monotonic(), _recent[who]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT:
        raise HTTPException(429, "Clara needs a short break. Please try again in a minute.")
    window.append(now)


@router.get("/start", response_model=StartOut)
def start():
    return StartOut(greeting=_book.greeting, chips=[_chip(_book.by_id(c)) for c in _book.chips])


@router.post("/ask", response_model=AskOut)
def ask(body: AskIn, request: Request):
    _check_rate(request)
    if body.faq_id:
        found = _book.by_id(body.faq_id)
        if found is None:
            raise HTTPException(404, "Unknown question")
        return _faq_reply(found, others=[])
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(422, "Type a question for Clara")

    chat = clara.small_talk(message)
    if chat:
        return AskOut(answer=chat, source="faq", related=[_chip(_book.by_id(c)) for c in _book.chips[:3]])

    ranked = clara.rank(_book, message)
    if ranked and ranked[0][0] >= clara.MATCH_THRESHOLD:
        return _faq_reply(ranked[0][1], others=[f for score, f in ranked[1:] if score > 0.3])

    answer, related_ids = clara.ai_answer(_book, message)
    if answer:
        related = [_chip(_book.by_id(r)) for r in related_ids]
        contact = any(_book.by_id(r).contact for r in related_ids)
        return AskOut(answer=answer, source="ai", related=related, show_contact=contact)
    suggestions = [_chip(f) for score, f in ranked[:clara.RELATED_COUNT] if score > 0.2]
    return AskOut(answer=NOT_SURE, source="none", related=suggestions, show_contact=True)


def _faq_reply(found: clara.Faq, others: list[clara.Faq]) -> AskOut:
    related = [_chip(f) for f in others[:2] if f.id != found.id]
    return AskOut(answer=found.answer, source="faq", faq_id=found.id, related=related, show_contact=found.contact)