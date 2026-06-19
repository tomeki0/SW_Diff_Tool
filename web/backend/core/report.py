"""
Geração do relatório HTML (versão web: retorna string, sem I/O de desktop).

Portado de src/report.py. Diferenças em relação ao original:
  - imports relativos ao pacote core;
  - assets resolvidos contra web/backend/assets/ (não resource_path);
  - logos cacheados em base64 no import (não reprocessa a cada request);
  - gerar_html_report retorna a string HTML (sem tempfile/webbrowser/log_callback).
"""
import os
import html
from pathlib import Path
from datetime import datetime

from .parsing import img_to_base64
from .diff_engine import (
    is_changed,
    process_prop_value,
    calcular_diff_props,
    parse_packages_with_path
)

# ── assets ──────────────────────────────────────────────────────────────────
# Reusa os assets da raiz do repositório (assets/), evitando duplicar binários.
# Permite override por env var (útil no deploy/Vercel) via SWDIFF_ASSETS.
_repo_assets = Path(__file__).resolve().parents[3] / "assets"
ASSETS = Path(os.environ.get("SWDIFF_ASSETS", _repo_assets))
TEMPLATE_PATH = ASSETS / "templates" / "report_template.html"

# logos cacheados (1x no import)
LOGO_POSITIVO_B64 = img_to_base64(ASSETS / "logo_positivo.png")
LOGO_ANDROID_B64 = img_to_base64(ASSETS / "logo_android.png")


def classificar_por_path(path):
    if not path:
        return "unknown"

    if path.startswith("/system_ext"):
        return "system_ext"
    elif path.startswith("/system"):
        return "system"
    elif path.startswith("/vendor"):
        return "vendor"
    elif path.startswith("/product"):
        return "product"
    elif path.startswith("/data"):
        return "data"
    else:
        return "other"


def agrupar_por_partition(lista, path_map):
    grupos = {}

    for pkg in lista:
        path = path_map.get(pkg, "")
        grupo = classificar_por_path(path)

        grupos.setdefault(grupo, []).append(pkg)

    return grupos


def comparar_apks(apk_a: dict, apk_b: dict) -> list:
    alertas = []

    if not apk_a or not apk_b:
        return alertas

    for pkg in set(apk_a.keys()) | set(apk_b.keys()):
        a = apk_a.get(pkg)
        b = apk_b.get(pkg)

        if not a or not b:
            continue

        v1 = a.get("versionName")
        v2 = b.get("versionName")

        if v1 != v2:
            alertas.append(f"⚠ {pkg} mudou versão ({v1} → {v2})")

    return alertas


