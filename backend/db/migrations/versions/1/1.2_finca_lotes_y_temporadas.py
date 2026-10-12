"""finca lotes y temporadas

Migración 1.2 · va después de 1.1
Creada el 2026-10-12 14:54:09.633348+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1.2"
down_revision: str | None = "1.1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lots",
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("municipality_id", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("area_ha", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("irrigated", sa.Boolean(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("area_ha > 0", name=op.f("ck_lots_area_positive")),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_lots_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("lot_id", name=op.f("pk_lots")),
    )
    op.create_index(op.f("ix_lots_municipality_id"), "lots", ["municipality_id"], unique=False)
    op.create_index(op.f("ix_lots_user_id"), "lots", ["user_id"], unique=False)
    op.create_table(
        "seasons",
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("crop_id", sa.String(length=40), nullable=False),
        sa.Column("area_ha", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("follows_season_ids", postgresql.ARRAY(sa.Uuid()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("sowing_date", sa.Date(), nullable=False),
        sa.Column("harvest_date", sa.Date(), nullable=True),
        sa.Column("diagnosis_light", sa.String(length=16), nullable=True),
        sa.Column("diagnosis_light_default", sa.String(length=16), nullable=True),
        sa.Column("diagnosis_action", sa.String(length=16), nullable=True),
        sa.Column("diagnosis_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("diagnosis_irrigated", sa.Boolean(), nullable=True),
        sa.Column("dataset_version", sa.String(length=40), nullable=True),
        sa.Column("rules_version", sa.String(length=40), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "diagnosis_action is null or diagnosis_action in ('sow', 'other_window', 'rotate', 'review_data')",
            name=op.f("ck_seasons_diagnosis_action_valid"),
        ),
        sa.CheckConstraint(
            "diagnosis_light is null or diagnosis_light in ('green', 'yellow', 'red', 'not_evaluable')",
            name=op.f("ck_seasons_diagnosis_light_valid"),
        ),
        sa.CheckConstraint(
            "diagnosis_light_default is null or diagnosis_light_default in ('green', 'yellow', 'red', 'not_evaluable')",
            name=op.f("ck_seasons_diagnosis_light_default_valid"),
        ),
        sa.CheckConstraint("area_ha > 0", name=op.f("ck_seasons_area_positive")),
        sa.CheckConstraint("harvest_date is null or harvest_date >= sowing_date", name=op.f("ck_seasons_harvest_after_sowing")),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.lot_id"], name=op.f("fk_seasons_lot_id_lots"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("season_id", name=op.f("pk_seasons")),
    )
    op.create_index(op.f("ix_seasons_lot_id"), "seasons", ["lot_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_seasons_lot_id"), table_name="seasons")
    op.drop_table("seasons")
    op.drop_index(op.f("ix_lots_user_id"), table_name="lots")
    op.drop_index(op.f("ix_lots_municipality_id"), table_name="lots")
    op.drop_table("lots")
