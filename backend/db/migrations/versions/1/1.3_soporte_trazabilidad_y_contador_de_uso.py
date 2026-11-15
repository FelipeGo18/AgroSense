"""soporte trazabilidad y contador de uso

Migración 1.3 · va después de 1.2
Creada el 2026-10-12 14:54:34.261811+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1.3"
down_revision: str | None = "1.2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_daily",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("endpoint", sa.String(length=16), nullable=False),
        sa.Column("municipality_id", sa.String(length=12), nullable=False),
        sa.Column("crop_id", sa.String(length=40), nullable=False),
        sa.Column("count", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "endpoint in ('diagnostics', 'rotations', 'changes', 'calendar', 'water_plans', 'scenarios')",
            name=op.f("ck_usage_daily_endpoint_valid"),
        ),
        sa.CheckConstraint("count >= 0", name=op.f("ck_usage_daily_count_not_negative")),
        sa.PrimaryKeyConstraint("day", "endpoint", "municipality_id", "crop_id", name=op.f("pk_usage_daily")),
    )
    op.create_table(
        "support_tickets",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('open', 'in_progress', 'closed')", name=op.f("ck_support_tickets_status_valid")),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.lot_id"], name=op.f("fk_support_tickets_lot_id_lots"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_support_tickets_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ticket_id", name=op.f("pk_support_tickets")),
    )
    op.create_index(op.f("ix_support_tickets_user_id"), "support_tickets", ["user_id"], unique=False)
    op.create_table(
        "activity_log",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=16), nullable=True),
        sa.Column("subject_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("object_type", sa.String(length=16), nullable=True),
        sa.Column("object_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(length=8), server_default="ok", nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "object_type is null or object_type in ('user', 'session', 'lot', 'season', 'ticket')",
            name=op.f("ck_activity_log_object_type_valid"),
        ),
        sa.CheckConstraint("outcome in ('ok', 'denied', 'failed')", name=op.f("ck_activity_log_outcome_valid")),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.user_id"], name=op.f("fk_activity_log_actor_user_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"], ["users.user_id"], name=op.f("fk_activity_log_subject_user_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["support_tickets.ticket_id"], name=op.f("fk_activity_log_ticket_id_support_tickets"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_activity_log")),
    )
    op.create_index(op.f("ix_activity_log_actor_user_id"), "activity_log", ["actor_user_id"], unique=False)
    op.create_index("ix_activity_log_occurred_at", "activity_log", ["occurred_at"], unique=False)
    op.create_index("ix_activity_log_subject_user_id_occurred_at", "activity_log", ["subject_user_id", "occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_log_subject_user_id_occurred_at", table_name="activity_log")
    op.drop_index("ix_activity_log_occurred_at", table_name="activity_log")
    op.drop_index(op.f("ix_activity_log_actor_user_id"), table_name="activity_log")
    op.drop_table("activity_log")
    op.drop_index(op.f("ix_support_tickets_user_id"), table_name="support_tickets")
    op.drop_table("support_tickets")
    op.drop_table("usage_daily")
