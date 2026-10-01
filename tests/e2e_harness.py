"""Live-server harness for real-browser tests (constitution 1.1.0): the real app on 127.0.0.1,
MOCK_LLM=1, a temp SQLite file, and an optional artificial delay before POST /api/triage so the
searching indicator can be observed."""

import asyncio
import os
import threading
import time

import httpx
import uvicorn


class _TriageDelay:
    """Test-only ASGI middleware: awaits server.triage_delay before POST /api/triage."""

    def __init__(self, app, server: "LiveServer"):
        self.app = app
        self.server = server

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == "/api/triage"
            and self.server.triage_delay > 0
        ):
            await asyncio.sleep(self.server.triage_delay)
        await self.app(scope, receive, send)


class LiveServer:
    def __init__(self, db_path: str, port: int | None = None):
        self.db_path = db_path
        self.port = port or int(os.environ.get("E2E_PORT", "8766"))
        self.triage_delay = 0.0
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._saved_env: dict[str, str | None] = {}

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def set_triage_delay(self, seconds: float) -> None:
        self.triage_delay = float(seconds)

    def start(self) -> None:
        for key, value in (("MOCK_LLM", "1"), ("PAPER_TRIAGE_DB", self.db_path)):
            self._saved_env[key] = os.environ.get(key)
            os.environ[key] = value
        from paper_triage.app import create_app

        config = uvicorn.Config(
            _TriageDelay(create_app(), self), host="127.0.0.1", port=self.port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{self.url}/api/status", timeout=1).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        self.stop()
        raise RuntimeError(f"live server did not become ready on {self.url} within 10 s")

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        for key, old in self._saved_env.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        self._saved_env.clear()
