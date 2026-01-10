import customtkinter as ctk
import pyperclip
import threading
from calculator import QuoteCalculator, format_glin_message, format_currency, format_payment_link_message
from glin_automation import get_glin_quote

import ctypes

# Configurações de Tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

try:
    # Define ID do App para o Windows agrupar ícone corretamente na barra de tarefas
    myappid = 'teucool.personal.shopping.quoter.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

class StockXApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Personal Shopping Quoter 🛍️")
        self.geometry("600x850") # Aumentado altura para caber botões
        
        try:
            self.iconbitmap("icon.ico")
        except:
            pass
        
        # Dados
        self.calculator = QuoteCalculator()
        self.current_quote_data = None
        self.glin_data = None
        
        # Layout
        self.create_widgets()
        
    def create_widgets(self):
        # Cabeçalho
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(pady=20, padx=20, fill="x")
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Personal Shopping Quoter 🛍️", 
            font=("Roboto", 24, "bold")
        )
        self.title_label.pack(pady=10)

        # Área de Input (Entrada de Dados)
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=20, fill="x")
        
        # Fonte (StockX vs Outros)
        self.source_label = ctk.CTkLabel(self.input_frame, text="Origem:", font=("Roboto", 14))
        self.source_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.source_var = ctk.StringVar(value="stockx")
        self.source_seg = ctk.CTkSegmentedButton(
            self.input_frame,
            values=["StockX", "Outros Sites"],
            variable=self.source_var,
            command=self.update_source_ui
        )
        self.source_seg.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")

        # Categoria (Traduzida e com 'Outros')
        self.cat_label = ctk.CTkLabel(self.input_frame, text="Categoria:", font=("Roboto", 14))
        self.cat_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.category_var = ctk.StringVar(value="Tênis")
        self.category_seg = ctk.CTkSegmentedButton(
            self.input_frame, 
            values=["Tênis", "Camiseta", "Moletom", "Jaqueta", "Outros"],
            command=self.update_category,
            variable=self.category_var
        )
        self.category_seg.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Preço Base
        self.price_label = ctk.CTkLabel(self.input_frame, text="Preço Base ($):", font=("Roboto", 14))
        self.price_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.price_entry = ctk.CTkEntry(self.input_frame, placeholder_text="ex: 180")
        self.price_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Tamanho (Opcional inicialmente)
        self.size_label = ctk.CTkLabel(self.input_frame, text="Tamanho:", font=("Roboto", 14))
        self.size_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.size_entry = ctk.CTkEntry(self.input_frame, placeholder_text="ex: 9.5, L")
        self.size_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        self.input_frame.grid_columnconfigure(1, weight=1)

        # Botões de Ação
        self.btn_frame = ctk.CTkFrame(self)
        self.btn_frame.pack(pady=10, padx=20, fill="x")
        
        self.calc_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Calcular Cotação", 
            command=self.calculate_quote,
            font=("Roboto", 14, "bold"),
            height=40
        )
        self.calc_btn.pack(pady=10, padx=10, fill="x")
        
        self.glin_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Gerar Link Glin & Mensagem 🚀", 
            command=self.start_glin_automation,
            font=("Roboto", 14, "bold"),
            fg_color="green",
            hover_color="darkgreen",
            height=40,
            state="disabled" # Desabilitado até calcular
        )
        self.glin_btn.pack(pady=5, padx=10, fill="x")

        self.generate_link_var = ctk.BooleanVar(value=False)
        self.link_chk = ctk.CTkCheckBox(
            self.btn_frame, 
            text="Gerar Link de Pagamento Final 🔗", 
            variable=self.generate_link_var,
            font=("Roboto", 12)
        )
        self.link_chk.pack(pady=5)

        # Área de Saída (Output)
        self.output_textbox = ctk.CTkTextbox(self, width=500, height=200, font=("Consolas", 12))
        self.output_textbox.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Rodapé (Ações Finais)
        # Rodapé (Ações Finais)
        # Usar padding bottom maior e fill X garante que fique fixo embaixo
        self.footer_frame = ctk.CTkFrame(self)
        self.footer_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        
        self.copy_btn = ctk.CTkButton(
            self.footer_frame, 
            text="Copiar Mensagem 📋", 
            command=self.copy_to_clipboard,
            state="disabled"
        )
        self.copy_btn.pack(side="left", padx=10, expand=True, fill="x")
        
        self.reset_btn = ctk.CTkButton(
            self.footer_frame, 
            text="Novo Cálculo / Menu 🔄", 
            command=self.reset_app,
            fg_color="gray",
            hover_color="gray30"
        )
        self.reset_btn.pack(side="right", padx=10, expand=True, fill="x")

    def update_category(self, value):
        pass # Apenas atualiza a variável

    def update_source_ui(self, value):
        if value == "StockX":
            self.price_entry.configure(placeholder_text="ex: 180")
        else:
            self.price_entry.configure(placeholder_text="Preço do Site + Shipping")

    def calculate_quote(self):
        try:
            price_text = self.price_entry.get().replace(',', '.')
            if not price_text:
                self.log("Por favor, insira um preço base.")
                return
            
            base_price = float(price_text)
            category = self.category_var.get()
            
            # Calcular
            source = self.source_var.get()
            
            if source == "StockX":
                quote_details = self.calculator.calculate(base_price, category)
                
                # Mostrar Detalhamento
                breakdown = (
                    f"--- Detalhamento para {category} (StockX) ---\n"
                    f"Preço Base:       {format_currency(base_price)}\n"
                    f"Total StockX Est.:{format_currency(quote_details['stockx_total'])}\n"
                    f"=================\n"
                    f"COTAÇÃO FINAL:    {format_currency(quote_details['final_quote'])}\n"
                    f"=================\n"
                )
            else:
                # Outros Sites
                quote_details = self.calculator.calculate_other_platform(base_price, category)
                
                breakdown = (
                    f"--- Detalhamento para {category} (Outros Sites) ---\n"
                    f"Preço Site+Ship:  {format_currency(base_price)}\n"
                    f"Markup (15%):     {format_currency(quote_details['markup_total'])}\n"
                    f"Taxa Fixa:        + {format_currency(quote_details['fee'])}\n"
                    f"=================\n"
                    f"COTAÇÃO FINAL:    {format_currency(quote_details['final_quote'])}\n"
                    f"=================\n"
                )
            
            self.current_quote_data = quote_details
            
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("end", breakdown)
            
            # Habilitar botão da Glin
            self.glin_btn.configure(state="normal")
            self.glin_data = None # Resetar dados antigos
            
        except ValueError:
            self.log("Formato de preço inválido.")

    def start_glin_automation(self):
        if not self.current_quote_data:
            return
            
        size = self.size_entry.get()
        if not size:
            self.log("⚠️ Por favor, insira um tamanho (ex: 9.5) antes de gerar o link.")
            return

        self.glin_btn.configure(state="disabled", text="Processando... ⏳")
        self.log(f"\nIniciando automação para ${self.current_quote_data['final_quote']:.2f}...\n")
        
        gen_link = self.generate_link_var.get()
        # Executa em thread separada para não travar a interface
        threading.Thread(target=self.run_automation_thread, args=(self.current_quote_data['final_quote'], size, gen_link), daemon=True).start()

    def run_automation_thread(self, amount, size, generate_link):
        try:
            # Passa a função de log via wrapper para ser segura em threads
            # Idealmente usa-se self.after para manipular GUI, mas para print simples aqui funciona
            
            def safe_log(msg):
                self.after(0, lambda: self.log(msg))
                
            result = get_glin_quote(amount, generate_link=generate_link, log_func=safe_log)
            
            # Atualiza GUI da thread principal
            self.after(0, lambda: self.handle_automation_result(result, amount, size))
        except Exception as e:
            self.after(0, lambda: self.log(f"\nErro: {e}"))
            self.after(0, lambda: self.glin_btn.configure(state="normal", text="Gerar Link Glin & Mensagem 🚀"))

    def handle_automation_result(self, result, amount, size):
        self.glin_btn.configure(state="normal", text="Gerar Link Glin & Mensagem 🚀")
        
        if result:
            self.glin_data = result
            
            # Formata mensagem final
            # Formata mensagem final
            if result.get('payment_link'):
                 # Se tem link de pagamento, usa o template novo
                 message = format_payment_link_message(result['payment_link'])
            else:
                 # Cotação padrão
                 message = format_glin_message(amount, result, size)
            
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("end", message)
            
            self.copy_btn.configure(state="normal")
            self.log("\n✅ Sucesso! Mensagem gerada.")
        else:
            self.log("\n❌ Falha ao obter dados da Glin.")

    def copy_to_clipboard(self):
        text = self.output_textbox.get("1.0", "end")
        pyperclip.copy(text)
        self.copy_btn.configure(text="Copiado! ✅")
        self.after(2000, lambda: self.copy_btn.configure(text="Copiar Mensagem 📋"))

    def reset_app(self):
        self.price_entry.delete(0, "end")
        self.size_entry.delete(0, "end")
        self.output_textbox.delete("1.0", "end")
        self.current_quote_data = None
        self.glin_data = None
        self.glin_btn.configure(state="disabled")
        self.copy_btn.configure(state="disabled")
        self.price_entry.focus()

    def log(self, text):
        self.output_textbox.insert("end", text + "\n")
        self.output_textbox.see("end")

if __name__ == "__main__":
    app = StockXApp()
    app.mainloop()
