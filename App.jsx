import { useState, useCallback, useRef, useEffect } from "react";

// ── Constantes de cálculo (espelhando calculator.py) ──────────────────────────
const TAX_RATE = 0.085;
const PROCESSING_RATE = 0.085;

const SHIPPING_COSTS = { tênis: 14.95, camiseta: 12.95, moletom: 12.95, jaqueta: 14.95, outros: 14.95 };
const SERVICE_FEES   = { tênis: 50,    camiseta: 20,    moletom: 30,    jaqueta: 40,    outros: 0    };

const CATEGORIES = [
  { key: "tênis",    label: "Tênis",    icon: "👟" },
  { key: "camiseta", label: "Camiseta", icon: "👕" },
  { key: "moletom",  label: "Moletom",  icon: "🧥" },
  { key: "jaqueta",  label: "Jaqueta",  icon: "🧣" },
  { key: "outros",   label: "Outros",   icon: "📦" },
];

const BACKEND_URL = "http://localhost:8000";

// ── Cálculo StockX (instantâneo, no frontend) ─────────────────────────────────
function calcStockX(basePrice, category) {
  const tax        = basePrice * TAX_RATE;
  const processing = basePrice * PROCESSING_RATE;
  const shipping   = SHIPPING_COSTS[category];
  const stockxTotal = basePrice + tax + processing + shipping;
  const quote       = stockxTotal * 0.98 + SERVICE_FEES[category];
  return { tax, processing, shipping, stockxTotal, quote };
}

function calcOther(basePrice, category) {
  const markup = basePrice * 1.15;
  const fee    = SERVICE_FEES[category] === 50 ? 50
               : SERVICE_FEES[category] === 20 ? 20
               : SERVICE_FEES[category] === 30 ? 30
               : SERVICE_FEES[category] === 40 ? 40
               : 0;
  return { markup, fee, quote: markup + fee };
}

// ── Formatadores ──────────────────────────────────────────────────────────────
const usd = (v) => `$${Number(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`;

function buildGlinMessage(quoteUsd, glin, size) {
  const installmentLines = (glin.installments || [])
    .filter(i => i.n <= 12)
    .map(i => `${i.value}\n${i.total}`)
    .join("\n");

  return `💲   ${Math.round(quoteUsd)}      Enviado no size: ${size}

💸 Pix-


${glin.pix}

💳 Cartão-


${glin.card_1x}

${installmentLines}

🤑 Pagamento: Pix, Boleto e Cartão em 12x com juros, clientes NU podem parcelar em até 24x. Também trabalhamos com Wise.

✈️ *Prazo de entrega* - 30 dias úteis em média
🛃 Taxa Alfandegária não inclusa.`.trim();
}

function buildLinkMessage(link) {
  return `👇🏻*Link de Pagamento*👇🏻


${link}

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


Ao prosseguir com o pagamento, você declara estar ciente e de acordo com essas condições.`.trim();
}

// ── Micro componentes ─────────────────────────────────────────────────────────
function Pill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 14px",
        borderRadius: 99,
        border: active ? "1.5px solid #e63946" : "1.5px solid #333",
        background: active ? "#e63946" : "transparent",
        color: active ? "#fff" : "#aaa",
        fontSize: 13,
        fontFamily: "'DM Mono', monospace",
        cursor: "pointer",
        transition: "all .15s",
        letterSpacing: ".03em",
      }}
    >
      {children}
    </button>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} style={{
      background: copied ? "#1a7a3f" : "#1e1e1e",
      color: copied ? "#7fff9a" : "#aaa",
      border: "1px solid #333",
      borderRadius: 6,
      padding: "5px 12px",
      fontSize: 11,
      fontFamily: "'DM Mono', monospace",
      cursor: "pointer",
      transition: "all .2s",
      letterSpacing: ".05em",
    }}>
      {copied ? "✓ COPIADO" : "COPIAR"}
    </button>
  );
}

function MessageBox({ label, text }) {
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:6 }}>
        <span style={{ fontSize:11, color:"#666", fontFamily:"'DM Mono',monospace", letterSpacing:".08em" }}>{label}</span>
        <CopyButton text={text} />
      </div>
      <pre style={{
        background: "#0d0d0d",
        border: "1px solid #222",
        borderRadius: 8,
        padding: "14px 16px",
        fontSize: 12.5,
        color: "#ccc",
        fontFamily: "'DM Mono', monospace",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        margin: 0,
        lineHeight: 1.7,
        maxHeight: 320,
        overflowY: "auto",
      }}>{text}</pre>
    </div>
  );
}

