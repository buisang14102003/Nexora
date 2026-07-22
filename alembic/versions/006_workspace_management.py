"""Add pin and archive state to workspaces."""

from alembic import op
import sqlalchemy as sa


revision = "006_workspace_management"
down_revision = "005_chat_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "archived_at")
    op.drop_column("workspaces", "is_pinned")
