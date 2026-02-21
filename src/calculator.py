
import locale
try:
    from glin_automation import get_glin_quote
except ImportError:
    get_glin_quote = None

class QuoteCalculator:
    def __init__(self):
        # Taxas de Imposto e Processamento
        self.tax_rate = 0.085
        self.processing_rate = 0.085
        
        # Custos de Envio (Shipping) por cagetoria
        self.shipping_costs = {
            'tênis': 14.95,
            'camiseta': 12.95,
            'moletom': 12.95,
            'jaqueta': 14.95,
            'outros': 14.95 # Padrão
        }

        # Constantes de Serviço para a fórmula: Total * 0.98 + TaxaFixa
        # Atualizado para Português
        self.service_fees = {
            'tênis': 50.0,
            'camiseta': 20.0,
            'moletom': 30.0,
            'jaqueta': 40.0,
            'outros': 0.0 # Sem taxa extra por padrão
        }

    def calculate(self, base_price, category):
        category = category.lower()
        if category not in self.shipping_costs:
            raise ValueError(f"Categoria desconhecida: {category}")

        # Cálculo StockX
        tax = base_price * self.tax_rate
        processing = base_price * self.processing_rate
        shipping = self.shipping_costs[category]
        
        stockx_total = base_price + tax + processing + shipping
        
        # Cálculo da Cotação Personal Shopping
        # Fórmula: =D2*0.98+Fee
        quote = (stockx_total * 0.98) + self.service_fees[category]

        return {
            'base_price': base_price,
            'stockx_tax': tax,
            'stockx_processing': processing,
            'stockx_shipping': shipping,
            'stockx_total': stockx_total,
            'final_quote': quote
        }

    def calculate_other_platform(self, base_price, category):
        """
        Calcula cotação para outros sites (Non-StockX).
        Fórmula: Price * 1.15 + Fee
        Fees: Tênis=50, Jaqueta/Moletom=30, Camiseta=20, Outros=0
        """
        category = category.lower()
        
        # Markup base de 15%
        base_markup = base_price * 1.15
        
        fee = 0.0
        if category == 'tênis':
            fee = 50.0
        elif category in ['moletom', 'jaqueta']:
            fee = 30.0
        elif category == 'camiseta':
            fee = 20.0
        else:
            fee = 0.0 # Outros / Genérico
            
        final_quote = base_markup + fee
        
        return {
            'base_price': base_price,
            'markup_total': base_markup,
            'fee': fee,
            'final_quote': final_quote
        }

def format_currency(value):
    return f"${value:,.2f}"

def format_glin_message(quote_usd, glin_data, size_str=""):
    """
    Formata a mensagem final baseada nos dados da Glin.
    """
    if not glin_data:
        return "Erro ao obter dados da Glin."

    pix = glin_data.get('pix', 'R$ 0,00')
    card_1x = glin_data.get('card_1x', 'R$ 0,00').strip()
    
    # Constrói o texto das parcelas
    installments_str = ""
    # Filtra de 1x a 12x
    for item in glin_data.get('installments', []):
        if item['n'] <= 12:
            # Formato: "1x R$ 720,53\nTotal: R$ 720,53"
            installments_str += f"{item['value']}\n{item['total']}\n"

    template = f"""
💲   {int(quote_usd)}      Enviado no size: {size_str}

💸 Pix-


{pix}

💳 Cartão-


{card_1x}

{installments_str}
🤑 Pagamento: Pix, Boleto e Cartão em 12x com juros, clientes NU podem parcelar em até 24x. Também trabalhamos com Wise.

✈️ *Prazo de entrega* - 30 dias úteis em média
🛃 Taxa Alfandegária não inclusa.
"""
    return template.strip()

def format_payment_link_message(link):
    """
    Formata a mensagem com o link de pagamento.
    """
    return f"""
👇🏻*Link de Pagamento*👇🏻


{link}

💥Ao finalizar a compra, você concorda automaticamente com os Termos de Uso da TeuCool (disponíveis no app).

💲 Formas de pagamento:
• Pix
• Boleto
• Cartão (em até 12x com juros)
• Wise

⚠️ Importante: devido à variação cambial, o pagamento deve ser realizado em até 1 hora após a geração do link.

‼️ *Atenção* às regras da compra:
• *Compras realizadas via StockX, GOAT e plataformas similares são finais, sem possibilidade de cancelamento ou arrependimento após a confirmação*.
• Caso a plataforma de compra possua política de devolução (ex: Amazon), eventual valor reembolsado pelo vendedor *será convertido em crédito no app TeuCool, não havendo estorno em dinheiro*.
• *Após a confirmação do pagamento e da compra, não realizamos estorno por desistência, arrependimento ou mudança de decisão.*


Ao prosseguir com o pagamento, você declara estar ciente e de acordo com essas condições.
""".strip()

def main():
    calculator = QuoteCalculator()

    print("--- Calculadora StockX Personal Shopping ---")
    
    while True:
        try:
            print("\nCategorias: Sneakers, T-Shirt, Hoodie, Jacket")
            category_input = input("Digite a Categoria (ou 'q' para sair): ").strip().lower()
            if category_input == 'q':
                break
            
            if category_input not in calculator.shipping_costs:
                print("Categoria inválida. Tente novamente.")
                continue

            price_input = input("Preço Base ($): ").replace('$','').strip()
            base_price = float(price_input)

            result = calculator.calculate(base_price, category_input)

            final_quote = result['final_quote']

            print("\n--- Detalhamento ---")
            print(f"Preço Base:       {format_currency(result['base_price'])}")
            print(f"Total Est. StockX:{format_currency(result['stockx_total'])}")
            print(f"=================")
            print(f"COTAÇÃO FINAL:    {format_currency(final_quote)}")
            print(f"=================")
            
            # Integração Glin
            if get_glin_quote:
                opt = input("\nGerar mensagem de cotação Glin? (s/n): ").lower()
                if opt == 's' or opt == 'y': # aceita y ou s
                    size_val = input("Digite o tamanho (ex: 9.5, L): ").strip()
                    print("\nIniciando automação Glin (isso pode levar alguns segundos)...")
                    
                    glin_data = get_glin_quote(final_quote)
                    
                    if glin_data:
                        msg = format_glin_message(final_quote, glin_data, size_val)
                        print("\n" + "="*40)
                        print(msg)
                        print("="*40 + "\n")
                    else:
                        print("Falha ao obter dados da Glin.")

        except ValueError:
            print("Preço inválido.")
        except Exception as e:
            print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()

