"""notes and categories

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("normalized_name", sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("notes")
    op.drop_table("categories")
