import streamlit as st
import os
import traceback
import asyncio
import sys
sys.path.append('src') # Adiciona pasta src ao path para importar modulos

# Bugfix for Playwright on Windows + Streamlit (Asyncio Loop Policy)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Ensure Playwright Browsers are installed (Critical for Cloud)
import subprocess
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    pass

def install_playwright_browsers():
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
         print("Verificando navegadores Playwright...")
         try:
            # Maneira mais garantida de rodar o Playwright install via bash environment
            os.system("playwright install chromium")
            os.system("playwright install-deps chromium")
            print("Navegadores instalados (os.system).")
         except Exception as e:
            print(f"Aviso na instalação de navegadores: {e}")

install_playwright_browsers()

from calculator import QuoteCalculator, format_glin_message, format_currency, format_payment_link_message
from glin_automation import get_glin_quote
from dotenv import load_dotenv

# Load environment variables (credentials)
load_dotenv()

# Page Config
st.set_page_config(
    page_title="Personal Shopping Quoter 🛍️",
    page_icon="🛍️",
    layout="centered"
)

# Title
st.title("Personal Shopping Quoter 🛍️")

# Initialize Calculator
if 'calculator' not in st.session_state:
    st.session_state.calculator = QuoteCalculator()

# Initialize Session State for Results
if 'quote_data' not in st.session_state:
    st.session_state.quote_data = None
if 'glin_result' not in st.session_state:
    st.session_state.glin_result = None
if 'final_message' not in st.session_state:
    st.session_state.final_message = ""

# Callback function for Reset
def reset_callback():
    st.session_state.quote_data = None
    st.session_state.glin_result = None
    st.session_state.final_message = ""
    st.session_state.price_stockx = 0.0
    # Verifica se a chave existe antes de resetar (safety check)
    if 'price_other' in st.session_state:
        st.session_state.price_other = 0.0
    st.session_state.size_input = ""
    st.session_state.category_input = "Tênis"

# --- SIDEBAR (INPUTS) ---
with st.sidebar:
    st.header("1. Configuração")
    
    source = st.radio("Origem:", ["StockX", "Outros Sites"], horizontal=True, key="source_input")
    category = st.selectbox("Categoria:", ["Tênis", "Camiseta", "Moletom", "Jaqueta", "Outros (SEM ENVIO)"], key="category_input")
    
    st.divider()
    
    if source == "StockX":
        price_input = st.number_input("Preço Base ($):", min_value=0.0, format="%.2f", help="Preço do produto na StockX", key="price_stockx")
    else:
        price_input = st.number_input("Preço Site + Shipping ($):", min_value=0.0, format="%.2f", key="price_other")
        
    size_input = st.text_input("Tamanho:", placeholder="ex: 9.5, L, 42", key="size_input")
    
    st.divider()
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        # Calculate Button
        calculate_btn = st.button("Calcular 🧮", use_container_width=True, type="primary")
    with col_btn2:
        # Reset Button (with Callback)
        st.button("Limpar 🗑️", use_container_width=True, on_click=reset_callback)

# --- MAIN AREA ---

# 1. Calculation Logic
if calculate_btn:
    if price_input > 0:
        # Map category name for calculator
        calc_category = category
        if "Outros" in category:
            calc_category = "Outros"

        if source == "StockX":
            quote = st.session_state.calculator.calculate(price_input, calc_category)
        else:
            quote = st.session_state.calculator.calculate_other_platform(price_input, calc_category)
        
        st.session_state.quote_data = quote
        
        # Generate Draft Message
        if source == "StockX":
             st.session_state.final_message = (
                f"--- Detalhamento para {category} (StockX) ---\n"
                f"Preço Base:       {format_currency(price_input)}\n"
                f"Total StockX Est.:{format_currency(quote['stockx_total'])}\n"
                f"=================\n"
                f"COTAÇÃO FINAL:    {format_currency(quote['final_quote'])}\n"
                f"=================\n"
            )
        else:
             st.session_state.final_message = (
                f"--- Detalhamento para {category} (Outros Sites) ---\n"
                f"Preço Site+Ship:  {format_currency(price_input)}\n"
                f"Markup (15%):     {format_currency(quote['markup_total'])}\n"
                f"Taxa Fixa:        + {format_currency(quote['fee'])}\n"
                f"=================\n"
                f"COTAÇÃO FINAL:    {format_currency(quote['final_quote'])}\n"
                f"=================\n"
            )
    else:
        st.toast("⚠️ Insira um preço maior que 0.")

# 2. Results Display
if st.session_state.quote_data:
    st.header("2. Resultado")
    
    # Metrics Row
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Preço Base", format_currency(price_input))
    col_m2.metric("Taxas/Envio", format_currency(st.session_state.quote_data['final_quote'] - price_input))
    col_m3.metric("Final", format_currency(st.session_state.quote_data['final_quote']), delta_color="normal")
    
    with st.expander("Ver Detalhes do Cálculo"):
        st.text(st.session_state.final_message)

    # 3. Glin Automation Section
    st.divider()
    st.header("3. Automação Glin")
    
    col_action, col_opt = st.columns([2, 1])
    
    with col_opt:
        generate_link = st.checkbox("Gerar Link Pagamento 🔗", value=False)
    
    with col_action:
        if st.button("Gerar mensagem 🚀", type="primary", use_container_width=True):
             if not size_input:
                st.error("⚠️ Insira o TAMANHO na barra lateral!")
             else:
                final_price = st.session_state.quote_data['final_quote']
                
                with st.status("Processando...", expanded=True) as status:
                    st.write("Iniciando automação...")
                    log_area = st.empty()
                    logs = []
                    
                    def ui_logger(msg):
                        logs.append(msg)
                        # Mostra as últimas 5 linhas de log para não poluir demais
                        log_area.code("\n".join(logs[-5:]))
                        print(msg) # Mantém no console do servidor também

                    try:
                        # Run Automation
                        result = get_glin_quote(final_price, generate_link=generate_link, log_func=ui_logger)
                    
                        if result:
                            status.update(label="Concluído!", state="complete", expanded=False)
                            st.session_state.glin_result = result
                            
                            # Format Final Message
                            if result.get('payment_link'):
                                 msg = format_payment_link_message(result['payment_link'])
                            else:
                                 msg = format_glin_message(final_price, result, size_input)
                            
                            st.session_state.final_message = msg
                            st.balloons()
                        else:
                            status.update(label="Falha", state="error", expanded=True)
                            st.error("Falha ao obter dados. Veja os logs acima para entender o motivo.")
                    except Exception as e:
                        status.update(label="Erro Crítico", state="error")
                        st.error("Erro na automação:")
                        st.exception(e)

# --- FINAL OUTPUT ---
if st.session_state.glin_result:
    st.divider()
    st.subheader("Mensagem Final (Pronta para Copiar)")
    
    st.code(st.session_state.final_message, language="markdown")
    st.caption("Copie o texto acima e envie para o cliente.")
