"""V5 baseline schema"""
from alembic import op
import sqlalchemy as sa
revision="0001_v5_baseline"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    # Baseline is generated from the same SQLAlchemy metadata used by the application.
    # Future schema changes should be separate Alembic revisions.
    from app.main import Base
    bind=op.get_bind()
    Base.metadata.create_all(bind=bind)
def downgrade():
    # Baseline downgrade is intentionally non-destructive.
    pass
