"""
Personal Shopping Quoter - Backend FastAPI
Execute: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

# Adiciona o diretório pai ao path para importar glin_automation
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from glin_automation import get_glin_quote
    GLIN_AVAILABLE = True
except ImportError:
    GLIN_AVAILABLE = False
    print("Aviso: glin_automation não encontrado. Coloque o arquivo na mesma pasta.")

app = FastAPI(title="Personal Shopping Quoter API", version="1.0.0")

# CORS - permite o frontend React conectar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique o domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modelos ──────────────────────────────────────────────────────────────────

class GlinRequest(BaseModel):
    usd_amount: float
    generate_link: bool = False

class GlinResponse(BaseModel):
    pix: str
    card_1x: str
    installments: list
    payment_link: Optional[str] = None

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "glin_available": GLIN_AVAILABLE}


@app.post("/glin/quote", response_model=GlinResponse)
def glin_quote(req: GlinRequest):
    if not GLIN_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="glin_automation.py não encontrado. Coloque-o na mesma pasta do main.py."
        )

    logs = []
    def log_func(msg):
        logs.append(msg)
        print(msg)

    result = get_glin_quote(
        usd_amount=req.usd_amount,
        generate_link=req.generate_link,
        log_func=log_func
    )

    if not result:
        raise HTTPException(status_code=502, detail="Falha ao obter cotação da Glin.")

    return result


@app.post("/glin/link")
def glin_link(req: GlinRequest):
    """Gera apenas o link de pagamento."""
    if not GLIN_AVAILABLE:
        raise HTTPException(status_code=503, detail="glin_automation.py não encontrado.")

    req.generate_link = True
    result = get_glin_quote(usd_amount=req.usd_amount, generate_link=True)

    if not result or not result.get("payment_link"):
        raise HTTPException(status_code=502, detail="Falha ao gerar link de pagamento.")

    return {"payment_link": result["payment_link"]}
