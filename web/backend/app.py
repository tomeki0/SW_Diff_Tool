"""
Backend FastAPI do SW Diff Tool (web).

Importado por api/index.py (entrypoint serverless da Vercel) e executável em
dev local com `uvicorn web.backend.app:app --reload`.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# imports do pacote core funcionam tanto rodando de dentro de web/backend
# (api/index.py adiciona web/backend ao sys.path) quanto como módulo.
try:
    from core.build_data import build_diff_data, build_summary
    from core.report import gerar_html_report
    from models import DiffRequest, PresetIn, PresetRename
    from storage import presets as presets_store
    from storage.db import DatabaseNotConfigured
except ImportError:  # quando executado como pacote web.backend
    from web.backend.core.build_data import build_diff_data, build_summary
    from web.backend.core.report import gerar_html_report
    from web.backend.models import DiffRequest, PresetIn, PresetRename
    from web.backend.storage import presets as presets_store
    from web.backend.storage.db import DatabaseNotConfigured


app = FastAPI(title="SW Diff Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # TODO: restringir ao domínio do deploy quando definido
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/diff")
def diff(req: DiffRequest):
    a, b = req.build_a, req.build_b

    data = build_diff_data(
        a.props, a.packages, a.features,
        b.props, b.packages, b.features,
        a.build_id, b.build_id,
        apk_info_a=a.apk_info,
        apk_info_b=b.apk_info,
    )

    html = gerar_html_report(
        data, a.build_id, b.build_id,
        serial_a=a.serial, serial_b=b.serial,
    )

    if req.format == "json":
        return JSONResponse({"html": html, "summary": build_summary(data)})

    return HTMLResponse(html)


# ── PRESETS ─────────────────────────────────────────────────────────────────

def _guard_db(fn):
    """Traduz erros do store para HTTP."""
    try:
        return fn()
    except DatabaseNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
    except presets_store.PresetExists as e:
        raise HTTPException(status_code=409, detail=str(e))
    except presets_store.PresetNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/presets")
def listar_presets():
    return _guard_db(lambda: presets_store.listar())


@app.get("/api/presets/{preset_id}")
def obter_preset(preset_id: str):
    return _guard_db(lambda: presets_store.carregar(preset_id))


@app.post("/api/presets", status_code=201)
def criar_preset(preset: PresetIn):
    return _guard_db(lambda: presets_store.salvar(
        preset.nome, preset.props, preset.build_id,
        packages=preset.packages, features=preset.features, apk_info=preset.apk_info,
    ))


@app.put("/api/presets/{preset_id}")
def renomear_preset(preset_id: str, body: PresetRename):
    return _guard_db(lambda: presets_store.renomear(preset_id, body.nome))


@app.delete("/api/presets/{preset_id}", status_code=204)
def deletar_preset(preset_id: str):
    _guard_db(lambda: presets_store.deletar(preset_id))
    return None
