"""create members classes bookings

Revision ID: 0001
Revises: 
Create Date: 2026-11-18 17:04:36.763222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("type IN ('BASIC', 'PREMIUM')", name="ck_members_type"),
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("max_capacity > 0", name="ck_classes_max_capacity"),
    )

    op.create_table(
        "bookings",
        sa.Column("member_id", sa.String(length=32), nullable=False),
        sa.Column("class_id", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("member_id", "class_id"),
        sa.ForeignKeyConstraint(
            ["member_id"], ["members.id"],
            name="fk_bookings_member_id_members", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"],
            name="fk_bookings_class_id_classes", ondelete="CASCADE",
        ),
    )
    # PostgreSQL does not index foreign key columns automatically
    op.create_index("ix_bookings_class_id", "bookings", ["class_id"])


def downgrade() -> None:
    # Reverse order: bookings references the other two, so it must go first
    op.drop_table("bookings")
    op.drop_table("classes")
    op.drop_table("members")