function Spinner() {
  return (
    <span style={{ display:"inline-block", width:14, height:14, border:"2px solid #444", borderTopColor:"#e63946", borderRadius:"50%", animation:"spin .7s linear infinite", marginRight:8, verticalAlign:"middle" }} />
  );
}

// ── App principal ─────────────────────────────────────────────────────────────
export default function App() {
  const [platform, setPlatform] = useState("stockx");
  const [category, setCategory] = useState("tênis");
  const [price, setPrice]       = useState("");
  const [size, setSize]         = useState("");

  const [calc, setCalc]         = useState(null);   // resultado calculado
  const [glin, setGlin]         = useState(null);   // dados da Glin
  const [link, setLink]         = useState(null);   // link de pagamento

  const [loadingGlin, setLoadingGlin] = useState(false);
  const [loadingLink, setLoadingLink] = useState(false);
  const [error, setError]             = useState("");
  const [backendOk, setBackendOk]     = useState(null); // null=checking, true, false

  // Verifica se o backend está rodando
  useEffect(() => {
    fetch(`${BACKEND_URL}/health`, { signal: AbortSignal.timeout(3000) })
      .then(r => r.json())
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  // Cálculo instantâneo ao digitar
  const handleCalculate = useCallback(() => {
    const base = parseFloat(price.replace(",", "."));
    if (!base || base <= 0) { setError("Digite um preço válido."); return; }
    setError("");
    setGlin(null);
    setLink(null);

    const result = platform === "stockx"
      ? calcStockX(base, category)
      : calcOther(base, category);

    setCalc({ ...result, base, platform, category });
  }, [price, category, platform]);

  const handleGlin = useCallback(async () => {
    if (!calc) return;
    setLoadingGlin(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND_URL}/glin/quote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usd_amount: calc.quote, generate_link: false }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Erro na Glin");
      setGlin(await res.json());
    } catch (e) {
      setError(`Erro Glin: ${e.message}`);
    } finally {
      setLoadingGlin(false);
    }
  }, [calc]);

  const handleLink = useCallback(async () => {
    if (!calc) return;
    setLoadingLink(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND_URL}/glin/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usd_amount: calc.quote }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Erro no link");
      const data = await res.json();
      setLink(data.payment_link);
    } catch (e) {
      setError(`Erro Link: ${e.message}`);
    } finally {
      setLoadingLink(false);
    }
  }, [calc]);

  const handleClear = () => {
    setPrice(""); setSize(""); setCalc(null); setGlin(null); setLink(null); setError("");
  };

  const handleKeyDown = (e) => { if (e.key === "Enter") handleCalculate(); };

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0a",
      color: "#e0e0e0",
      fontFamily: "'DM Mono', monospace",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "40px 16px 80px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=Syne:wght@700;800&display=swap');
        * { box-sizing: border-box; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        input:focus { outline: none; border-color: #e63946 !important; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background:#111; } ::-webkit-scrollbar-thumb { background:#333; border-radius:2px; }
      `}</style>

      {/* Header */}
      <div style={{ textAlign:"center", marginBottom:40 }}>
        <div style={{ fontSize:11, letterSpacing:".2em", color:"#555", marginBottom:8 }}>PERSONAL SHOPPING</div>
        <h1 style={{ fontFamily:"'Syne',sans-serif", fontSize:"clamp(28px,6vw,48px)", fontWeight:800, margin:0, letterSpacing:"-.02em", color:"#fff" }}>
          QUOTER<span style={{ color:"#e63946" }}>.</span>
        </h1>
      </div>

      {/* Backend status */}
      {backendOk === false && (
        <div style={{ background:"#1a0a0a", border:"1px solid #5a1a1a", borderRadius:8, padding:"10px 16px", marginBottom:24, fontSize:12, color:"#f88", maxWidth:480, width:"100%" }}>
          ⚠️ Backend offline — cálculos funcionam, mas Glin/Link requer o servidor local.
          <br/><span style={{ color:"#666" }}>$ uvicorn main:app --reload --port 8000</span>
        </div>
      )}

      {/* Card principal */}
      <div style={{
        background: "#111",
        border: "1px solid #222",
        borderRadius: 16,
        padding: "28px 24px",
        width: "100%",
        maxWidth: 480,
        animation: "fadeUp .4s ease",
      }}>

        {/* Plataforma */}
        <div style={{ marginBottom:20 }}>
          <label style={{ fontSize:11, color:"#555", letterSpacing:".1em", display:"block", marginBottom:10 }}>PLATAFORMA</label>
          <div style={{ display:"flex", gap:8 }}>
            <Pill active={platform==="stockx"} onClick={() => { setPlatform("stockx"); setCalc(null); }}>StockX</Pill>
            <Pill active={platform==="outros"}  onClick={() => { setPlatform("outros");  setCalc(null); }}>Outros Sites</Pill>
          </div>
        </div>

        {/* Categoria */}
        <div style={{ marginBottom:20 }}>
          <label style={{ fontSize:11, color:"#555", letterSpacing:".1em", display:"block", marginBottom:10 }}>CATEGORIA</label>
          <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
            {CATEGORIES.map(c => (
              <Pill key={c.key} active={category===c.key} onClick={() => setCategory(c.key)}>
                {c.icon} {c.label}
              </Pill>
            ))}
          </div>
        </div>

        {/* Preço */}
        <div style={{ marginBottom:16 }}>
          <label style={{ fontSize:11, color:"#555", letterSpacing:".1em", display:"block", marginBottom:8 }}>PREÇO BASE (USD)</label>
          <div style={{ position:"relative" }}>
            <span style={{ position:"absolute", left:12, top:"50%", transform:"translateY(-50%)", color:"#555", fontSize:14 }}>$</span>
            <input
              value={price}
              onChange={e => setPrice(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="0.00"
              type="number"
              min="0"
              step="0.01"
              style={{
                width:"100%", background:"#0d0d0d", border:"1px solid #2a2a2a",
                borderRadius:8, padding:"10px 12px 10px 28px", color:"#fff",
                fontSize:16, fontFamily:"'DM Mono',monospace", transition:"border .15s",
              }}
            />
          </div>
        </div>

        {/* Tamanho */}
        <div style={{ marginBottom:24 }}>
          <label style={{ fontSize:11, color:"#555", letterSpacing:".1em", display:"block", marginBottom:8 }}>TAMANHO <span style={{ color:"#444" }}>(opcional)</span></label>
          <input
            value={size}
            onChange={e => setSize(e.target.value)}
            placeholder="ex: 9.5, L, M"
            style={{
              width:"100%", background:"#0d0d0d", border:"1px solid #2a2a2a",
              borderRadius:8, padding:"10px 12px", color:"#fff",
              fontSize:14, fontFamily:"'DM Mono',monospace", transition:"border .15s",
            }}
          />
        </div>

        {/* Botões de ação */}
        <div style={{ display:"flex", gap:10 }}>
          <button onClick={handleCalculate} style={{
            flex:1, background:"#e63946", color:"#fff", border:"none", borderRadius:8,
            padding:"12px 0", fontSize:13, fontFamily:"'DM Mono',monospace",
            fontWeight:500, cursor:"pointer", letterSpacing:".06em",
            transition:"background .15s, transform .1s",
          }}
          onMouseDown={e => e.currentTarget.style.transform="scale(.97)"}
          onMouseUp={e => e.currentTarget.style.transform="scale(1)"}
          >
            ▶ CALCULAR
          </button>
          <button onClick={handleClear} style={{
            background:"transparent", color:"#555", border:"1px solid #2a2a2a",
            borderRadius:8, padding:"12px 16px", fontSize:13, fontFamily:"'DM Mono',monospace",
            cursor:"pointer", transition:"color .15s",
          }}>✕</button>
        </div>

        {error && (
          <div style={{ marginTop:12, color:"#f88", fontSize:12, background:"#1a0a0a", borderRadius:6, padding:"8px 12px" }}>
            {error}
          </div>
        )}
      </div>

      {/* Resultado do cálculo */}
      {calc && (
        <div style={{
          background:"#111", border:"1px solid #222", borderRadius:16,
          padding:"24px", width:"100%", maxWidth:480, marginTop:16,
          animation:"fadeUp .3s ease",
        }}>
          <div style={{ fontSize:11, color:"#555", letterSpacing:".1em", marginBottom:16 }}>DETALHAMENTO</div>

          {calc.platform === "stockx" ? (
            <>
              <Row label="Preço Base"     value={usd(calc.base)} />
              <Row label="Imposto (8.5%)" value={usd(calc.tax)} dim />
              <Row label="Processing"     value={usd(calc.processing)} dim />
              <Row label="Shipping"       value={usd(calc.shipping)} dim />
              <Row label="Total StockX"   value={usd(calc.stockxTotal)} />
            </>
          ) : (
            <>
              <Row label="Preço Base"     value={usd(calc.base)} />
              <Row label="Markup (+15%)"  value={usd(calc.markup)} dim />
              <Row label="Taxa de Serviço" value={usd(calc.fee)} dim />
            </>
          )}

          <div style={{ borderTop:"1px solid #222", marginTop:12, paddingTop:14 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <span style={{ fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:13, color:"#aaa", letterSpacing:".05em" }}>COTAÇÃO FINAL</span>
              <span style={{ fontFamily:"'Syne',sans-serif", fontWeight:800, fontSize:28, color:"#e63946" }}>{usd(calc.quote)}</span>
            </div>
          </div>

          {/* Botões Glin */}
          {backendOk !== false && (
            <div style={{ display:"flex", gap:10, marginTop:16 }}>
              <button onClick={handleGlin} disabled={loadingGlin} style={{
                flex:1, background:"#1a1a2e", color: loadingGlin ? "#555" : "#7eb8f7",
                border:"1px solid #2a2a4a", borderRadius:8, padding:"10px 0",
                fontSize:12, fontFamily:"'DM Mono',monospace", cursor: loadingGlin ? "default" : "pointer",
                letterSpacing:".05em", transition:"all .15s",
              }}>
                {loadingGlin ? <><Spinner/>Consultando...</> : "💬 MENSAGEM GLIN"}
              </button>
              <button onClick={handleLink} disabled={loadingLink} style={{
                flex:1, background:"#0d1f0d", color: loadingLink ? "#555" : "#7fff9a",
                border:"1px solid #1a3a1a", borderRadius:8, padding:"10px 0",
                fontSize:12, fontFamily:"'DM Mono',monospace", cursor: loadingLink ? "default" : "pointer",
                letterSpacing:".05em", transition:"all .15s",
              }}>
                {loadingLink ? <><Spinner/>Gerando...</> : "🔗 LINK PAGAMENTO"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Mensagem Glin */}
      {glin && calc && (
        <div style={{
          background:"#111", border:"1px solid #222", borderRadius:16,
          padding:"24px", width:"100%", maxWidth:480, marginTop:16,
          animation:"fadeUp .3s ease",
        }}>
          <div style={{ fontSize:11, color:"#555", letterSpacing:".1em", marginBottom:4 }}>MENSAGEM DE COTAÇÃO</div>
          <div style={{ fontSize:11, color:"#333", marginBottom:12 }}>
            PIX: <span style={{ color:"#7fff9a" }}>{glin.pix}</span>
            &nbsp;|&nbsp;
            1x: <span style={{ color:"#7eb8f7" }}>{glin.card_1x}</span>
          </div>
          <MessageBox label="MENSAGEM WHATSAPP" text={buildGlinMessage(calc.quote, glin, size)} />
        </div>
      )}

      {/* Link de pagamento */}
      {link && (
        <div style={{
          background:"#111", border:"1px solid #1a3a1a", borderRadius:16,
          padding:"24px", width:"100%", maxWidth:480, marginTop:16,
          animation:"fadeUp .3s ease",
        }}>
          <div style={{ fontSize:11, color:"#555", letterSpacing:".1em", marginBottom:12 }}>LINK GERADO</div>
          <div style={{ background:"#0d1a0d", borderRadius:8, padding:"10px 12px", fontSize:12, color:"#7fff9a", wordBreak:"break-all", marginBottom:12 }}>
            {link}
          </div>
          <MessageBox label="MENSAGEM DE PAGAMENTO" text={buildLinkMessage(link)} />
        </div>
      )}
    </div>
  );
}

function Row({ label, value, dim }) {
  return (
    <div style={{ display:"flex", justifyContent:"space-between", padding:"5px 0", borderBottom:"1px solid #191919" }}>
      <span style={{ fontSize:12, color: dim ? "#444" : "#666" }}>{label}</span>
      <span style={{ fontSize:12, color: dim ? "#555" : "#bbb", fontVariantNumeric:"tabular-nums" }}>{value}</span>
    </div>
  );
}
