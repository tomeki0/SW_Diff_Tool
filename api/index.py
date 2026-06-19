"""
Entrypoint serverless da Vercel: expõe o app ASGI da FastAPI.

A Vercel (runtime @vercel/python) detecta a variável `app` como aplicação ASGI.
Adicionamos web/backend ao sys.path para os imports `from core...`/`from models...`
funcionarem dentro do pacote.
"""
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "web", "backend")
)

from app import app  # noqa: E402  (re-exporta o FastAPI)

__all__ = ["app"]
