"""
Conexão com o Postgres do Supabase via psycopg (v3).

A string de conexão vem de DATABASE_URL (formato libpq/URL do Supabase:
postgresql://postgres:<senha>@<host>:5432/postgres). Em dev local, carregada
de um .env (python-dotenv) se presente.
"""
import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import psycopg
from psycopg.rows import dict_row


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL não definida — endpoints de preset ficam indisponíveis."""


# Query params que o libpq/psycopg não entende (ex.: `pgbouncer=true`, específico
# do Prisma). Removidos do DSN para evitar "invalid connection option".
_UNSUPPORTED_PARAMS = {"pgbouncer"}


def _sanitize_dsn(dsn: str) -> str:
    parts = urlsplit(dsn)
    if not parts.query:
        return dsn
    kept = [(k, v) for k, v in parse_qsl(parts.query) if k not in _UNSUPPORTED_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise DatabaseNotConfigured(
            "DATABASE_URL não configurada. Defina a connection string do Supabase."
        )
    return _sanitize_dsn(dsn)


def connect():
    """Abre uma conexão psycopg com linhas como dict.

    `prepare_threshold=None` desabilita prepared statements nomeados — necessário
    com o pooler do Supabase em modo transação (pgbouncer), que não os suporta
    entre conexões reaproveitadas.
    """
    return psycopg.connect(
        get_dsn(),
        row_factory=dict_row,
        autocommit=True,
        prepare_threshold=None,
    )
