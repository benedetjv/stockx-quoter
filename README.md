# Personal Shopping Quoter 🛍️

## Sobre o Projeto
Este projeto foi desenvolvido com o propósito específico de **otimizar o fluxo de trabalho de Personal Shopping**. 

Anteriormente, o processo dependia de planilhas complexas do Excel para realizar cotações, seguido de um processo manual para inserir esses valores em templates de mensagem e, posteriormente, a geração manual de links de pagamento. Isso era lento, propenso a erros e pouco escalável.

O **Personal Shopping Quoter** automatiza todo esse funil:
1.  **Cotação Instantânea**: Calcula o preço final do produto baseado em regras complexas de taxas, shipping e markup (StockX e Outros sites).
2.  **Integração Glin V2 (API REST)**: O sistema comunica-se diretamente com a API não-oficial da Glin para obter os dados financeiros (Pix e parcelas) instantaneamente. O Playwright (navegador fantasma) atua apenas como fallback para renovar a sessão automaticamente.
3.  **Geração de Link**: Com um clique, o sistema faz o POST em background e gera o Link de Pagamento final na hora.
4.  **Template Pronto**: A mensagem final já sai formatada com valores, parcelas, termos de uso e o link de pagamento, pronta para ser enviada ao cliente.

O objetivo final é transformar um processo de 5-10 minutos em uma operação de **segundos**, permitindo maior volume de atendimento e profissionalismo.

## Estrutura do Projeto

*   `gui_app.py`: Interface Gráfica (GUI) moderna construída com `customtkinter`. Gerencia a interação com o usuário, seleção de categorias e exibição dos resultados.
*   `streamlit_app.py`: Interface Web leve e responsiva, feita com `streamlit`, ideal para uso em celular ou browser desktop.
*   `src/calculator.py`: O "cérebro" matemático. Contém as fórmulas de precificação para StockX (Taxas + Shipping + Markup) e Outros Sites (Markup 15% + Fee Fixa).
*   `src/glin_automation.py`: Módulo de comunicação com a Glin. Usa `requests` para chamadas de API **instantâneas** e `Playwright` apenas como fallback para login de sessão.
*   `.env`: Arquivo de configuração seguro (não versionado) que armazena as credenciais de acesso (`GLIN_EMAIL`, `GLIN_PASSWORD`).

## Como Usar

1.  Clone o repositório.
2.  Crie um arquivo `.env` baseado no `.env.example` e insira suas credenciais da Glin.
3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
4.  Execute a aplicação:
    ```bash
    python gui_app.py
    ```
5.  Para gerar o executável (.exe):
    ```bash
    pyinstaller StockX_Calculator_BR.spec
    ```

## Como rodar em outro PC (Produção)

Para usar o aplicativo em outro computador sem precisar instalar Python ou Git:

1.  Vá até a pasta `dist` gerada pelo PyInstaller.
2.  Copie a pasta inteira **`Personal Shopping Quoter`**.
3.  Cole essa pasta no outro computador (ex: na Área de Trabalho).
4.  **IMPORTANTE**: Certifique-se de que o arquivo `.env` (com suas senhas) esteja dentro dessa pasta, junto com o executável.
    *   Se não estiver, crie um arquivo chamado `.env` e coloque seu email e senha da Glin:
        ```
        GLIN_EMAIL=seu_email@...
        GLIN_PASSWORD=sua_senha...
        ```
        ```
5.  Abra o arquivo `Personal Shopping Quoter.exe`.

---

## Versão Web (Streamlit) 🌐

Se preferir usar via navegador (estilo site):

1.  Certifique-se de ter instalado as dependências:
    ```bash
    pip install streamlit
    ```
2.  Rode o comando:
    ```bash
    streamlit run streamlit_app.py
    ```
3.  O navegador abrirá automaticamente com a interface web. A automação rodará no servidor (seu PC) e o resultado aparecerá na tela.

---

## Deploy no Streamlit Cloud ☁️

Para colocar este app online (acessível de qualquer lugar):

1.  Suba este código para o **GitHub**.
2.  Crie uma conta no [Streamlit Cloud](https://share.streamlit.io/).
3.  Conecte seu GitHub e selecione este repositório.
4.  **IMPORTANTE (Configuração de Senhas):**
    *   O arquivo `.env` **NÃO** vai para o GitHub por segurança.
    *   No painel do Streamlit, vá em **App Settings** -> **Secrets**.
    *   Cole o conteúdo do seu `.env` lá, assim:
        ```toml
        GLIN_EMAIL = "seu_email@..."
        GLIN_PASSWORD = "sua_senha..."
        ```
5.  Clique em **Deploy**! O Streamlit vai instalar tudo (incluindo o navegador) e rodar.
