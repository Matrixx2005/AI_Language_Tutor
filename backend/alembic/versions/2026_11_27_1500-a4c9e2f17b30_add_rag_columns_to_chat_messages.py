"""add rag columns to chat_messages

Revision ID: a4c9e2f17b30
Revises: dfd85f565969
Create Date: 2026-11-27 15:00:00

Tuần 4 (RAG): chế độ thực sự dùng, nguồn đã truy xuất, cờ hạ cấp. Cột mới nullable/có mặc định —
không đổi dữ liệu cũ.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4c9e2f17b30"
down_revision: Union[str, Sequence[str], None] = "dfd85f565969"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("rag_mode", sa.String(length=16), nullable=True))
    op.add_column("chat_messages", sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "chat_messages", sa.Column("rag_fallback", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "rag_fallback")
    op.drop_column("chat_messages", "sources")
    op.drop_column("chat_messages", "rag_mode")
