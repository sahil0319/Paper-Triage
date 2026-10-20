"""FastAPI app: JSON API per contracts/api.md plus the static single page."""

import mimetypes
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from . import db, paper_chat, pdfstore
from .chat import answer as chat_answer
from .config import get_settings
from .llm import LazyClient, LLMError
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


Color = Literal["yellow", "mint", "peach"]
NOTE_MAX = 500


def _rects_ok(rects: list[list[float]]) -> list[list[float]]:
    for r in rects:
        if len(r) != 4 or not all(0 <= v <= 1 for v in r):
            raise ValueError("each rect must be [x, y, w, h] with values between 0 and 1")
    return rects


class AnnotationIn(BaseModel):
    paper_id: str
    page: int = Field(ge=1)
    kind: Literal["highlight", "note"]
    color: Color = "yellow"
    rects: list[list[float]] = Field(default_factory=list, max_length=50)
    quote: str = Field(default="", max_length=500)
    prefix: str = Field(default="", max_length=64)
    suffix: str = Field(default="", max_length=64)
    note: str = Field(default="", max_length=NOTE_MAX)

    @model_validator(mode="after")
    def _kind_rules(self):
        _rects_ok(self.rects)
        if self.kind == "highlight":
            if not self.rects:
                raise ValueError("a highlight needs 1 to 50 rects")
            if not self.quote:
                raise ValueError("a highlight needs a quote of 1 to 500 characters")
        else:
            if self.rects or self.quote:
                raise ValueError("a page note has no rects or quote")
            if not self.note:
                raise ValueError("a page note needs note text of 1 to 500 characters")
        return self


class AnnotationPatch(BaseModel):
    color: Color | None = None
    note: str | None = Field(default=None, max_length=NOTE_MAX)


def _annotation_out(a: dict) -> dict:
    return {k: v for k, v in a.items() if k != "top"}


class Turn(BaseModel):
    question: str
    answer: str


class PaperChatIn(BaseModel):
    paper_id: str
    question: str
    history: list[Turn] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v


class RetryIn(BaseModel):
    paper_id: str


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



