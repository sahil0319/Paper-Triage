"""FastAPI app: JSON API per contracts/api.md plus the static single page."""

import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import db
from .chat import answer as chat_answer
from .config import get_settings
from .llm import LLMError, get_client
from .models import LibraryItem
from .net import make_http
from .pipeline import (
    NoStoredResult,
    ResultFailed,
    build_snapshot,
    library_item,
    mark_saved,
    sort_results,
    to_out,
    triage,
)
from .tags import keywords

STATIC = Path(__file__).parent / "static"


class TriageIn(BaseModel):
    query: str
    max_results: int = 10
    offset: int = Field(default=0, ge=0, le=1000)


class ChatIn(BaseModel):
    question: str
    paper_ids: list[str]  # the current result set; required (may be empty)

    @field_validator("question")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v

    @field_validator("paper_ids")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class SaveIn(BaseModel):
    paper_id: str
    topic: str = ""


class DirIn(BaseModel):
    name: str


class MoveIn(BaseModel):
    paper_id: str
    directory_id: int | None = None


def _dir_write(fn, *args):
    """Run a directory create/rename; map name errors to 409 (taken) or 422 (invalid)."""
    try:
        return fn(*args)
    except db.DuplicateName as e:
        raise HTTPException(409, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


def _item(conn, saved: dict) -> dict:
    return LibraryItem(**library_item(conn, saved)).model_dump()


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
                return triage(
                    body.query, body.max_results, st.conn, st.http, st.llm, body.offset
                )
            except ValueError as e:
                raise HTTPException(422, str(e)) from e

    @app.get("/api/papers")
    def papers(request: Request, topic: str | None = None):
        conn = request.app.state.conn
        with request.app.state.lock:
            if topic is None:
                topic = db.latest_topic(conn) or ""
            rows = db.list_results(conn, topic)
            results = sort_results([to_out(r) for r in rows])
            mark_saved(conn, results)
        return {"topic": topic, "results": results}

    @app.get("/api/library")
    def get_library(request: Request):
        conn = request.app.state.conn
        with request.app.state.lock:
            saved = db.list_saved(conn)
            papers = [_item(conn, s) for s in saved]
            dirs = db.list_directories(conn)
        unsorted = sum(1 for p in papers if p["directory_id"] is None)
        return {
            "papers": papers, "directories": dirs, "unsorted_count": unsorted,
            "total": len(papers),
        }

    @app.post("/api/library")
    def post_library(body: SaveIn, request: Request, response: Response):
        st = request.app.state
        with st.lock:
            try:
                snapshot = build_snapshot(st.conn, body.paper_id, body.topic)
            except NoStoredResult:
                raise HTTPException(404, "no stored result for this paper") from None
            except ResultFailed:
                raise HTTPException(409, "only completed results can be saved") from None
            created = db.save_paper(
                st.conn, body.paper_id, snapshot, body.topic, keywords(body.topic)
            )
            if created:
                db.set_file_status(st.conn, body.paper_id, "pending", source_url=snapshot["pdf_url"])
            item = _item(st.conn, db.get_saved(st.conn, body.paper_id))
        response.status_code = 201 if created else 200
        return {"created": created, "paper": item}

    @app.delete("/api/library")
    def delete_library(paper_id: str, request: Request):
        st = request.app.state
        with st.lock:
            if db.get_saved(st.conn, paper_id) is None:
                raise HTTPException(404, "not in the library")
            annotations = db.annotation_count(st.conn, paper_id)
            db.delete_saved(st.conn, paper_id)
        return {"deleted": True, "annotations": annotations}

    @app.post("/api/chat")
    def post_chat(body: ChatIn, request: Request):
        if len(body.paper_ids) > get_settings().chat_max_ids:
            raise HTTPException(422, f"paper_ids: at most {get_settings().chat_max_ids} ids")
        st = request.app.state
        with st.lock:
            try:
                out = chat_answer(body.question, body.paper_ids, st.conn, st.llm)
            except LLMError as e:
                raise HTTPException(502, f"model call failed: {e}") from e
            db.save_chat_turn(st.conn, body.question, out.answer, out.citations, out.refused)
        return out.model_dump()

    @app.post("/api/library/move")
    def move_library(body: MoveIn, request: Request):
        st = request.app.state
        with st.lock:
            if not db.move_paper(st.conn, body.paper_id, body.directory_id):
                raise HTTPException(404, "unknown paper or directory")
        return {"paper_id": body.paper_id, "directory_id": body.directory_id}

    @app.post("/api/directories", status_code=201)
    def post_directory(body: DirIn, request: Request):
        st = request.app.state
        with st.lock:
            return _dir_write(db.create_directory, st.conn, body.name)

    @app.patch("/api/directories/{directory_id}")
    def patch_directory(directory_id: int, body: DirIn, request: Request):
        st = request.app.state
        with st.lock:
            out = _dir_write(db.rename_directory, st.conn, directory_id, body.name)
        if out is None:
            raise HTTPException(404, "unknown directory")
        return out

    @app.delete("/api/directories/{directory_id}")
    def delete_directory(directory_id: int, request: Request):
        st = request.app.state
        with st.lock:
            moved = db.delete_directory(st.conn, directory_id)
        if moved is None:
            raise HTTPException(404, "unknown directory")
        return {"deleted": True, "moved": moved}

    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app


app = create_app()
