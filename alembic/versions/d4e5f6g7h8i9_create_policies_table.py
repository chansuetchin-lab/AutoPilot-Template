"""create policies table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "policies",

        sa.Column(
            "id",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.String(),
            nullable=False,
            server_default="",
        ),

        sa.Column(
            "summary",
            sa.String(),
            nullable=True,
        ),

        sa.Column(
            "natural_language",
            sa.String(),
            nullable=False,
            server_default="",
        ),

        sa.Column(
            "policy_type",
            sa.String(length=50),
            nullable=False,
            server_default="natural_language",
        ),

        sa.Column(
            "policy_scope",
            sa.String(length=50),
            nullable=True,
            server_default="base",
        ),

        sa.Column(
            "dsl",
            sa.JSON(),
            nullable=True,
        ),

        sa.Column(
            "refined_instruction",
            sa.String(),
            nullable=True,
        ),

        sa.Column(
            "ai_instruction",
            sa.String(),
            nullable=True,
        ),

        sa.Column(
            "entity_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),

        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="50",
        ),

        sa.Column(
            "tags",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),

        sa.Column(
            "source",
            sa.String(length=100),
            nullable=True,
            server_default="user",
        ),

        sa.Column(
            "execution_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "last_executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_policies_id",
        "policies",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_policies_name",
        "policies",
        ["name"],
        unique=False,
    )

    op.create_index(
        "ix_policies_policy_type",
        "policies",
        ["policy_type"],
        unique=False,
    )

    op.create_index(
        "ix_policies_is_active",
        "policies",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        "ix_policies_priority",
        "policies",
        ["priority"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_policies_priority",
        table_name="policies",
    )

    op.drop_index(
        "ix_policies_is_active",
        table_name="policies",
    )

    op.drop_index(
        "ix_policies_policy_type",
        table_name="policies",
    )

    op.drop_index(
        "ix_policies_name",
        table_name="policies",
    )

    op.drop_index(
        "ix_policies_id",
        table_name="policies",
    )

    op.drop_table("policies")