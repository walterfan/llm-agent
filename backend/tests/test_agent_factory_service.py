"""Unit tests for AgentSpecService — persistence + quality gate lifecycle."""

import pytest

from app.services.agent_factory.service import (
    AgentSpecService,
    SpecIncompleteError,
    SpecStateError,
)
from app.services.agent_factory.spec import (
    AcceptanceCase,
    AgentSpec,
    PromptSpec,
    RoleSpec,
    ToolBinding,
)


def _complete_spec() -> AgentSpec:
    return AgentSpec(
        one_liner="做一个日程安排专家",
        role=RoleSpec(name="日程安排专家", description="排期设提醒", boundaries=["不写代码"]),
        tools=[ToolBinding(name="reminder")],
        policies=["下雨改户外"],
        prompts=PromptSpec(system="你是日程安排专家", user_template="{input}"),
        acceptance=[AcceptanceCase(given="下雨", when="有户外", then="改期")],
    )


def _incomplete_spec() -> AgentSpec:
    # missing policies and acceptance
    return AgentSpec(
        one_liner="做点什么",
        role=RoleSpec(name="半成品"),
        prompts=PromptSpec(system="你是助手"),
    )


def test_save_and_get_draft(db):
    rec = AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    assert rec.status == "draft"
    assert rec.name == "日程安排专家"
    fetched = AgentSpecService.get_spec(db, rec.id)
    assert fetched is not None
    assert fetched.role.name == "日程安排专家"


def test_list_filters_by_status_and_owner(db):
    AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    AgentSpecService.save_draft(db, _complete_spec(), created_by=2)
    assert len(AgentSpecService.list(db)) == 2
    assert len(AgentSpecService.list(db, created_by=1)) == 1
    assert len(AgentSpecService.list(db, status="draft")) == 2
    assert len(AgentSpecService.list(db, status="approved")) == 0


def test_approve_complete_spec_bumps_version(db):
    rec = AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    assert rec.version == 1
    approved = AgentSpecService.approve(db, rec.id)
    assert approved.status == "approved"
    assert approved.version == 2


def test_approve_incomplete_spec_is_blocked(db):
    rec = AgentSpecService.save_draft(db, _incomplete_spec(), created_by=1)
    with pytest.raises(SpecIncompleteError) as exc:
        AgentSpecService.approve(db, rec.id)
    joined = "; ".join(exc.value.errors)
    assert "policies" in joined
    assert "acceptance" in joined
    # remains draft
    assert AgentSpecService.get(db, rec.id).status == "draft"


def test_draft_cannot_be_run(db):
    rec = AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    assert AgentSpecService.is_runnable(rec) is False
    approved = AgentSpecService.approve(db, rec.id)
    assert AgentSpecService.is_runnable(approved) is True


def test_cannot_edit_approved_in_place(db):
    rec = AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    AgentSpecService.approve(db, rec.id)
    with pytest.raises(SpecStateError):
        AgentSpecService.update_draft(db, rec.id, _complete_spec())


def test_update_draft_persists_changes(db):
    rec = AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    edited = AgentSpecService.get_spec(db, rec.id)
    edited.policies = ["下雨改户外", "深夜不打扰家人"]
    AgentSpecService.update_draft(db, rec.id, edited)
    reloaded = AgentSpecService.get_spec(db, rec.id)
    assert reloaded.policies == ["下雨改户外", "深夜不打扰家人"]
    assert AgentSpecService.get(db, rec.id).status == "draft"


def test_publish_only_from_approved(db):
    rec = AgentSpecService.save_draft(db, _complete_spec(), created_by=1)
    with pytest.raises(SpecStateError):
        AgentSpecService.publish(db, rec.id)  # still draft
    AgentSpecService.approve(db, rec.id)
    published = AgentSpecService.publish(db, rec.id)
    assert published.status == "published"
    assert AgentSpecService.is_runnable(published) is True
