"""
Compatibility layer for cross-database support (PostgreSQL + SQLite).

Import UUID and JSONB from here instead of sqlalchemy.dialects.postgresql
to ensure compatibility with both SQLite (dev) and PostgreSQL (prod).
"""
from sqlalchemy import Uuid, JSON

# Alias — use the same names as PostgreSQL dialect for easy migration
UUID = Uuid
JSONB = JSON
