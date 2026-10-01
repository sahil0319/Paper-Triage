import pytest


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")
