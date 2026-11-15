"""respuesta de los mensajes

Migración 1.5 · va después de 1.4
Creada el 2026-11-14

HU-163: el responsable de los datos contesta cada mensaje de «Escribir al responsable», y la persona ve la respuesta en
«Mis mensajes». `support_tickets` suma `reply` (el texto de la respuesta) y `replied_at` (cuándo se dio). Los dos
nulos mientras no se conteste; las filas que ya existen quedan sin respuesta.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "1.5"
down_revision: str | None = "1.4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("support_tickets", sa.Column("reply", sa.Text(), nullable=True))
    op.add_column("support_tickets", sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("support_tickets", "replied_at")
    op.drop_column("support_tickets", "reply")
