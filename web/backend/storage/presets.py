"""
CRUD de presets no Postgres (Supabase).

Espelha a semântica do src/presets.py original (salvar/listar/carregar/
renomear/deletar/atualizar), trocando o armazenamento em arquivos JSON por uma
tabela `presets`. Nome duplicado continua sendo erro (constraint UNIQUE(nome)).

O bloco `meta` (total_props/packages/features, device) é computado na escrita,
igual ao original.
"""
import json
from psycopg.errors import UniqueViolation

from .db import connect


class PresetExists(Exception):
    """Já existe preset com esse nome (equivalente ao FileExistsError original)."""


class PresetNotFound(Exception):
    pass


def _meta(props: dict, packages: str, features: str) -> dict:
    if not isinstance(props, dict):
        props = {}
    if not isinstance(packages, str):
        packages = ""
    if not isinstance(features, str):
        features = ""
    return {
        "total_props": len(props),
        "total_packages": len(packages.splitlines()),
        "total_features": len(features.splitlines()),
        "device": props.get("ro.product.device", "unknown"),
    }


def _row_to_dict(row: dict) -> dict:
    """Converte uma linha da tabela para o formato usado pela UI/preset."""
    props = row.get("props") or {}
    packages = row.get("packages") or ""
    features = row.get("features") or ""
    apk_info = row.get("apk_info") or {}
    return {
        "id": str(row["id"]),
        "nome": row["nome"],
        "build_id": row["build_id"],
        "data": row["data"].isoformat() if row.get("data") else "",
        "props": props,
        "packages": packages,
        "features": features,
        "apk_info": apk_info,
        "meta": _meta(props, packages, features),
    }


def salvar(nome, props, build_id, packages="", features="", apk_info=None) -> dict:
    if not isinstance(props, dict):
        props = {}
    packages = packages or ""
    features = features or ""
    apk_info = apk_info or {}

    try:
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO presets (nome, build_id, props, packages, features, apk_info)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (nome, build_id, json.dumps(props), packages, features, json.dumps(apk_info)),
            ).fetchone()
        return _row_to_dict(row)
    except UniqueViolation:
        raise PresetExists(f"Preset já existe: {nome}")


def listar() -> list:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM presets ORDER BY data DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def carregar(preset_id: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM presets WHERE id = %s", (preset_id,)
        ).fetchone()
    if not row:
        raise PresetNotFound("Preset não encontrado")
    return _row_to_dict(row)


def deletar(preset_id: str):
    with connect() as conn:
        res = conn.execute("DELETE FROM presets WHERE id = %s", (preset_id,))
    if res.rowcount == 0:
        raise PresetNotFound("Preset não encontrado")


def renomear(preset_id: str, novo_nome: str) -> dict:
    try:
        with connect() as conn:
            row = conn.execute(
                "UPDATE presets SET nome = %s WHERE id = %s RETURNING *",
                (novo_nome, preset_id),
            ).fetchone()
    except UniqueViolation:
        raise PresetExists(f"Já existe preset com nome: {novo_nome}")
    if not row:
        raise PresetNotFound("Preset não encontrado")
    return _row_to_dict(row)


def atualizar(preset_id: str, novos_dados: dict) -> dict:
    """Atualiza apenas os campos enviados (props/packages/features/apk_info)."""
    campos = []
    valores = []
    for key in ["props", "packages", "features", "apk_info"]:
        if key in novos_dados:
            campos.append(f"{key} = %s")
            v = novos_dados[key]
            valores.append(json.dumps(v) if key in ("props", "apk_info") else v)

    if not campos:
        return carregar(preset_id)

    valores.append(preset_id)
    with connect() as conn:
        row = conn.execute(
            f"UPDATE presets SET {', '.join(campos)} WHERE id = %s RETURNING *",
            valores,
        ).fetchone()
    if not row:
        raise PresetNotFound("Preset não encontrado")
    return _row_to_dict(row)
