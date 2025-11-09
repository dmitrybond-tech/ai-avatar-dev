from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

import app.main as main_module
from app.providers import skills as skills_provider


class _FailingNotionClient:
    def __init__(self, *args, **kwargs) -> None:
        raise TypeError("ClientOptions.__init__() got an unexpected keyword argument 'timeout'")


@pytest.fixture(autouse=True)
def _reset_skills_state(monkeypatch):
    skills_provider.clear_skills_cache()
    monkeypatch.setattr(skills_provider, "_notion_client", None)
    monkeypatch.setattr(skills_provider, "_last_fetch_meta", skills_provider._FetchMeta())
    yield
    skills_provider.clear_skills_cache()


@pytest.fixture()
def api_client(monkeypatch, tmp_path) -> TestClient:
    async def _async_noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(main_module, "init_db", _async_noop)
    monkeypatch.setattr(main_module, "close_db", _async_noop)
    monkeypatch.setattr(main_module, "validate_env", lambda: None)
    monkeypatch.setattr(main_module, "ping_telegram_if_strict", lambda: None)
    monkeypatch.setattr(main_module, "Path", lambda *_args, **_kwargs: tmp_path / "tts")

    client = TestClient(main_module.app)
    try:
        yield client
    finally:
        client.close()


def _configure_settings(monkeypatch, *, source: str) -> None:
    csv_fixture = Path(__file__).resolve().parents[2] / "api" / "data" / "skills.csv"
    monkeypatch.setattr(skills_provider.settings, "skills_source", source)
    monkeypatch.setattr(skills_provider.settings, "notion_api_key", "secret-key")
    monkeypatch.setattr(skills_provider.settings, "notion_skills_db_id", "db-123")
    monkeypatch.setattr(skills_provider.settings, "skills_csv_path", str(csv_fixture))
    monkeypatch.setattr(skills_provider.settings, "debug_skills_api", True)
    monkeypatch.setattr(skills_provider.settings, "notion_timeout", 5)


def test_skills_auto_falls_back_to_csv_on_client_typeerror(monkeypatch, api_client: TestClient) -> None:
    _configure_settings(monkeypatch, source="auto")
    monkeypatch.setattr(skills_provider, "Client", _FailingNotionClient)

    response = api_client.get("/api/skills", params={"lang": "en"})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data, "expected CSV fallback to return items"

    meta = skills_provider.get_last_fetch_meta()
    assert meta.source == "csv"
    assert meta.fallback is True


def test_skills_notion_mode_surfaces_notion_error(monkeypatch, api_client: TestClient) -> None:
    _configure_settings(monkeypatch, source="notion")
    monkeypatch.setattr(skills_provider, "Client", _FailingNotionClient)

    response = api_client.get("/api/skills", params={"lang": "en"})

    assert response.status_code == 503
    assert response.json() == {"error": "notion_error"}

