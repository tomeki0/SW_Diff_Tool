import difflib
import html

def highlight_diff(a, b):
    
    a = a or ""
    b = b or ""
    
    if a == b:
        return html.escape(a), html.escape(b)
    
    matcher = difflib.SequenceMatcher(None, a, b)
    html_a, html_b = "", ""

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        seg_a = a[i1:i2]
        seg_b = b[j1:j2]

        if tag == 'equal':
            html_a += html.escape(seg_a)
            html_b += html.escape(seg_b)
        else:
            if seg_a:
                html_a += f'<mark class="diff-mark">{html.escape(seg_a)}</mark>'
            if seg_b:
                html_b += f'<mark class="diff-mark">{html.escape(seg_b)}</mark>'

    return html_a, html_b


def split_fingerprint_parts(fp):
    try:
        parts = fp.split("/")
        if len(parts) < 5:
            return None

        base = "/".join(parts[:4])
        incremental = parts[4].split(":")[0]
        suffix = fp.split(incremental)[-1]

        return base, incremental, suffix
    except:
        return None
    
def process_prop_value(key, val_a, val_b):
    changed = is_changed(val_a, val_b)

    if not changed:
        return html.escape(val_a or ""), html.escape(val_b or "")

    key_lower = key.lower()

    is_simple = any(k in key_lower for k in [
        "ro.build.version.incremental",
        "ro.build.display.id",
        "ro.build.version.base_os"
    ])

    is_fingerprint = "fingerprint" in key_lower

    if is_simple:
        return highlight_diff(val_a, val_b)

    elif is_fingerprint:
        pa = split_fingerprint_parts(val_a)
        pb = split_fingerprint_parts(val_b)

        if pa and pb and pa[0] == pb[0]:
            base = pa[0]
            inc_a = pa[1]
            inc_b = pb[1]
            suffix = pa[2]

            return (
                f"{html.escape(base)}/<mark class='diff-mark'>{html.escape(inc_a)}</mark>{html.escape(suffix)}",
                f"{html.escape(base)}/<mark class='diff-mark'>{html.escape(inc_b)}</mark>{html.escape(suffix)}"
            )

        return highlight_diff(val_a, val_b)

    return val_a, val_b

def calcular_diff_props(props):
    return sum(
        1 for p in props
        if is_changed(p['a'], p['b'])
    )
    
def is_changed(a, b):
    a = (a or "").strip()
    b = (b or "").strip()
    return a != b and a != '---' and b != '---'

def parse_packages_with_path(raw_text):
    result = {}

    if not raw_text:
        return result

    for line in raw_text.splitlines():
        line = line.strip()

        if not line.startswith("package:"):
            continue

        clean = line.replace("package:", "")

        if "=" not in clean:
            continue  # ignora linhas quebradas

        path_part, pkg = clean.rsplit("=", 1)

        pkg = pkg.strip()
        path_part = path_part.strip()

        if pkg:
            result[pkg] = path_part

    return result