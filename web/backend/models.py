"""Schemas Pydantic da API."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class BuildInput(BaseModel):
    """Dados brutos coletados de uma build (saída crua dos comandos adb)."""
    build_id: str = Field(..., description="ro.build.display.id")
    serial: str = ""
    props: str = Field("", description="saída de `getprop`")
    packages: str = Field("", description="saída de `pm list packages -f`")
    features: str = Field("", description="saída de `pm list features`")
    # opcional: apk_info pré-computado (ex.: vindo de preset)
    apk_info: Optional[dict] = None


class DiffRequest(BaseModel):
    build_a: BuildInput
    build_b: BuildInput
    format: Literal["html", "json"] = "html"


class PresetIn(BaseModel):
    nome: str
    build_id: str
    props: dict = {}
    packages: str = ""
    features: str = ""
    apk_info: dict = {}


class PresetRename(BaseModel):
    nome: str
