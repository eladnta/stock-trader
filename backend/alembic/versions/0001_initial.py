"""initial

Revision ID: 0001
Revises:
Create Date: 2026-06-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("total_value", sa.Float(), nullable=False),
        sa.Column("total_return_pct", sa.Float(), nullable=False),
        sa.Column("positions", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("shares", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "conviction_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("horizon", sa.String(length=8), nullable=False),
        sa.Column("predicted_action", sa.String(length=8), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("accuracy_pct", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("conviction_records")
    op.drop_table("trades")
    op.drop_table("portfolio_snapshots")
