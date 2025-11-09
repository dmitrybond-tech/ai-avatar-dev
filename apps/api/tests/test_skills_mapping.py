from __future__ import annotations

import copy

from app.providers import skills as skills_provider


def _title(value: str) -> dict:
    return {"type": "title", "title": [{"plain_text": value}]}


def _rich(value: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"plain_text": value}]}


def test_notion_page_to_skill_localized_fallback_and_cleanup() -> None:
    """Ensure Notion pages map to SkillOut with locale fallbacks and bullet cleanup."""

    page = {
        "id": "123",
        "properties": {
            "Title EN": _title("Skill EN"),
            "Title RU": _rich(""),
            "Short RU": _rich("Краткое описание"),
            "Short EN": _rich("Short EN"),
            "Bullets EN": _rich("- First point\n• Second point"),
            "Examples EN": _rich("Example A\nExample B"),
            "Slug": {"type": "formula", "formula": {"string": "custom-slug"}},
            "Tags": {
                "type": "multi_select",
                "multi_select": [
                    {"name": "Team"},
                    {"name": "team"},
                    {"name": "Ops"},
                ],
            },
            "Status": {"type": "status", "status": {"name": "Public"}},
            "Order": {"type": "number", "number": 7},
        },
    }

    skill = skills_provider._notion_page_to_skill(copy.deepcopy(page), "ru", index=1)

    assert skill.slug == "custom-slug"
    assert skill.title == "Skill EN"  # falls back to EN title
    assert skill.short == "Краткое описание"
    assert skill.bullets == ["First point", "Second point"]
    assert skill.examples == ["Example A", "Example B"]
    assert skill.tags == ["Team", "Ops"]  # duplicates removed, preserves order
    assert skill.order == 7


def test_is_published_respects_status_public() -> None:
    """Published checkbox may be false while status=Public keeps the page visible."""

    page = {
        "properties": {
            "Published": {"type": "checkbox", "checkbox": False},
            "Status": {"type": "status", "status": {"name": "Public"}},
        }
    }

    assert skills_provider._is_published(page) is True

