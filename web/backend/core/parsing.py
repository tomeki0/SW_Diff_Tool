"""
Helpers de parsing/encoding puros (sem dependência de Tk/ADB).

Copiados de src/utils.py (filtrar_props, img_to_base64). As demais funções do
utils.py original (resource_path, get_base_dir, Tooltip) eram específicas do
desktop/PyInstaller e não são portadas.
"""
import re
import base64


def filtrar_props(texto):
    """Converte a saída de `getprop` (`[chave]: [valor]`) em dict.

    Se já receber um dict (ex.: preset), apenas o retorna.
    """
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
    """Lê um PNG e devolve um data URI base64."""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()
