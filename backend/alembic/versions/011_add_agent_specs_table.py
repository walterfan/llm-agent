"""add agent_specs table (AI Agent Factory)

Revision ID: 011
Revises: 010
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_specs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("one_liner", sa.Text(), nullable=False, server_default=""),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_specs_id", "agent_specs", ["id"])
    op.create_index("ix_agent_specs_status", "agent_specs", ["status"])
    op.create_index("ix_agent_specs_created_by", "agent_specs", ["created_by"])
    op.create_index("ix_agent_specs_created_at", "agent_specs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_specs_created_at", table_name="agent_specs")
    op.drop_index("ix_agent_specs_created_by", table_name="agent_specs")
    op.drop_index("ix_agent_specs_status", table_name="agent_specs")
    op.drop_index("ix_agent_specs_id", table_name="agent_specs")
    op.drop_table("agent_specs")
