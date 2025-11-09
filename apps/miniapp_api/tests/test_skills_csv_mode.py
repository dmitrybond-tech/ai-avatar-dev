from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

pytest.importorskip("fastapi")

from apps.miniapp_api.routers import skills as skills_router


def _write_csv(path: Path) -> None:
    path.write_text(
        (
            "Title EN,Bullets EN,Bullets RU,Examples EN,Examples RU,Short EN,Short RU,Slug,Tags,Title RU\n"
            "Sample Skill,\"Point one\",\"Пункт один\",\"Example\",\"Пример\",\"Short EN\",\"Short RU\",sample-skill,"
            "\"tag-one, tag-two\",Sample RU\n"
        ),
        encoding="utf-8",
    )


def test_csv_mode_skips_notion_client(monkeypatch, tmp_path):
    csv_path = tmp_path / "skills.csv"
    _write_csv(csv_path)

    monkeypatch.setenv("SKILLS_SOURCE", "csv")
    monkeypatch.setenv("SKILLS_CSV_PATH", str(csv_path))

    invoked = False

    class _SentinelClient:  # noqa: N801 - test shim
        def __init__(self, *args, **kwargs):
            nonlocal invoked
            invoked = True
            raise AssertionError("Notion client must not be constructed in CSV mode")

    monkeypatch.setattr(skills_router, "Client", _SentinelClient)

    result = skills_router.skills()

    assert not invoked
    assert result["items"]
    assert result["items"][0]["slug"] == "sample-skill"

