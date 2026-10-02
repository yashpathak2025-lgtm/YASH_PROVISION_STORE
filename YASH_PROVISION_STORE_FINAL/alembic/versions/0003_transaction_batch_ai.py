"""Add purchase idempotency and batch allocation persistence."""
from alembic import op
import sqlalchemy as sa

revision = "0003_transaction_batch_ai"
down_revision = "0002_integrity_hardening"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("purchases", sa.Column("idempotency_key", sa.String(length=100), nullable=True))
    op.create_index("ix_purchases_idempotency_key", "purchases", ["idempotency_key"], unique=True)
    for table in ("sale_items", "order_items", "return_items"):
        op.add_column(table, sa.Column("batch_allocations", sa.Text(), nullable=True, server_default="[]"))

def downgrade():
    for table in ("sale_items", "order_items", "return_items"):
        op.drop_column(table, "batch_allocations")
    op.drop_index("ix_purchases_idempotency_key", table_name="purchases")
    op.drop_column("purchases", "idempotency_key")
