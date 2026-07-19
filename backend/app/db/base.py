"""Declarative base for all ORM models.

Kept separate from session.py so models can be imported without creating an
engine or reading configuration (useful for tests and Alembic autogenerate).
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
