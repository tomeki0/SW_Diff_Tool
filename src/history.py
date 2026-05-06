from pathlib import Path
import json
from datetime import datetime

HISTORY_DIR = Path.home() / "AndroidSWDiff" / "historico"
HISTORY_FILE = HISTORY_DIR / "history.json"


def _load() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items: list):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def registrar(build_a: str, build_b: str, serial_a: str, serial_b: str, report_path: str):
    """Adiciona uma entrada no histórico."""
    items = _load()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "build_a": build_a,
        "build_b": build_b,
        "device_a": serial_a or "—",
        "device_b": serial_b or "—",
        "report_path": report_path,
    }
    items.insert(0, entry)  # mais recente primeiro
    _save(items)
    return entry


def listar() -> list:
    return _load()


def deletar(index: int):
    items = _load()
    if 0 <= index < len(items):
        items.pop(index)
        _save(items)


def limpar():
    _save([])