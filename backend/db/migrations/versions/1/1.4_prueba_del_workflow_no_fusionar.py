"""prueba del workflow, no fusionar

Migración 1.4 · va después de 1.3
Solo para probar HU-229 en un PR borrador que se cierra sin fusionar: no cambia la base de datos.
"""

from alembic import op

revision: str = "1.4"
down_revision: str | None = "1.3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SELECT 1")


def downgrade() -> None:
    op.execute("SELECT 1")
