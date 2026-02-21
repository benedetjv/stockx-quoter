import os
import sys
import json
import time
import re
import requests
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

BASE_URL = "https://www.glin.com.br"
GLINPAY_BASE = "https://glinpay.me"

# ──────────────────────────────────────────────
# Helpers de sessão / cookies
# ──────────────────────────────────────────────

def _get_state_file():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "state.json")


def _load_cookies_from_state():
    """
    Lê o state.json (formato Playwright storage_state) e extrai
    os cookies como um dicionário {name: value}.
    """
    state_file = _get_state_file()
    if not os.path.exists(state_file):
        return {}
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        cookies = {}
        for c in state.get("cookies", []):
            cookies[c["name"]] = c["value"]
        return cookies
    except Exception:
        return {}


def _save_cookies_to_state(cookies_dict):
    """
    Salva um dicionário de cookies de volta ao state.json no formato
    Playwright storage_state (coluna mínima necessária para re-uso).
    """
    state_file = _get_state_file()
    # Tenta preservar o estado existente (localStorage etc.)
    existing = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    cookie_list = []
    for name, value in cookies_dict.items():
        cookie_list.append({
            "name": name,
            "value": value,
            "domain": ".glin.com.br",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        })

    existing["cookies"] = cookie_list
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def _build_session(cookies: dict) -> requests.Session:
    """Cria uma requests.Session com os cookies e headers padrão da Glin."""
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": f"{BASE_URL}/merchant/dashboard/charge",
        "Origin": BASE_URL,
    })
    return session


# ──────────────────────────────────────────────
# Login via Playwright (somente quando necessário)
# ──────────────────────────────────────────────

