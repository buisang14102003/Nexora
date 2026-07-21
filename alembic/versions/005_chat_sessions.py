"""Persist workspace-scoped chat sessions and conversational messages."""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "005_chat_sessions"
down_revision = "004_chats_and_citations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_sessions_workspace_user_updated_at",
        "chat_sessions",
        ["workspace_id", "user_id", "updated_at"],
    )
    op.add_column("chat_messages", sa.Column("session_id", sa.Uuid(), nullable=True))
    op.add_column("chat_messages", sa.Column("role", sa.String(length=16), nullable=True))
    op.add_column("chat_messages", sa.Column("content", sa.String(), nullable=True))
    op.add_column("chat_messages", sa.Column("citations", sa.JSON(), nullable=True))

    connection = op.get_bind()
    chat_sessions = sa.table(
        "chat_sessions",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("title", sa.String(length=255)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    legacy_messages = sa.table(
        "chat_messages",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("answer", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("session_id", sa.Uuid()),
        sa.column("role", sa.String()),
        sa.column("content", sa.String()),
        sa.column("citations", sa.JSON()),
    )
    legacy_citations = sa.table(
        "chat_citations",
        sa.column("message_id", sa.Uuid()),
        sa.column("document_id", sa.Uuid()),
        sa.column("source_name", sa.String()),
        sa.column("page_number", sa.Integer()),
        sa.column("row_range", sa.String()),
        sa.column("chunk_id", sa.Uuid()),
    )
    citations_by_message: dict[object, list[dict[str, object]]] = {}
    for citation in connection.execute(sa.select(legacy_citations)).mappings():
        citations_by_message.setdefault(citation["message_id"], []).append(
            {
                "document_id": str(citation["document_id"]),
                "source_name": citation["source_name"],
                "page_number": citation["page_number"],
                "row_range": citation["row_range"],
                "chunk_id": str(citation["chunk_id"]) if citation["chunk_id"] else None,
            }
        )

    for message in connection.execute(sa.select(legacy_messages)).mappings():
        session_id = uuid4()
        connection.execute(
            sa.insert(chat_sessions).values(
                id=session_id,
                workspace_id=message["workspace_id"],
                user_id=message["user_id"],
                title="Previous chat",
                created_at=message["created_at"],
                updated_at=message["updated_at"],
            )
        )
        connection.execute(
            sa.update(legacy_messages)
            .where(legacy_messages.c.id == message["id"])
            .values(
                session_id=session_id,
                role="assistant",
                content=message["answer"],
                citations=citations_by_message.get(message["id"], []),
            )
        )

    op.drop_table("chat_citations")
    op.drop_index("ix_chat_messages_workspace_id", table_name="chat_messages")
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.create_foreign_key(
            "fk_chat_messages_session_id_chat_sessions", "chat_sessions", ["session_id"], ["id"]
        )
        batch_op.alter_column("session_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.alter_column("role", existing_type=sa.String(length=16), nullable=False)
        batch_op.alter_column("content", existing_type=sa.String(), nullable=False)
        batch_op.alter_column("citations", existing_type=sa.JSON(), nullable=False)
        batch_op.drop_column("workspace_id")
        batch_op.drop_column("user_id")
        batch_op.drop_column("route")
        batch_op.drop_column("answer")
        batch_op.drop_column("updated_at")


def downgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("route", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("answer", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    connection = op.get_bind()
    messages = sa.table(
        "chat_messages",
        sa.column("id", sa.Uuid()),
        sa.column("session_id", sa.Uuid()),
        sa.column("content", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("route", sa.String()),
        sa.column("answer", sa.String()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    sessions = sa.table(
        "chat_sessions",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
    )
    for message in connection.execute(sa.select(messages)).mappings():
        chat_session = connection.execute(
            sa.select(sessions).where(sessions.c.id == message["session_id"])
        ).mappings().one()
        connection.execute(
            sa.update(messages)
            .where(messages.c.id == message["id"])
            .values(
                workspace_id=chat_session["workspace_id"],
                user_id=chat_session["user_id"],
                route="document_rag",
                answer=message["content"],
                updated_at=message["created_at"],
            )
        )

    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.alter_column("workspace_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.alter_column("user_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.alter_column("route", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column("answer", existing_type=sa.String(), nullable=False)
        batch_op.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.drop_constraint("fk_chat_messages_session_id_chat_sessions", type_="foreignkey")
        batch_op.drop_column("citations")
        batch_op.drop_column("content")
        batch_op.drop_column("role")
        batch_op.drop_column("session_id")

    op.create_index("ix_chat_messages_workspace_id", "chat_messages", ["workspace_id"])
    op.create_table(
        "chat_citations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("source_name", sa.String(length=512), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("row_range", sa.String(length=255), nullable=True),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_index("ix_chat_sessions_workspace_user_updated_at", table_name="chat_sessions")
    op.drop_table("chat_sessions")
