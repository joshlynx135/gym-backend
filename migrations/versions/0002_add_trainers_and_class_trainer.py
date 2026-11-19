"""add trainers and class trainer

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19 12:13:05.041990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trainers",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Nullable on purpose: classes that already exist have no trainer yet.
    # A NOT NULL column without a default would be rejected for a table that has rows.
    op.add_column("classes", sa.Column("trainer_id", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        "fk_classes_trainer_id_trainers",  # constraint name
        "classes",                         # table that holds the reference
        "trainers",                        # table being referenced
        ["trainer_id"],                    # local column
        ["id"],                            # referenced column
        ondelete="RESTRICT",
    )
    # PostgreSQL does not index foreign key columns automatically
    op.create_index("ix_classes_trainer_id", "classes", ["trainer_id"])


def downgrade() -> None:
    # Reverse order of upgrade: first what depends on the column, then the column, then the table
    op.drop_index("ix_classes_trainer_id", table_name="classes")
    op.drop_constraint("fk_classes_trainer_id_trainers", "classes", type_="foreignkey")
    op.drop_column("classes", "trainer_id")
    op.drop_table("trainers")