def _playwright_login(log):
    """
    Realiza login no Glin via Playwright e salva o state.json
    com a sessão válida. Retorna os cookies obtidos.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("Erro: playwright não instalado. Execute: pip install playwright")
        return {}

    email = os.getenv("GLIN_EMAIL")
    password = os.getenv("GLIN_PASSWORD")

    if not email or not password:
        log("Erro: GLIN_EMAIL ou GLIN_PASSWORD não definidos no .env")
        return {}

    log("Sessão expirada. Fazendo login via navegador (uma só vez)...")

    with sync_playwright() as p:
        state_file = _get_state_file()

        # Lança browser
        try:
            if sys.platform.startswith("linux"):
                log("Ambiente Linux detectado. Usando Chromium com sandbox desativado...")
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
            else:
                try:
                    browser = p.chromium.launch(headless=True, channel="msedge")
                except Exception:
                    browser = p.chromium.launch(headless=True, channel="chrome")
        except Exception as e:
            log(f"Erro ao lançar navegador: {e}")
            return {}

        context = browser.new_context(
            storage_state=state_file if os.path.exists(state_file) else None
        )
        page = context.new_page()

        try:
            page.goto(f"{BASE_URL}/merchant/dashboard/charge", timeout=60000)

            if "login" in page.url:
                log("Preenchendo credenciais...")
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                page.locator("#email").fill(email)
                page.get_by_placeholder("Senha").fill(password)
                page.locator("#submit-btn").click()

                try:
                    page.wait_for_url("**/merchant/dashboard/charge", timeout=60000)
                except Exception as e:
                    log(f"Timeout aguardando dashboard: {page.url}")
                    raise e

            # Salva estado
            context.storage_state(path=state_file)
            log("Login realizado e sessão salva com sucesso.")

            # Extrai cookies para retornar
            cookies = {}
            for c in context.cookies():
                cookies[c["name"]] = c["value"]
            return cookies

        except Exception as e:
            log(f"Erro durante login: {e}")
            return {}
        finally:
            browser.close()


# ──────────────────────────────────────────────
# Chamadas REST da Glin
# ──────────────────────────────────────────────

def _validate_session(session: requests.Session, log) -> str | None:
    """
    Chama GET /api/user para validar a sessão.
    Retorna o slug do merchant em caso de sucesso, ou None se inválida.
    """
    try:
        resp = session.get(f"{BASE_URL}/api/user", timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            merchants = data.get("merchants", [])
            if merchants:
                slug = merchants[0].get("slug")
                log(f"Sessão válida. Merchant: {slug}")
                return slug
            log("Sessão válida mas sem merchants encontrados.")
            return None
        log(f"Sessão inválida (status {resp.status_code}).")
        return None
    except Exception as e:
        log(f"Erro ao validar sessão: {e}")
        return None


def _fetch_payment_terms(session: requests.Session, slug: str, usd_amount: float, log):
    """
    GET /app/merchants/{slug}/payment-terms/USD{valor}
    Retorna o dict de paymentTerms ou None.
    """
    url = f"{BASE_URL}/app/merchants/{slug}/payment-terms/USD{usd_amount:.2f}"
    log(f"Consultando termos de pagamento: USD {usd_amount:.2f}...")
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("paymentTerms", resp.json())
        log(f"Erro ao buscar payment-terms (status {resp.status_code}): {resp.text[:200]}")
        return None
    except Exception as e:
        log(f"Erro na requisição payment-terms: {e}")
        return None


def _create_payment_link(session: requests.Session, slug: str, usd_amount: float, log):
    """
    POST /app/merchants/{slug}/payment-links
    Retorna a URL do link ou None.
    """
    url = f"{BASE_URL}/app/merchants/{slug}/payment-links"
    payload = {
        "amount": round(usd_amount, 2),
        "currency": "USD",
        "unique": False
    }
    log("Gerando link de pagamento...")
    try:
        resp = session.post(url, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            data = resp.json()
            link_id = data.get("id")
            if link_id:
                link = f"{GLINPAY_BASE}/{slug}/{link_id}/USD{usd_amount:.2f}"
                log(f"Link gerado: {link}")
                return link
            log(f"ID do link não encontrado no response: {data}")
            return None
        log(f"Erro ao gerar link (status {resp.status_code}): {resp.text[:200]}")
        return None
    except Exception as e:
        log(f"Erro na requisição payment-links: {e}")
        return None


# ──────────────────────────────────────────────
# Parsing do response de payment-terms
# ──────────────────────────────────────────────

def _parse_payment_terms(terms: dict, log) -> dict:
    """
    Converte o response JSON da API no mesmo formato de dicionário
    que a função antiga retornava (mantém compatibilidade).
    """
    options = terms.get("options", [])

    pix_value = "N/A"
    card_1x_value = "N/A"
    installments = []

    for option in options:
        method = option.get("method", "")

        if method == "pix":
            total = option.get("totalDueAmount")
            if total is not None:
                # Formata: R$ 10.542,37
                pix_value = _format_brl(total)

        elif method == "card":
            plans = option.get("installmentPlans", [])
            for plan in plans:
                n = plan.get("installments", 0)
                inst_amount = plan.get("installmentAmount")
                total_amount = plan.get("totalAmount")

                if inst_amount is None:
                    continue

                value_str = f"{n}x {_format_brl(inst_amount)}"
                total_str = f"Total: {_format_brl(total_amount)}" if total_amount else ""

                installments.append({
                    "n": n,
                    "value": value_str,
                    "total": total_str
                })

                if n == 1:
                    card_1x_value = _format_brl(inst_amount)

    installments.sort(key=lambda x: x["n"])
    log(f"Cotacao obtida - Pix: {pix_value} | 1x Cartao: {card_1x_value} | {len(installments)} parcelas")

    return {
        "pix": pix_value,
        "card_1x": card_1x_value,
        "installments": installments,
        "payment_link": None  # preenchido depois se solicitado
    }


def _format_brl(value: float) -> str:
    """Formata um float como moeda brasileira: R$ 1.234,56"""
    try:
        # Formata com separadores brasileiros
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except Exception:
        return f"R$ {value}"


# ──────────────────────────────────────────────
# Função pública principal (interface compatível)
# ──────────────────────────────────────────────

def get_glin_quote(usd_amount: float, generate_link: bool = False, log_func=None) -> dict | None:
    """
    Obtém cotação Pix + Cartão da Glin via API REST direta.

    Retorna um dicionário com:
        - pix: str          → "R$ 10.542,37"
        - card_1x: str      → "R$ 10.887,21"
        - installments: list → [{"n": 1, "value": "1x R$ ...", "total": "Total: R$ ..."}, ...]
        - payment_link: str | None

    Retorna None em caso de falha.
    """
    def log(msg):
        if log_func:
            log_func(msg)
        else:
            print(msg)

    # 1. Carrega cookies salvos
    cookies = _load_cookies_from_state()
    session = _build_session(cookies)

    # 2. Valida sessão — se inválida, refaz login
    slug = _validate_session(session, log)

    if not slug:
        log("Sessão inválida. Iniciando login...")
        cookies = _playwright_login(log)
        if not cookies:
            log("Falha no login. Abortando.")
            return None
        session = _build_session(cookies)
        slug = _validate_session(session, log)
        if not slug:
            log("Sessão inválida mesmo após login. Abortando.")
            return None

    # 3. Consulta payment-terms via API (instantâneo)
    terms = _fetch_payment_terms(session, slug, usd_amount, log)
    if not terms:
        return None

    # 4. Parseia resultado
    result = _parse_payment_terms(terms, log)

    # 5. Gera link de pagamento (opcional)
    if generate_link:
        link = _create_payment_link(session, slug, usd_amount, log)
        result["payment_link"] = link

    return result


if __name__ == "__main__":
    # Teste rápido
    res = get_glin_quote(120, generate_link=False)
    print("\n=== Resultado ===")
    if res:
        print(f"Pix:    {res['pix']}")
        print(f"1x:     {res['card_1x']}")
        print(f"Parcelas: {len(res['installments'])}")
        for inst in res["installments"][:3]:
            print(f"  {inst['value']}  {inst['total']}")
        if res.get("payment_link"):
            print(f"Link:   {res['payment_link']}")
    else:
        print("Falha ao obter cotação.")
