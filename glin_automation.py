import os
import sys
import time
import re
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

def get_glin_quote(usd_amount, generate_link=False, log_func=None):
    """
    Automatiza Glin.com.br para obter Pix e detalhes de parcelamento no Cartão.
    Retorna um dicionário com strings formatadas ou None se falhar.
    """
    
    def log(msg):
        if log_func:
            log_func(msg)
        else:
            print(msg)

    with sync_playwright() as p:
        # Arquivo de estado de autenticação do usuário
        auth_file = 'state.json'
        
        # Browser Launch Logic (Cloud vs Local)
        browser = None
        try:
            # Check for Linux/Streamlit Cloud environment
            if sys.platform.startswith("linux"):
                log("Ambiente Linux detectado (Cloud). Usando Chromium com args sandbox...")
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
            else:
                # Windows Local: Try Edge first, then Chrome
                try:
                    log("Windows detectado. Tentando abrir Microsoft Edge...")
                    browser = p.chromium.launch(headless=True, channel="msedge")
                except Exception as e_edge:
                     # Fallback para chrome se edge falhar
                     log(f"Edge não encontrado. Tentando Google Chrome...")
                     browser = p.chromium.launch(headless=True, channel="chrome")
        except Exception as e_launch:
             log(f"Erro crítico ao lançar navegador: {e_launch}")
             return None

        if not browser:
             return None

        context = browser.new_context(storage_state=auth_file if os.path.exists(auth_file) else None)
        page = context.new_page()

        try:
            log("Acessando Glin...")
            page.goto("https://glin.com.br/merchant/dashboard/charge", timeout=60000)
            
            # Verifica se login é necessário (redirecionado para login)
            if "login" in page.url:
                if "login" in page.url:
                    log("Fazendo login...")
                    # Aguarda rede acalmar para garantir que página carregou
                    try: 
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except: 
                        pass # Continua mesmo se timeout na rede
                        
                    # Lógica de Login
                    email = os.getenv("GLIN_EMAIL")
                    password = os.getenv("GLIN_PASSWORD")
                    
                    if not email or not password:
                         log("Erro: Credenciais GLIN_EMAIL ou GLIN_PASSWORD não encontradas no .env")
                         return None
                    
                    page.locator("#email").fill(email)
                page.get_by_placeholder("Senha").fill(password)
                page.locator("#submit-btn").click()
                
                # Aguarda dashboard para salvar estado
                # Aguarda dashboard para salvar estado
                try:
                    page.wait_for_url("**/merchant/dashboard/charge", timeout=60000)
                except Exception as e:
                    log(f"Timeout aguardando dashboard. URL atual: {page.url}")
                    raise e
                
                # Salva estado
                context.storage_state(path=auth_file)
                log("Sessão salva.")

            # Lida com Banner de Cookies (AdOpt) de forma robusta
            log("Verificando banner de cookies...")
            try:
                # Tenta aceitar via botão, procurando por textos comuns
                # Seletor genérico para botões dentro de divs com classes de cookie/adopt
                cookie_btn = page.locator("button:has-text('Aceitar'), button:has-text('Concordo'), button:has-text('Allow'), button:has-text('Prosseguir')").first
                
                if cookie_btn.is_visible(timeout=2000): # Reduzido timeout
                    log("Banner de cookies detectado. Clicando em aceitar...")
                    cookie_btn.click()
                    time.sleep(0.5) # Aguarda animação (Reduzido)
                else:
                    # Tenta seletor específico da AdOpt se o genérico falhar
                    adopt_btn = page.locator("[class*='adopt-'] button").first
                    if adopt_btn.is_visible(timeout=1000): # Reduzido timeout
                         log("Banner AdOpt detectado. Clicando...")
                         adopt_btn.click()
                         time.sleep(0.5) # Reduzido
            except Exception as e_cookie:
                log(f"Aviso: Falha ao lidar com cookies (não crítico): {e_cookie}")

            # Insere Valor
            log(f"Cotando para ${usd_amount:.2f}...")
            
            # Seletor robusto para o input de valor
            input_locator = page.locator("input.pl-14, input[placeholder='0.00']").first
            input_locator.wait_for()
            
            # Limpar e Digitar - Otimizado com Eventos JS (Híbrido)
            input_locator.click()
            
            # Tenta fill (instantâneo)
            val_str = f"{usd_amount:.2f}"
            try:
                input_locator.fill(val_str)
                # Força eventos para garantir que o site detecte a mudança (React/Vue/Ang often need this)
                input_locator.evaluate("el => el.dispatchEvent(new Event('input', { bubbles: true }))")
                input_locator.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            except:
                # Fallback se fill falhar
                input_locator.press("Control+A")
                input_locator.press("Backspace")
                input_locator.press_sequentially(val_str, delay=50)

            input_locator.press("Enter")
            
            # Aguarda a label "Pix" aparecer
            try:
                page.locator("text=Pix").first.wait_for(timeout=20000) # Aumentado para 20s (Cloud é lento)
            except:
                log("Timeout aguardando 'Pix'. Tentando reinserir valor...")
                # Retry Input
                input_locator.click()
                input_locator.press("Control+A")
                input_locator.press("Backspace")
                input_locator.press_sequentially(f"{usd_amount:.2f}", delay=150)
                input_locator.press("Enter")
                page.locator("text=Pix").first.wait_for(timeout=20000)

            # Smart Wait: Aguarda o valor do Pix ser calculado (diferente de N/A ou vazio)
            # Loop de verificação rápida (max 3s)
            pix_value = "N/A"
            for _ in range(15): # 15 * 0.2s = 3s max
                content_text = page.locator("body").inner_text()
                # Regex procura por R$ seguido de números (excluindo 0,00 se possível, mas o regex pega qualquer digito)
                match = re.search(r'Pix.*?R\$\s*([\d\.,]+)', content_text, re.IGNORECASE | re.DOTALL)
                if match:
                    raw_val = match.group(1)
                    # Verifica se não é "0,00" ou vazio
                    if raw_val.strip() != "0,00" and any(c.isdigit() for c in raw_val):
                        pix_value = f"R$ {raw_val}"
                        break
                time.sleep(0.2)
            
            # Abre Parcelamento via JS (Maneira mais robusta)
            log("Buscando parcelamento...")
            
            # Executa JS para encontrar, HABILITAR e clicar no elemento
            # Encontramos que o botão frequentemente está 'disabled'. Vamos forçar habilitar.
            clicked = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('button'));
                const target = elements.find(el => 
                    (el.innerText.includes('View installments') || el.innerText.includes('Ver parcelamento'))
                );
                
                if (target) {
                    // Força habilitar
                    target.removeAttribute('disabled');
                    target.classList.remove('disabled');
                    target.click();
                    return true;
                }
                return false;
            }""")
            
            if not clicked:
                # Fallback: seletor específico da análise anterior
                btn = page.locator("button.text-gradient").first
                if btn.is_visible():
                    # Força habilitar via handle
                    btn.evaluate("el => el.removeAttribute('disabled')")
                    btn.click(force=True)
            
            # Aguarda conteúdo do modal
            installments_container = page.locator("div.space-y-1").first
            installments_container.wait_for()

            time.sleep(1) 
            
            # Grab text
            modal_text = installments_container.inner_text()
                
            installments = []
            lines = modal_text.split('\n')
            
            current_installment = None
            
            for line in lines:
                line = line.strip()
                match = re.match(r'(\d+)x\s+(R\$\s*[\d\.,]+)', line)
                if match:
                    if current_installment:
                        installments.append(current_installment)
                    current_installment = {
                        'n': int(match.group(1)),
                        'value': match.group(0),
                        'total': ''
                    }
                elif "Total:" in line and current_installment:
                    current_installment['total'] = line
            
            if current_installment:
                installments.append(current_installment)
            
            installments.sort(key=lambda x: x['n'])
            
            card_value = "N/A"
            if installments and installments[0]['n'] == 1:
                parts = installments[0]['value'].split('R$')
                if len(parts) > 1:
                    card_value = f"R${parts[1]}"
            
            if generate_link:
                log("Gerando link de pagamento...")
                try:
                    # Clica em Continuar no modal (Image 1) - Suporte a PT/EN
                    continue_btn = page.locator("button:has-text('Continuar'), button:has-text('Continue')").first
                    
                    if continue_btn.is_visible():
                        continue_btn.click()
                    else:
                        # Tenta encontrar no rodapé se não for modal
                        # Mas assumimos modal aberto pos 'View Installments'
                        log("Botão Continuar/Continue não visível. Tentando forçar via JS...")
                        
                        # DEBUG: Listar todos os botões visíveis para diagnóstico
                        visible_buttons = page.locator("button:visible").all_inner_texts()
                        log(f"Botões visíveis na página: {visible_buttons}")
                        
                        page.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            const target = btns.find(b => b.innerText.includes('Continuar') || b.innerText.includes('Continue'));
                            if (target) target.click();
                        }""")
                    
                    # Aguarda botão "Criar link de cobrança" (Image 2)
                    create_link_btn = page.locator("button:has-text('Criar link de cobrança'), button:has-text('Create payment link')").first
                    create_link_btn.wait_for(timeout=10000)
                    create_link_btn.click()
                    
                    # Tenta remover banner de cookies novamente se ele reapareceu (AdOpt)
                    log("Verificando se banner de cookies reapareceu antes de ler link...")
                    try:
                        adopt_btn = page.locator("[class*='adopt-'] button, button:has-text('Aceitar'), button:has-text('Allow')").first
                        if adopt_btn.is_visible(timeout=2000):
                            log("Banner AdOpt re-detectado. Forçando fechamento...")
                            adopt_btn.click()
                            time.sleep(1)
                    except:
                        pass

                    # Aguarda "Link gerado!" (Image 3)
                    log("Aguardando link final...")
                    try:
                        # Reduzi o timeout para não prender tanto o usuário se já estiver visível mas o Playwright não detecta
                        page.locator("text=Link gerado!, text=Link generated!").wait_for(timeout=10000)
                    except Exception as e_wait:
                        log(f"Aviso: Timeout aguardando mensagem 'Link gerado'. Tentando extrair mesmo assim...")
                        log(f"Timeout details: {e_wait}")
                        # Não vamos dar raise, vamos tentar extrair o link de qualquer jeito
                        pass

                    # Extrai Link
                    # Tentativa 1: Iterar sobre todos os inputs e verificar o valor (propriedade value)
                    link_text = None
                    try:
                        inputs = page.locator("input[type='text'], input:not([type])").all()
                        log(f"Encontrados {len(inputs)} inputs para verificar link.")
                        
                        for i, inp in enumerate(inputs):
                            if not inp.is_visible():
                                continue
                            val = inp.input_value()
                            if "glinpay.me" in val:
                                link_text = val
                                log(f"Link encontrado no input #{i}: {link_text}")
                                break
                    except Exception as e_inputs:
                        log(f"Erro ao iterar inputs: {e_inputs}")

                    # Tentativa 2: Busca BRUTA via JS (Tree Walker)
                    # Procura em todos os nós de texto da página
                    if not link_text:
                        log("Tentando busca bruta via JS (TreeWalker)...")
                        try:
                            link_text = page.evaluate("""() => {
                                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                                let node;
                                while(node = walker.nextNode()) {
                                    if(node.nodeValue.includes('glinpay.me')) {
                                        return node.nodeValue.trim();
                                    }
                                }
                                return null;
                            }""")
                            if link_text:
                                log(f"Link encontrado via JS Bruto: {link_text}")
                        except Exception as e_js:
                            log(f"Erro na busca JS: {e_js}")
                            
                    # Tentativa 3: Se input falhar, tenta texto puro (Snapshot 3 mostra texto em cinza/label)
                    if not link_text:
                        try:
                            # Procura qualquer elemento contendo glinpay.me (div, span, p)
                            text_el = page.locator("text=glinpay.me").first
                            if text_el.count() > 0:
                                raw_text = text_el.inner_text()
                                if "glinpay.me" in raw_text:
                                    link_text = raw_text.strip()
                                    log(f"Link encontrado via texto cru: {link_text}")
                        except Exception as e_text:
                            log(f"Erro na busca por texto: {e_text}")
                            
                    if link_text:
                        log(f"Link obtido com sucesso: {link_text}")
                        
                        # Opcional: Clica no botão de copiar só para feedback visual na página (se visível)
                        try:
                            copy_icon = page.locator("i.pi.pi-copy").first
                            if copy_icon.is_visible():
                                copy_icon.click()
                        except:
                            pass

                        return {
                            'pix': pix_value,
                            'card_1x': card_value,
                            'installments': installments,
                            'payment_link': link_text
                        }
                    else:
                        log("FALHA FINAL: Link não encontrado em nenhum input ou texto.")
                        # Screenshot final para diagnóstico
                        page.screenshot(path="debug_link_extraction_final.png")
                        
                        # Retorna sem link
                        return {
                            'pix': pix_value,
                            'card_1x': card_value,
                            'installments': installments,
                            'payment_link': None
                        }
                except Exception as e_link:
                    log(f"Erro ao gerar link final: {e_link}")
                    # Retorna dados parciais se falhar link
            
            return {
                'pix': pix_value,
                'card_1x': card_value,
                'installments': installments,
                'payment_link': None
            }

        except Exception as e:
            log(f"Erro na automação: {e}")
            if 'page' in locals():
                try:
                    title = page.title()
                    log(f"Título da página no erro: {title}")
                    
                    # Screenshot absoluto
                    cwd = os.getcwd()
                    shot_path = os.path.join(cwd, "debug_error.png")
                    page.screenshot(path=shot_path)
                    log(f"Screenshot salvo em: {shot_path}")
                    
                    # Conteúdo da página
                    content = page.locator("body").inner_text()
                    log(f"Conteúdo da página (início): {content[:500]}...")
                    
                except Exception as screenshot_err:
                    log(f"Erro ao salvar debug info: {screenshot_err}")
            return None
        finally:
            if 'browser' in locals() and browser:
                browser.close()

if __name__ == "__main__":
    # Test
    res = get_glin_quote(120)
    print(res)
