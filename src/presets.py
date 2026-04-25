from pathlib import Path
import json
from datetime import datetime

PRESETS_DIR = Path.home() / "AndroidSWDiff" / "presets"

TARGET_PACKAGES = {
    "com.positivo.fota",
    "com.bitdefender.security",
    "com.bitdefender.promo",
    "com.dr.positivo.preload"
}


def _sanitize_name(nome: str) -> str:
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in nome).strip()


def salvar(nome, props, build_id, packages=None, features=None, apk_info=None) -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_name(nome)
    filename = PRESETS_DIR / f"{safe_name}.json"

    if filename.exists():
        raise FileExistsError(f"Preset já existe: {safe_name}")

    packages = packages or ""
    features = features or ""
    apk_info = apk_info or {}

    # 🔥 garante tipos seguros
    if not isinstance(props, dict):
        props = {}

    payload = {
        "nome": nome,
        "build_id": build_id,
        "data": datetime.now().isoformat(),

        "props": props,
        "packages": packages,
        "features": features,
        "apk_info": apk_info,

        "meta": {
            "total_props": len(props),
            "total_packages": len(packages.splitlines()) if isinstance(packages, str) else len(packages),
            "total_features": len(features.splitlines()) if isinstance(features, str) else len(features),
            "device": props.get("ro.product.device", "unknown")
        }
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return filename


def listar() -> list[dict]:
    if not PRESETS_DIR.exists():
        return []

    items = []
    for f in PRESETS_DIR.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)

                # 🔥 garante campos mínimos
                data.setdefault("nome", "Sem nome")
                data.setdefault("build_id", "Desconhecido")
                data.setdefault("props", {})
                data.setdefault("packages", "")
                data.setdefault("features", "")
                data.setdefault("apk_info", {})

                data["_file"] = str(f)
                items.append(data)
        except Exception:
            continue

    return sorted(items, key=lambda x: x.get("data", ""), reverse=True)


def carregar(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if "props" not in data or "build_id" not in data:
        raise ValueError("Preset inválido")

    return data


def deletar(filepath: str):
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError("Preset não encontrado")

    path.unlink()


def renomear(filepath: str, novo_nome: str):
    data = carregar(filepath)
    novo_nome_safe = _sanitize_name(novo_nome)

    novo_path = PRESETS_DIR / f"{novo_nome_safe}.json"

    if novo_path.exists():
        raise FileExistsError(f"Já existe preset com nome: {novo_nome}")

    data["nome"] = novo_nome

    with open(novo_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    Path(filepath).unlink()
    return novo_path


def buscar(termo: str):
    termo = termo.lower()

    return [
        p for p in listar()
        if termo in p.get("nome", "").lower()
        or termo in p.get("build_id", "").lower()
    ]


def existe_build(build_id: str) -> bool:
    return any(p.get("build_id") == build_id for p in listar())


def extrair_info_apk(pkgs_raw: str) -> dict:
    resultado = {}

    if not pkgs_raw:
        return resultado

    linhas = pkgs_raw.splitlines()
    current_pkg = None

    for linha in linhas:
        linha = linha.strip()

        if linha.startswith("package:"):
            parts = linha.split("=")
            if len(parts) == 2:
                path = parts[0].replace("package:", "")
                pkg = parts[1]

                if pkg in TARGET_PACKAGES:
                    resultado[pkg] = {
                        "path": path,
                        "versionName": None,
                        "versionCode": None
                    }
                    current_pkg = pkg
                else:
                    current_pkg = None

        elif current_pkg and "versionName=" in linha:
            resultado[current_pkg]["versionName"] = linha.split("=")[1]

        elif current_pkg and "versionCode=" in linha:
            resultado[current_pkg]["versionCode"] = linha.split("=")[1]

    return resultado


def atualizar(filepath: str, novos_dados: dict):
    data = carregar(filepath)

    # 🔥 atualiza apenas campos enviados
    for key in ["props", "packages", "features", "apk_info"]:
        if key in novos_dados:
            data[key] = novos_dados[key]

    props = data.get("props", {})
    packages = data.get("packages", "")
    features = data.get("features", "")

    # 🔥 garante tipos
    if not isinstance(props, dict):
        props = {}

    if not isinstance(packages, str):
        packages = ""

    if not isinstance(features, str):
        features = ""

    # 🔥 atualiza metadata corretamente
    data["meta"] = {
        "total_props": len(props),
        "total_packages": len(packages.splitlines()),
        "total_features": len(features.splitlines()),
        "device": props.get("ro.product.device", "unknown")
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath