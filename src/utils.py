import sys, os, re

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base, relative_path)

# Removido o 'self', pois agora é uma função solta
def filtrar_props(texto):
    d = {}
    for line in texto.splitlines():
        m = re.match(r'^\[(.+?)\]: \[(.*)?\]$', line.strip())
        if m:
            k, v = m.group(1), m.group(2)
            d[k] = v
    return d