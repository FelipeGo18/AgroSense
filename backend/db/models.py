"""Todas las tablas, en un solo lugar: Alembic y las pruebas importan este módulo para verlas todas.

Al crear un módulo nuevo con tablas, agregue aquí su importación; si no, las migraciones no lo ven.
"""

from backend.accounts import farm_models, models, trace_models  # noqa: F401
from backend.db.base import Base

__all__ = ["Base"]
