"""
Backend FastAPI do SW Diff Tool (web).

Importado por api/index.py (entrypoint serverless da Vercel) e executável em
dev local com `uvicorn web.backend.app:app --reload`.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# imports do pacote core funcionam tanto rodando de dentro de web/backend
# (api/index.py adiciona web/backend ao sys.path) quanto como módulo.
try:
    from core.build_data import build_diff_data, build_summary
    from core.report import gerar_html_report
except ImportError:  # quando executado como pacote web.backend
    from web.backend.core.build_data import build_diff_data, build_summary
    from web.backend.core.report import gerar_html_report

try:
    from models import DiffRequest
except ImportError:
    from web.backend.models import DiffRequest


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
