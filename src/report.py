import tempfile
import html
import webbrowser
from datetime import datetime

from utils import resource_path, img_to_base64
from diff_engine import is_changed, process_prop_value, calcular_diff_props


def comparar_apks(apk_a: dict, apk_b: dict) -> list[str]:
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


def gerar_html_report(data, build_a_id, build_b_id, log_callback):

    # 🔥 ALERTAS APK
    apk_alertas = comparar_apks(
        data.get("apk_info_a", {}),
        data.get("apk_info_b", {})
    )

    apk_alerts_html = ""
    for alerta in apk_alertas:
        apk_alerts_html += f"""
        <div class="apk-alert">{html.escape(alerta)}</div>
        """

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
                <td><span class="prop-key">{p['key']}</span></td>
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

    # ================= PACKAGES / FEATURES =================
    pkgs_added = data['pkgs']['added']
    pkgs_removed = data['pkgs']['removed']
    feats_added = data['feats']['added']
    feats_removed = data['feats']['removed']

    def build_dual_list(left, right, label_left, label_right):
        max_len = max(len(left), len(right), 1)
        rows = ""
        for i in range(max_len):
            l = left[i] if i < len(left) else ""
            r = right[i] if i < len(right) else ""
            rows += f"<tr><td>{html.escape(l)}</td><td>{html.escape(r)}</td></tr>"
        return f"""
        <table>
        <tr>
            <th>{label_left}</th>
            <th>{label_right}</th>
        </tr>
        {rows}
        </table>
        """

    pkgs_table = build_dual_list(
        pkgs_removed,
        pkgs_added,
        f"Build A  —  {build_a_id}",
        f"Build B  —  {build_b_id}"
    )

    feats_table = build_dual_list(
        [f"- {x}" for x in feats_removed],
        [f"+ {x}" for x in feats_added],
        f"Build A  —  {build_a_id}",
        f"Build B  —  {build_b_id}"
    )

    # ================= TEMPLATE =================
    template_path = resource_path("assets/templates/report_template.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    logo_path = img_to_base64(resource_path("assets/logo_positivo.png"))
    logo_android_path = img_to_base64(resource_path("assets/logo_android.png"))

    html_content = template

    html_content = html_content.replace("{{LOGO_PATH}}", logo_path.replace("\\", "/"))
    html_content = html_content.replace("{{LOGO_ANDROID_PATH}}", logo_android_path.replace("\\", "/"))

    html_content = html_content.replace("{{BUILD_A}}", build_a_id)
    html_content = html_content.replace("{{BUILD_B}}", build_b_id)
    html_content = html_content.replace("{{DATE}}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    html_content = html_content.replace("{{TOTAL_PROPS}}", str(total_props_diff))
    html_content = html_content.replace("{{PROPS_HTML}}", props_html)

    html_content = html_content.replace("{{TOTAL_PKGS}}", str(len(pkgs_added) + len(pkgs_removed)))
    html_content = html_content.replace("{{PKGS_TABLE}}", pkgs_table)

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

    # 🔥 INJETAR ALERTAS
    html_content = html_content.replace("{{APK_ALERTS}}", apk_alerts_html)

    # ================= OUTPUT =================
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)

    webbrowser.open(path)
    log_callback("Relatório gerado com sucesso!", "destaque")