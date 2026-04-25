import difflib

def highlight_diff(a, b):
    matcher = difflib.SequenceMatcher(None, a, b)
    html_a, html_b = "", ""

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        seg_a = a[i1:i2]
        seg_b = b[j1:j2]

        if tag == 'equal':
            html_a += seg_a
            html_b += seg_b
        else:
            if seg_a:
                html_a += f'<mark class="diff-mark">{seg_a}</mark>'
            if seg_b:
                html_b += f'<mark class="diff-mark">{seg_b}</mark>'

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
    changed = val_a != val_b and val_a != '---' and val_b != '---'

    if not changed:
        return val_a, val_b

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
                f"{base}/<mark class='diff-mark'>{inc_a}</mark>{suffix}",
                f"{base}/<mark class='diff-mark'>{inc_b}</mark>{suffix}"
            )

        return highlight_diff(val_a, val_b)

    return val_a, val_b

def calcular_diff_props(props):
    return sum(
        1 for p in props
        if p['a'] != p['b'] and p['a'] != "---" and p['b'] != "---"
    )
    
def is_changed(a, b):
    return a != b and a != '---' and b != '---'