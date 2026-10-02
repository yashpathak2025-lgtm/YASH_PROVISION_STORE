"""${message}"""
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
from alembic import op
import sqlalchemy as sa
${imports or ""}
def upgrade():
    ${upgrades or "pass"}
def downgrade():
    ${downgrades or "pass"}