def gerar_html_report(data, build_a_id, build_b_id, serial_a="", serial_b="") -> str:
    """Monta o relatório HTML completo e retorna como string."""

    # 🔥 ALERTAS APK
    apk_alertas = comparar_apks(
        data.get("apk_info_a", {}),
        data.get("apk_info_b", {})
    )

    # ================= PROPERTIES =================
    props_html = ""
    total_props_diff = 0

    props_items = [
        (categoria, props, calcular_diff_props(props))
        for categoria, props in data['props'].items()
    ]

    props_items.sort(key=lambda item: item[2] == 0)

    for categoria, props, n_diff in props_items:
        if not props:
            continue

        total_props_diff += n_diff

        if n_diff == 0:
            status_html = '<span class="status ok">✓ Idêntico</span>'
            arrow = '▶'
        else:
            status_html = f'<span class="status bad">⚠ {n_diff} mudança{"s" if n_diff > 1 else ""}</span>'
            arrow = '▼'

        rows = ""
        for p in props:
            changed = is_changed(p['a'], p['b'])
            row_class = ' class="row-changed"' if changed else ''

            status_icon = "✔" if not changed else "✖"
            status_class = "status-ok" if not changed else "status-bad"

            val_a_html, val_b_html = process_prop_value(
                p['key'],
                p['a'],
                p['b']
            )

            rows += f"""
            <tr{row_class}>
                <td class="status-cell {status_class}">{status_icon}</td>
                <td>
                    <div style="display:flex; align-items:flex-start; gap:6px;">
                        <span class="prop-key">{p['key']}</span>
                        <button class="btn-focus" onclick="toggleFocus(this)">🔍</button>
                    </div>
                </td>
                <td class="col-a"><div class="value-box">{val_a_html}</div></td>
                <td class="col-b"><div class="value-box">{val_b_html}</div></td>
            </tr>
            """

        body_html = f"""
        <div class="block-body">
            <table>
                <thead><tr>
                    <th class="status-head">Status</th>
                    <th>Property</th>
                    <th class="col-a-head">{build_a_id}</th>
                    <th class="col-b-head">{build_b_id}</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """

        block_class = "block collapsed" if n_diff == 0 else "block expanded"
        has_diff_attr = "true" if n_diff > 0 else "false"

        props_html += f"""
        <div class="{block_class}" data-has-diff="{has_diff_attr}">
            <div class="block-header" onclick="toggleBlock(this)">
                <div class="block-header-left">
                    <h3>{categoria} <span class="collapse-arrow">{arrow}</span></h3>
                </div>
                <div class="block-header-right">
                    {status_html}
                </div>
            </div>
            {body_html}
        </div>
        """

    def diff_packages(pkgs_a, pkgs_b):
        result = []

        all_pkgs = set(pkgs_a.keys()) | set(pkgs_b.keys())

        for pkg in sorted(all_pkgs):
            a = pkgs_a.get(pkg)
            b = pkgs_b.get(pkg)

            if a and not b:
                result.append({"pkg": pkg, "type": "removed", "a": a, "b": ""})

            elif b and not a:
                result.append({"pkg": pkg, "type": "added", "a": "", "b": b})

            elif (a or "").strip() != (b or "").strip():
                result.append({
                    "pkg": pkg,
                    "type": "changed",
                    "a": (a or "").strip(),
                    "b": (b or "").strip()
                })

        return result

    # ================= PACKAGES / FEATURES =================
    pkgs_added = data['pkgs']['added']
    pkgs_removed = data['pkgs']['removed']

    pkgs_path_a = parse_packages_with_path(data.get("raw_pkgs_a", ""))
    pkgs_path_b = parse_packages_with_path(data.get("raw_pkgs_b", ""))

    pkgs_diff = diff_packages(pkgs_path_a, pkgs_path_b)

    pkgs_added_grouped = agrupar_por_partition(pkgs_added, pkgs_path_b)
    pkgs_removed_grouped = agrupar_por_partition(pkgs_removed, pkgs_path_a)

    feats_added = data['feats']['added']
    feats_removed = data['feats']['removed']

    from html import escape as html_escape

    def render_feature_items(items):
        out = ""
        for item in sorted(items):
            out += f'<div class="pkg-item">{html_escape(item)}</div>'
        return out

    def render_grouped(grupos):
        out = ""
        for grupo, items in grupos.items():
            if not items:
                continue

            out += f"""
            <div class="pkg-group" data-category="{grupo}">
                <div class="pkg-group-title">
                    {grupo.upper()} <span class="count">({len(items)})</span>
                </div>
            """

            for pkg in sorted(items):
                out += f'<div class="pkg-item">{html_escape(pkg)}</div>'

            out += "</div>"

        return out

    pkgs_cards_html = f"""
    <div class="pkg-container">

        <div class="pkg-card">
            <div class="pkg-header" onclick="togglePkg(this)">
                {build_a_id} — {len(pkgs_removed)} exclusivos
            </div>
            <div class="pkg-body">
                {render_grouped(pkgs_removed_grouped)}
            </div>
        </div>

        <div class="pkg-card">
            <div class="pkg-header" onclick="togglePkg(this)">
                {build_b_id} — {len(pkgs_added)} exclusivos
            </div>
            <div class="pkg-body">
                {render_grouped(pkgs_added_grouped)}
            </div>
        </div>

    </div>
    """

    feats_table = f"""
    <div class="pkg-root">

        <div class="pkg-toolbar">

            <input
            type="text"
            id="featSearch"
            placeholder="🔍 Buscar feature..."
            oninput="filterFeatures(this)"
            class="pkg-search"
            >

            <div id="featSearchCount">
            Resultados: {len(feats_added) + len(feats_removed)}
            </div>

        </div>

        <div class="pkg-container">

            <div class="pkg-card">
                <div class="pkg-header" onclick="togglePkg(this)">
                    {build_a_id} — {len(feats_removed)} exclusivas
                </div>

                <div class="pkg-body">
                    <div class="pkg-group">
                        <div class="pkg-group-title">
                            FEATURES ({len(feats_removed)})
                        </div>

                        <div class="pkg-list">
                            {render_feature_items(feats_removed)}
                        </div>
                    </div>
                </div>
            </div>

            <div class="pkg-card">
                <div class="pkg-header" onclick="togglePkg(this)">
                    {build_b_id} — {len(feats_added)} exclusivas
                </div>

                <div class="pkg-body">
                    <div class="pkg-group">
                        <div class="pkg-group-title">
                            FEATURES ({len(feats_added)})
                        </div>

                        <div class="pkg-list">
                            {render_feature_items(feats_added)}
                        </div>
                    </div>
                </div>
            </div>

        </div>

    </div>
    """

    # ================= TEMPLATE =================
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    html_content = template

    html_content = html_content.replace("{{LOGO_PATH}}", LOGO_POSITIVO_B64)
    html_content = html_content.replace("{{LOGO_ANDROID_PATH}}", LOGO_ANDROID_B64)

    html_content = html_content.replace("{{BUILD_A}}", build_a_id)
    html_content = html_content.replace("{{BUILD_B}}", build_b_id)

    html_content = html_content.replace("{{SN_A}}", serial_a or "—")
    html_content = html_content.replace("{{SN_B}}", serial_b or "—")

    html_content = html_content.replace("{{DATE}}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    html_content = html_content.replace("{{TOTAL_PROPS}}", str(total_props_diff))
    html_content = html_content.replace("{{PROPS_HTML}}", props_html)

    html_content = html_content.replace("{{TOTAL_PKGS}}", str(len(pkgs_added) + len(pkgs_removed)))
    html_content = html_content.replace("{{PKGS_TABLE}}", pkgs_cards_html)

    html_content = html_content.replace("{{TOTAL_FEATS}}", str(len(feats_added) + len(feats_removed)))
    html_content = html_content.replace("{{FEATS_TABLE}}", feats_table)

    if apk_alertas:
        apk_alerts_html = '<div class="apk-alerts">'
        apk_alerts_html += '<div style="font-weight:600; margin-bottom:6px; color:var(--bad-fg);">Alterações críticas:</div>'

        for alerta in apk_alertas:
            apk_alerts_html += f'<div class="apk-alert">{html.escape(alerta)}</div>'

        apk_alerts_html += '</div>'
    else:
        apk_alerts_html = ""

    html_content = html_content.replace("{{APK_ALERTS}}", apk_alerts_html)

    return html_content
