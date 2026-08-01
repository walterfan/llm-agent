"""AI Agent Factory (孵化器) API endpoints.

Lifecycle: compile → (edit) → approve → (publish) → run.

AuthZ:
  - compile / list / view / edit-own-draft / run: any active user.
  - approve / publish: admin role (the human quality gate is an admin action).
  - editing another user's spec, or any non-draft spec, is rejected.
  - published specs are runnable by any user but never editable in place.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.db.base import get_db
from app.models.agent_spec import AgentSpecRecord
from app.models.user import User, UserRole
from app.schemas.agent_factory import (
    CompileRequest,
    RunRequest,
    RunResponse,
    RunStep,
    SpecResponse,
    SpecSummary,
    UpdateSpecRequest,
)
from app.services.agent_factory import registry
from app.services.agent_factory.assembler import assemble
from app.services.agent_factory.compiler import AgentCompiler
from app.services.agent_factory.service import (
    AgentSpecService,
    SpecIncompleteError,
    SpecStateError,
)
from app.services.memory import FileMemoryBackend

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(record: AgentSpecRecord) -> SpecResponse:
    spec = AgentSpecService._to_spec(record)
    return SpecResponse(
        id=record.id,
        name=record.name,
        version=record.version,
        status=record.status,
        spec=spec,
    )


def _require_owner_or_admin(record: AgentSpecRecord, user: User) -> None:
    is_admin = user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)
    if record.created_by != user.id and not is_admin:
        raise HTTPException(status_code=403, detail="not the owner of this spec")


# --- tools registry ---------------------------------------------------------


@router.get("/tools")
def list_tools(current_user: Annotated[User, Depends(get_current_active_user)]):
    """Read-only capability catalog the compiler picks from."""
    return [c.model_dump() for c in registry.list_capabilities()]


# --- compile ----------------------------------------------------------------


@router.post("/compile", response_model=SpecResponse)
async def compile_spec(
    request: CompileRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Compile a one-liner into an AgentSpec draft (five blueprints)."""
    try:
        spec = await AgentCompiler().compile(
            request.one_liner, created_by=current_user.id
        )
    except Exception as e:  # noqa: BLE001 — surface compile failures cleanly
        logger.exception("compile failed: %s", e)
        raise HTTPException(status_code=502, detail=f"compile failed: {e}") from e
    record = AgentSpecService.save_draft(db, spec, created_by=current_user.id)
    return _to_response(record)


# --- read -------------------------------------------------------------------


@router.get("/specs", response_model=list[SpecSummary])
def list_specs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    status: Optional[str] = Query(None),
):
    records = AgentSpecService.list(db, status=status)
    return [
        SpecSummary(
            id=r.id,
            name=r.name,
            version=r.version,
            status=r.status,
            one_liner=r.one_liner,
        )
        for r in records
    ]


@router.get("/specs/{spec_id}", response_model=SpecResponse)
def get_spec(
    spec_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    record = AgentSpecService.get(db, spec_id)
    if record is None:
        raise HTTPException(status_code=404, detail="spec not found")
    return _to_response(record)


# --- edit (draft only, owner only) ------------------------------------------


@router.patch("/specs/{spec_id}", response_model=SpecResponse)
def update_spec(
    spec_id: str,
    request: UpdateSpecRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    record = AgentSpecService.get(db, spec_id)
    if record is None:
        raise HTTPException(status_code=404, detail="spec not found")
    _require_owner_or_admin(record, current_user)
    try:
        updated = AgentSpecService.update_draft(db, spec_id, request.spec)
    except SpecStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(updated)


@router.delete("/specs/{spec_id}", status_code=204)
def delete_spec(
    spec_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Delete a spec. Only the owner or admin can delete."""
    record = AgentSpecService.get(db, spec_id)
    if record is None:
        raise HTTPException(status_code=404, detail="spec not found")
    _require_owner_or_admin(record, current_user)
    AgentSpecService.delete(db, spec_id)
    return None  # 204 No Content


# --- quality gate: approve / publish (admin) --------------------------------


@router.post("/specs/{spec_id}/approve", response_model=SpecResponse)
def approve_spec(
    spec_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    try:
        record = AgentSpecService.approve(db, spec_id)
    except SpecIncompleteError as e:
        raise HTTPException(
            status_code=422, detail={"message": "spec incomplete", "errors": e.errors}
        ) from e
    except SpecStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(record)


@router.post("/specs/{spec_id}/publish", response_model=SpecResponse)
def publish_spec(
    spec_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    try:
        record = AgentSpecService.publish(db, spec_id)
    except SpecStateError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(record)


# --- run --------------------------------------------------------------------


@router.post("/agents/{spec_id}/run", response_model=RunResponse)
async def run_agent(
    spec_id: str,
    request: RunRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    record = AgentSpecService.get(db, spec_id)
    if record is None:
        raise HTTPException(status_code=404, detail="spec not found")
    if not AgentSpecService.is_runnable(record):
        raise HTTPException(
            status_code=409,
            detail=f"spec is {record.status}; only approved/published specs can run",
        )
    spec = AgentSpecService._to_spec(record)
    try:
        agent, _tools = assemble(spec, db=db, user_id=current_user.id)
        result = await agent.ainvoke({"messages": [("user", request.input)]})
    except Exception as e:  # noqa: BLE001
        logger.exception("run failed: %s", e)
        raise HTTPException(status_code=502, detail=f"run failed: {e}") from e

    final = ""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    if messages:
        last = messages[-1]
        final = getattr(last, "content", "") or ""

    # Save conversation to long-term memory if enabled
    if spec.memory.long_term:
        try:
            memory_backend = FileMemoryBackend()
            # Save user input
            memory_backend.add_memory(
                agent_id=spec_id,
                content=f"User: {request.input}",
                metadata={"user_id": current_user.id, "role": "user"},
            )
            # Save agent response
            if final:
                memory_backend.add_memory(
                    agent_id=spec_id,
                    content=f"Agent: {final}",
                    metadata={"user_id": current_user.id, "role": "agent"},
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("failed to save conversation to memory: %s", e)

    return RunResponse(spec_id=spec_id, final=final, trace=[RunStep()])
