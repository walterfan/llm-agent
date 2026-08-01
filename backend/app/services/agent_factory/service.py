"""AgentSpec service — persistence + the human quality gate (质检闸门).

Owns the spec lifecycle and its state machine:

    draft  --approve-->  approved  --publish-->  published

Rules enforced here (not in the API layer):
  - Only a *complete* spec (validate_complete() == []) can be approved.
  - approve increments version and keeps prior versions for audit.
  - draft specs cannot be run; only approved/published can be assembled.
  - approved/published specs cannot be edited in place — edits require a new draft
    (fork). published specs are runnable by other users but never editable by them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent_spec import AgentSpecRecord
from app.services.agent_factory.spec import AgentSpec


class SpecStateError(Exception):
    """Raised when an operation is illegal for the spec's current status."""


class SpecIncompleteError(Exception):
    """Raised when approving a spec that is missing required blueprints."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class AgentSpecService:
    """CRUD + lifecycle for AgentSpec records."""

    # ---- serialization helpers -------------------------------------------------

    @staticmethod
    def _to_record(spec: AgentSpec, created_by: Optional[int]) -> AgentSpecRecord:
        return AgentSpecRecord(
            id=spec.id,
            name=spec.role.name,
            version=spec.version,
            status=spec.status,
            one_liner=spec.one_liner,
            spec_json=spec.model_dump(mode="json"),
            created_by=created_by,
        )

    @staticmethod
    def _to_spec(record: AgentSpecRecord) -> AgentSpec:
        return AgentSpec.model_validate(record.spec_json)

    # ---- create / read ---------------------------------------------------------

    @classmethod
    def save_draft(
        cls, db: Session, spec: AgentSpec, created_by: Optional[int] = None
    ) -> AgentSpecRecord:
        """Persist a freshly compiled draft spec."""
        spec.status = "draft"
        record = cls._to_record(spec, created_by)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def get(cls, db: Session, spec_id: str) -> Optional[AgentSpecRecord]:
        return db.query(AgentSpecRecord).filter(AgentSpecRecord.id == spec_id).first()

    @classmethod
    def get_spec(cls, db: Session, spec_id: str) -> Optional[AgentSpec]:
        record = cls.get(db, spec_id)
        return cls._to_spec(record) if record else None

    @classmethod
    def list(
        cls, db: Session, status: Optional[str] = None, created_by: Optional[int] = None
    ) -> list[AgentSpecRecord]:
        q = db.query(AgentSpecRecord)
        if status:
            q = q.filter(AgentSpecRecord.status == status)
        if created_by is not None:
            q = q.filter(AgentSpecRecord.created_by == created_by)
        return q.order_by(AgentSpecRecord.created_at.desc()).all()

    # ---- edit (draft only) -----------------------------------------------------

    @classmethod
    def update_draft(
        cls, db: Session, spec_id: str, updated: AgentSpec
    ) -> AgentSpecRecord:
        """Update a draft in place. Rejects edits to approved/published specs."""
        record = cls.get(db, spec_id)
        if record is None:
            raise SpecStateError(f"spec {spec_id} not found")
        if record.status != "draft":
            raise SpecStateError(
                f"cannot edit a {record.status} spec in place; fork a new draft instead"
            )
        updated.id = record.id
        updated.status = "draft"
        updated.version = record.version
        updated.updated_at = datetime.utcnow()
        record.name = updated.role.name
        record.one_liner = updated.one_liner
        record.spec_json = updated.model_dump(mode="json")
        db.commit()
        db.refresh(record)
        return record

    # ---- lifecycle gate --------------------------------------------------------

    @classmethod
    def approve(cls, db: Session, spec_id: str) -> AgentSpecRecord:
        """draft → approved. Blocks if the spec is incomplete; bumps version."""
        record = cls.get(db, spec_id)
        if record is None:
            raise SpecStateError(f"spec {spec_id} not found")
        if record.status != "draft":
            raise SpecStateError(
                f"only draft specs can be approved (was {record.status})"
            )

        spec = cls._to_spec(record)
        errors = spec.validate_complete()
        if errors:
            raise SpecIncompleteError(errors)

        spec.status = "approved"
        spec.version = record.version + 1
        spec.updated_at = datetime.utcnow()

        record.status = "approved"
        record.version = spec.version
        record.spec_json = spec.model_dump(mode="json")
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def publish(cls, db: Session, spec_id: str) -> AgentSpecRecord:
        """approved → published (shareable/runnable by other users)."""
        record = cls.get(db, spec_id)
        if record is None:
            raise SpecStateError(f"spec {spec_id} not found")
        if record.status != "approved":
            raise SpecStateError(
                f"only approved specs can be published (was {record.status})"
            )
        spec = cls._to_spec(record)
        spec.status = "published"
        spec.updated_at = datetime.utcnow()
        record.status = "published"
        record.spec_json = spec.model_dump(mode="json")
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def delete(cls, db: Session, spec_id: str) -> bool:
        """Delete a spec. Returns True if deleted, False if not found.

        Note: Only the owner or admin should be able to delete a spec.
        Authorization check should be done in the API layer.
        """
        record = cls.get(db, spec_id)
        if record is None:
            return False
        db.delete(record)
        db.commit()
        return True

    @staticmethod
    def is_runnable(record: AgentSpecRecord) -> bool:
        """draft cannot run; approved/published can be assembled and run."""
        return record.status in ("approved", "published")
