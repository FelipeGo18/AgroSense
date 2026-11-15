"""Base de todos los modelos de la base de datos. Cada módulo (cuentas hoy; lo que venga después) define sus tablas sobre ella."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres fijos para llaves, índices y restricciones: así una migración generada en cualquier máquina sale igual.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
