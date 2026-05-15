"""Initial normalized ATS schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.create_table("organizations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")
