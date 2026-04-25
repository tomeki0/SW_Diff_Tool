import sys, os, re

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base, relative_path)

def filtrar_props(texto):
    if isinstance(texto, dict):
        return texto

    d = {}
    for line in texto.splitlines():
        m = re.match(r'^\[(.+?)\]: \[(.*)?\]$', line.strip())
        if m:
            k, v = m.group(1), m.group(2)
            d[k] = v
    return d

def img_to_base64(path):
    import base64
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()