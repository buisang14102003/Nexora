"""Add durable CSV extraction metadata."""

from alembic import op
import sqlalchemy as sa


revision = "003_ingestion_metadata"
down_revision = "002_documents_and_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("csv_schema", sa.JSON(), nullable=True))
    op.add_column("documents", sa.Column("csv_row_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "csv_row_count")
    op.drop_column("documents", "csv_schema")
