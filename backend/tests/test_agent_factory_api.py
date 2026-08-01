"""API tests for the AI Agent Factory endpoints (full lifecycle).

The compiler's LLM call and the assembler's agent run are monkeypatched so the
tests exercise the API/gate/authz logic without network access.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_user, require_role
from app.main import app
from app.models.user import User, UserRole
from app.services.agent_factory.compiler import AgentCompiler, _CompiledDraft


@pytest.fixture
def user_headers(client, db):
    """A regular active user, injected via dependency override."""
    user = User(id=1001, email="u@example.com", hashed_password="x", is_active=True,
                role=UserRole.USER)

    app.dependency_overrides[get_current_active_user] = lambda: user
    # require_role(ADMIN) returns a fresh checker each call; override the factory result
    yield user
    app.dependency_overrides.pop(get_current_active_user, None)


@pytest.fixture
def admin_user():
    return User(id=1, email="a@example.com", hashed_password="x", is_active=True,
                role=UserRole.ADMIN)


def _fake_draft():
    return _CompiledDraft(
        role_name="日程安排专家",
        role_description="排期设提醒",
        boundaries=["不写代码"],
        tool_verbs=["查天气", "设提醒"],
        policies=["下雨改户外", "深夜不打扰家人"],
        acceptance=["当下雨且有户外时，应改期"],
    )


@pytest.fixture(autouse=True)
def patch_compiler(monkeypatch):
    async def fake_compile(self, one_liner, created_by=None):
        return self.assemble_spec(one_liner, _fake_draft(), created_by)
    monkeypatch.setattr(AgentCompiler, "compile", fake_compile)


def _admin_override(admin_user):
    # Override the active-user dep so admin-gated routes see an admin.
    app.dependency_overrides[get_current_active_user] = lambda: admin_user


def test_list_tools(client, user_headers):
    resp = client.get("/api/v1/factory/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert "weather" in names and "bash" in names


def test_full_lifecycle_compile_edit_approve_run(client, db, user_headers, admin_user):
    # compile
    resp = client.post("/api/v1/factory/compile", json={"one_liner": "做一个日程安排专家"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    spec_id = body["id"]
    assert body["status"] == "draft"
    assert {t["name"] for t in body["spec"]["tools"]} >= {"weather", "reminder"}

    # view
    assert client.get(f"/api/v1/factory/specs/{spec_id}").status_code == 200

    # a regular user cannot approve (needs admin)
    assert client.post(f"/api/v1/factory/specs/{spec_id}/approve").status_code == 403

    # admin approves
    _admin_override(admin_user)
    r = client.post(f"/api/v1/factory/specs/{spec_id}/approve")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"
    assert r.json()["version"] == 2

    # cannot edit an approved spec in place
    edited = r.json()["spec"]
    assert client.patch(f"/api/v1/factory/specs/{spec_id}", json={"spec": edited}).status_code == 409

    # publish
    rp = client.post(f"/api/v1/factory/specs/{spec_id}/publish")
    assert rp.status_code == 200
    assert rp.json()["status"] == "published"


def test_incomplete_spec_cannot_be_approved(client, db, user_headers, admin_user, monkeypatch):
    # compile a spec then wipe its policies to make it incomplete
    resp = client.post("/api/v1/factory/compile", json={"one_liner": "x"})
    spec_id = resp.json()["id"]
    spec = resp.json()["spec"]
    spec["policies"] = []
    spec["acceptance"] = []
    client.patch(f"/api/v1/factory/specs/{spec_id}", json={"spec": spec})

    _admin_override(admin_user)
    r = client.post(f"/api/v1/factory/specs/{spec_id}/approve")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "errors" in detail


def test_draft_cannot_run(client, db, user_headers):
    resp = client.post("/api/v1/factory/compile", json={"one_liner": "做一个日程安排专家"})
    spec_id = resp.json()["id"]
    r = client.post(f"/api/v1/factory/agents/{spec_id}/run", json={"input": "帮我安排明天"})
    assert r.status_code == 409
    assert "approved" in r.json()["detail"]
