# Personal Shopping Quoter — Instalação

## Estrutura

```
projeto/
├── backend/
│   ├── main.py            ← FastAPI (este arquivo)
│   ├── glin_automation.py ← seu arquivo existente
│   └── state.json         ← sessão Glin (gerado automaticamente)
└── frontend/
    └── src/
        └── App.jsx        ← interface React
```

---

## 1. Backend (Python + FastAPI)

### Instalar dependências
```bash
pip install fastapi uvicorn python-dotenv requests playwright
```

### Rodar o servidor
```bash
cd backend
uvicorn main:app --reload --port 8000
```

O backend ficará em: http://localhost:8000

---

## 2. Frontend (React)

### Criar o projeto
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
```

### Substituir o App.jsx
Copie o arquivo `frontend/src/App.jsx` para dentro de `frontend/src/App.jsx`.

### Rodar o frontend
```bash
npm run dev
```

O frontend ficará em: http://localhost:5173

---

## Como funciona

| Ação             | Onde executa | Velocidade     |
|------------------|--------------|----------------|
| Calcular cotação | Frontend     | **Instantâneo** |
| Mensagem Glin    | Backend      | ~2-5s (rede)   |
| Link pagamento   | Backend      | ~2-5s (rede)   |

Os cálculos de preço são feitos **100% no browser** — zero delay.
Apenas as chamadas à API da Glin vão para o backend.

---

## Deploy (opcional)

- **Frontend**: Netlify, Vercel (gratuito)
- **Backend**: Railway, Render, VPS própria

Lembre de atualizar `BACKEND_URL` no `App.jsx` para a URL do backend em produção.
