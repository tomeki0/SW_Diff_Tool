"""
Montagem pura do dict de diff consumido por report.gerar_html_report.

Extraído de src/app.py (IMPORTANT_PROPS, RISK_HIGH e a lógica de App.gerar_diff)
e de src/presets.py (extrair_info_apk). Nenhuma dependência de Tk/ADB.
"""
from .parsing import filtrar_props
from .diff_engine import parse_packages_with_path, calcular_diff_props


# Categorias de risco alto (origem: src/app.py:102-107)
RISK_HIGH = {
    "🧬 FINGERPRINT",
    "🔐 Security Patch",
    "🤖 GMS/API",
    "🧬 Prop ID",
}

# Mapa de propriedades importantes por categoria (origem: src/app.py:109-153)
IMPORTANT_PROPS = {
    "📱 IDENTIDADE": [
        "ro.product.device",
        "ro.product.model",
        "ro.product.name"
    ],
    "🧬 FINGERPRINT": [
        "ro.build.fingerprint",
        "ro.bootimage.build.fingerprint",
        "ro.system.build.fingerprint",
        "ro.vendor.build.fingerprint",
        "ro.product.build.fingerprint",
        "ro.odm.build.fingerprint"
    ],
    "🔢 VERSIONAMENTO": [
        "ro.build.version.incremental",
        "ro.build.display.id",
        "ro.build.version.release"
    ],
    "🔐 Security Patch": [
        "ro.build.version.security_patch"
    ],
    "🧱 Base OS": [
        "ro.build.version.base_os"
    ],
    "🤖 GMS/API": [
        "ro.com.google.gmsversion",
        "ro.product.first_api_level"
    ],
    "⚙️ CPU": [
        "ro.product.cpu.abilist32",
        "ro.product.cpu.abilist64"
    ],
    "🧪 BUILD": [
        "ro.build.type"
    ],
    "🧬 Prop ID": [
        "ro.boot.vbmeta.digest"
    ],
    "🔑 Client ID": [
        "ro.com.google.clientidbase",
        "ro.com.google.clientidbase.ms",
        "ro.com.google.clientidbase.vs"
    ]
}

# Pacotes-alvo cujas versões são comparadas (origem: src/presets.py:8-13)
TARGET_PACKAGES = {
    "com.positivo.fota",
    "com.bitdefender.security",
    "com.bitdefender.promo",
    "com.dr.positivo.preload"
}


def extrair_info_apk(pkgs_raw: str) -> dict:
    """Extrai versionName/versionCode dos pacotes-alvo (origem: src/presets.py:138-172)."""
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


def _set_from_features(texto) -> set:
    """Converte a saída de `pm list features` em set (origem: src/app.py:989-1003)."""
    result = set()
    if not isinstance(texto, str):
        return result
    for line in texto.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            try:
                pkg = line.split("=")[-1]
                result.add(pkg)
            except Exception:
                continue
        else:
            result.add(line)
    return result


def build_diff_data(
    props_a, pkgs_a, feats_a,
    props_b, pkgs_b, feats_b,
    build_a_id, build_b_id,
    apk_info_a=None, apk_info_b=None,
) -> dict:
    """Monta o dict `data` consumido por gerar_html_report.

    Recebe as strings brutas por build (props/pkgs/feats) e devolve a estrutura
    com props categorizadas e diffs de packages/features. Função pura, sem I/O.

    `props_*`/`feats_*` podem vir como string (saída de adb) ou já como
    dict/coleção (presets) — `filtrar_props` faz passthrough de dict.
    Origem: src/app.py:1005-1032.
    """
    pkgs_path_a = parse_packages_with_path(pkgs_a) if isinstance(pkgs_a, str) else {}
    pkgs_path_b = parse_packages_with_path(pkgs_b) if isinstance(pkgs_b, str) else {}

    set_pkgs_a = set(pkgs_path_a.keys())
    set_pkgs_b = set(pkgs_path_b.keys())

    feat_a = _set_from_features(feats_a)
    feat_b = _set_from_features(feats_b)

    prop_a = filtrar_props(props_a)
    prop_b = filtrar_props(props_b)

    data = {
        'pkgs':  {'added': sorted(set_pkgs_b - set_pkgs_a), 'removed': sorted(set_pkgs_a - set_pkgs_b)},
        'feats': {'added': sorted(feat_b - feat_a), 'removed': sorted(feat_a - feat_b)},
        'props': {},
        'apk_info_a': apk_info_a if apk_info_a is not None else extrair_info_apk(pkgs_a if isinstance(pkgs_a, str) else ""),
        'apk_info_b': apk_info_b if apk_info_b is not None else extrair_info_apk(pkgs_b if isinstance(pkgs_b, str) else ""),
        'raw_pkgs_a': pkgs_a if isinstance(pkgs_a, str) else "",
        'raw_pkgs_b': pkgs_b if isinstance(pkgs_b, str) else "",
    }

    for categoria, keys in IMPORTANT_PROPS.items():
        data['props'][categoria] = []
        for k in keys:
            va = prop_a.get(k, "---")
            vb = prop_b.get(k, "---")
            data['props'][categoria].append({'key': k, 'a': va, 'b': vb})

    return data


def build_summary(data: dict) -> dict:
    """Conta diffs de props/packages/features a partir do dict de diff."""
    props_diff = sum(
        calcular_diff_props(props)
        for props in data.get('props', {}).values()
    )
    pkgs_diff = len(data['pkgs']['added']) + len(data['pkgs']['removed'])
    feats_diff = len(data['feats']['added']) + len(data['feats']['removed'])
    return {
        "props_diff": props_diff,
        "pkgs_diff": pkgs_diff,
        "feats_diff": feats_diff,
    }
