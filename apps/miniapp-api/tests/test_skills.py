import os
from fastapi.testclient import TestClient


def get_client():
    os.environ.setdefault("NOTION_API_KEY", "")  # ensure Notion is optional
    from apps.miniapp_api.main import app
    return TestClient(app)


def test_list_skills_ok():
    c = get_client()
    r = c.get("/skills")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 6
    assert any(s.get("slug") == "automation" for s in data)


def test_detail_skill_ok():
    c = get_client()
    r = c.get("/skills/automation")
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == "automation"
    assert isinstance(data.get("bullets_en", []), list)


def test_api_skills_ok():
    c = get_client()
    r = c.get("/api/skills")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


