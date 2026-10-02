"""Add purchase idempotency and batch allocation persistence safely.

The V5 baseline builds tables from the current SQLAlchemy metadata. On a fresh
database those columns may already exist, so this revision is intentionally
idempotent and only adds missing schema pieces.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_transaction_batch_ai"
down_revision = "0002_integrity_hardening"
branch_labels = None
depends_on = None


def _columns(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _indexes(bind, table):
    return {i["name"] for i in sa.inspect(bind).get_indexes(table)}


def upgrade():
    bind = op.get_bind()

    purchase_columns = _columns(bind, "purchases")
    if "idempotency_key" not in purchase_columns:
        op.add_column(
            "purchases",
            sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        )

    purchase_indexes = _indexes(bind, "purchases")
    if "ix_purchases_idempotency_key" not in purchase_indexes:
        op.create_index(
            "ix_purchases_idempotency_key",
            "purchases",
            ["idempotency_key"],
            unique=True,
        )

    for table in ("sale_items", "order_items", "return_items"):
        if "batch_allocations" not in _columns(bind, table):
            op.add_column(
                table,
                sa.Column(
                    "batch_allocations",
                    sa.Text(),
                    nullable=True,
                    server_default="[]",
                ),
            )


def downgrade():
    bind = op.get_bind()

    for table in ("sale_items", "order_items", "return_items"):
        if "batch_allocations" in _columns(bind, table):
            op.drop_column(table, "batch_allocations")

    if "ix_purchases_idempotency_key" in _indexes(bind, "purchases"):
        op.drop_index("ix_purchases_idempotency_key", table_name="purchases")

    if "idempotency_key" in _columns(bind, "purchases"):
        op.drop_column("purchases", "idempotency_key")
