"""
Conexão com o Postgres do Supabase via psycopg (v3).

A string de conexão vem de DATABASE_URL (formato libpq/URL do Supabase:
postgresql://postgres:<senha>@<host>:5432/postgres). Em dev local, carregada
de um .env (python-dotenv) se presente.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import psycopg
from psycopg.rows import dict_row


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL não definida — endpoints de preset ficam indisponíveis."""


def get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise DatabaseNotConfigured(
            "DATABASE_URL não configurada. Defina a connection string do Supabase."
        )
    return dsn


def connect():
    """Abre uma conexão psycopg com linhas como dict."""
    return psycopg.connect(get_dsn(), row_factory=dict_row, autocommit=True)