class _RevalidatedStatic(StaticFiles):
    """Static files the browser must revalidate on every load, so UI updates show up without a hard refresh."""

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers.setdefault("Cache-Control", "no-cache")
        return resp


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = get_settings()
        conn = db.connect(s.db_path)
        db.init_schema(conn)
        app.state.conn = conn
        app.state.http = make_http(s.mock)
        app.state.llm = LazyClient()  # LLM config errors surface at the first call, not startup
        app.state.lock = threading.Lock()  # one sqlite connection, one user
        Path(s.data_dir).mkdir(parents=True, exist_ok=True)
        pdfstore.sweep_pending(conn)
        yield
        conn.close()
        app.state.http[0].close()

    mimetypes.add_type("text/javascript", ".mjs")  # module scripts (pdf.js) need a JS MIME type
    mimetypes.add_type("font/woff2", ".woff2")  # older Pythons and OS mime tables lack it
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
        if isinstance(st.llm, LazyClient):
            try:
                st.llm.ensure()
            except LLMError as e:
                raise HTTPException(502, f"model call failed: {e}") from e
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
    def post_library(
        body: SaveIn, request: Request, response: Response, background: BackgroundTasks
    ):
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
        if created:
            background.add_task(
                pdfstore.download, body.paper_id, st.conn, st.http, st.lock, get_settings()
            )
        response.status_code = 201 if created else 200
        return {"created": created, "paper": item}

    @app.delete("/api/library")
    def delete_library(paper_id: str, request: Request):
        st = request.app.state
        with st.lock:
            if db.get_saved(st.conn, paper_id) is None:
                raise HTTPException(404, "not in the library")
            annotations = db.annotation_count(st.conn, paper_id)
            path = (db.get_file(st.conn, paper_id) or {}).get("path")
            db.delete_saved(st.conn, paper_id)
        pdfstore.delete_file(path)
        return {"deleted": True, "annotations": annotations}

    @app.post("/api/library/retry", status_code=202)
    def retry_library(body: RetryIn, request: Request, background: BackgroundTasks):
        st = request.app.state
        with st.lock:
            if db.get_saved(st.conn, body.paper_id) is None:
                raise HTTPException(404, "not in the library")
            f = db.get_file(st.conn, body.paper_id)
            if f is not None and f["status"] != "failed":
                raise HTTPException(409, f"PDF is {f['status']}; retry only applies to failed")
            db.set_file_status(st.conn, body.paper_id, "pending", error=None)
        background.add_task(
            pdfstore.download, body.paper_id, st.conn, st.http, st.lock, get_settings()
        )
        return {"pdf": {"status": "pending", "error": None, "pages": None}}

    @app.get("/api/library/pdf")
    def get_library_pdf(paper_id: str, request: Request):
        st = request.app.state
        with st.lock:
            f = db.get_file(st.conn, paper_id)
        if f is None or f["status"] != "ready" or not f["path"] or not Path(f["path"]).is_file():
            raise HTTPException(404, "PDF not available")
        return FileResponse(
            f["path"],
            media_type="application/pdf",
            headers={"Content-Disposition": "inline", "Cache-Control": "private, max-age=3600"},
        )

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

    @app.post("/api/paper-chat")
    def post_paper_chat(body: PaperChatIn, request: Request):
        s = get_settings()
        if len(body.history) > s.paper_chat_history:
            raise HTTPException(422, f"history: at most {s.paper_chat_history} turns")
        st = request.app.state
        try:
            out = paper_chat.answer(
                body.paper_id, body.question, [t.model_dump() for t in body.history], st.conn,
                st.llm, st.lock, s,
            )
        except paper_chat.NotSaved:
            raise HTTPException(404, "not in the library") from None
        except LLMError as e:
            raise HTTPException(502, f"model call failed: {e}") from e
        return out.model_dump()

    @app.get("/api/annotations")
    def get_annotations(paper_id: str, request: Request):
        st = request.app.state
        with st.lock:
            if db.get_saved(st.conn, paper_id) is None:
                raise HTTPException(404, "not in the library")
            rows = db.list_annotations(st.conn, paper_id)
        return {"annotations": [_annotation_out(a) for a in rows]}

    @app.post("/api/annotations", status_code=201)
    def post_annotation(body: AnnotationIn, request: Request):
        st = request.app.state
        with st.lock:
            if db.get_saved(st.conn, body.paper_id) is None:
                raise HTTPException(404, "not in the library")
            f = db.get_file(st.conn, body.paper_id)
            if f is None or f["status"] != "ready":
                raise HTTPException(409, "the PDF is not ready yet")
            if f["pages"] is not None and body.page > f["pages"]:
                raise HTTPException(422, f"page: must be 1 to {f['pages']}")
            made = db.create_annotation(
                st.conn, body.paper_id, body.page, body.kind, body.color, body.rects, body.quote,
                body.prefix, body.suffix, body.note,
            )
        return _annotation_out(made)

    @app.patch("/api/annotations/{annotation_id}")
    def patch_annotation(annotation_id: int, body: AnnotationPatch, request: Request):
        st = request.app.state
        with st.lock:
            cur = db.get_annotation(st.conn, annotation_id)
            if cur is None:
                raise HTTPException(404, "unknown annotation")
            if cur["kind"] == "note" and body.note == "":
                raise HTTPException(422, "note: a page note needs text of 1 to 500 characters")
            out = db.update_annotation(st.conn, annotation_id, body.color, body.note)
        return _annotation_out(out)

    @app.delete("/api/annotations/{annotation_id}", status_code=204)
    def delete_annotation(annotation_id: int, request: Request):
        st = request.app.state
        with st.lock:
            if not db.delete_annotation(st.conn, annotation_id):
                raise HTTPException(404, "unknown annotation")
        return Response(status_code=204)

    app.mount("/", _RevalidatedStatic(directory=STATIC, html=True), name="static")
    return app


app = create_app()
