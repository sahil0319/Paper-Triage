"""FastAPI app: JSON API per contracts/api.md plus the static single page."""

import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from . import db
from .chat import answer as chat_answer
from .config import get_settings
from .llm import LLMError, get_client
from .net import make_http
from .pipeline import sort_results, to_out, triage

STATIC = Path(__file__).parent / "static"


class TriageIn(BaseModel):
    query: str
    max_results: int = 10


class ChatIn(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = get_settings()
        conn = db.connect(s.db_path)
        db.init_schema(conn)
        app.state.conn = conn
        app.state.http = make_http(s.mock)
        app.state.llm = get_client()
        app.state.lock = threading.Lock()  # one sqlite connection, one user
        yield
        conn.close()
        app.state.http[0].close()

    app = FastAPI(title="Paper Triage", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def _plain_422(request: Request, exc: RequestValidationError):
        msgs = [
            f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}".lstrip(": ")
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": "; ".join(msgs)})

    @app.get("/api/status")
    def status(request: Request):
        s = get_settings()
        with request.app.state.lock:
            count = len(db.paper_ids(request.app.state.conn))
        return {"mock": s.mock, "model": s.model, "provider": s.provider, "paper_count": count}

    @app.post("/api/triage")
    def post_triage(body: TriageIn, request: Request):
        if not 1 <= body.max_results <= get_settings().max_papers:
            raise HTTPException(422, f"max_results must be 1..{get_settings().max_papers}")
        st = request.app.state
        with st.lock:
            try:
                return triage(body.query, body.max_results, st.conn, st.http, st.llm)
            except ValueError as e:
                raise HTTPException(422, str(e)) from e

    @app.get("/api/papers")
    def papers(request: Request, topic: str | None = None):
        conn = request.app.state.conn
        with request.app.state.lock:
            if topic is None:
                topic = db.latest_topic(conn) or ""
            rows = db.list_results(conn, topic)
        return {"topic": topic, "results": sort_results([to_out(r) for r in rows])}

    @app.post("/api/chat")
    def post_chat(body: ChatIn, request: Request):
        st = request.app.state
        with st.lock:
            try:
                out = chat_answer(body.question, st.conn, st.llm)
            except LLMError as e:
                raise HTTPException(502, f"model call failed: {e}") from e
            db.save_chat_turn(st.conn, body.question, out.answer, out.citations, out.refused)
        return out.model_dump()

    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


app = create_app()
