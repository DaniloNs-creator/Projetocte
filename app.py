"""
app.py — Interface Streamlit para automação de download de XMLs do MasterSAF.

Arquitetura:
  • A UI roda na thread principal do Streamlit (obrigatório).
  • O Selenium roda em uma thread separada (daemon) para não bloquear a UI.
  • O progresso é compartilhado via st.session_state, que é atualizado
    pela thread do Selenium e lido a cada re-render do Streamlit.
  • Credenciais são lidas exclusivamente de .streamlit/secrets.toml —
    nunca escritas no código.
"""

import streamlit as st
import threading
import time
import os
from downloader import executar_automacao  # módulo com toda a lógica Selenium

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MasterSAF · XML Downloader",
    page_icon="📥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Visual industrial/terminal com animações de descarga
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow:wght@400;600;700;900&display=swap');

/* Reset e base */
html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif;
    background-color: #0a0c10;
    color: #c9d1d9;
}

/* Fundo com grade sutil */
[data-testid="stAppViewContainer"] {
    background-color: #0a0c10;
    background-image:
        linear-gradient(rgba(33,119,243,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(33,119,243,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* Header */
.hero {
    text-align: center;
    padding: 2rem 0 1rem;
}
.hero-title {
    font-family: 'Barlow', sans-serif;
    font-weight: 900;
    font-size: 2.6rem;
    letter-spacing: -1px;
    color: #f0f6fc;
    line-height: 1;
    margin: 0;
}
.hero-title span {
    color: #2177f3;
}
.hero-sub {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: #3d5a80;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: 6px;
}

/* Card de formulário */
.form-card {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
    margin: 1.2rem 0;
}
.form-card h4 {
    font-size: 0.7rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #2177f3;
    margin: 0 0 1rem;
    font-family: 'Share Tech Mono', monospace;
}

/* Estilo dos inputs nativos do Streamlit */
[data-testid="stDateInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: #0d1117 !important;
    border: 1px solid #21364f !important;
    border-radius: 6px !important;
    color: #c9d1d9 !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* Botão principal */
[data-testid="stButton"] > button {
    width: 100%;
    background: #2177f3;
    color: #fff;
    font-family: 'Barlow', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 1px;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
}
[data-testid="stButton"] > button:hover {
    background: #1a5fcc;
    transform: translateY(-1px);
}
[data-testid="stButton"] > button:disabled {
    background: #1e2d4a;
    color: #3d5a80;
    cursor: not-allowed;
    transform: none;
}

/* ── Animação de descarga (caixas saltando) ── */
@keyframes crate-bounce {
    0%   { transform: translateY(0px) rotate(0deg); }
    30%  { transform: translateY(-14px) rotate(-4deg); }
    60%  { transform: translateY(-6px) rotate(2deg); }
    100% { transform: translateY(0px) rotate(0deg); }
}
@keyframes conveyor {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-100%); }
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 6px #2177f3; }
    50%       { box-shadow: 0 0 20px #2177f3, 0 0 40px #2177f380; }
}

.loading-stage {
    background: #0d1117;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    margin: 1rem 0;
}
.crates-row {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-bottom: 1.5rem;
}
.crate {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    animation: crate-bounce 1s ease-in-out infinite;
    position: relative;
}
.crate::after {
    content: '';
    position: absolute;
    inset: 4px;
    border-radius: 3px;
    background: rgba(255,255,255,0.15);
}
.crate:nth-child(1) { background: #2177f3; animation-delay: 0s; }
.crate:nth-child(2) { background: #1a5fcc; animation-delay: 0.12s; }
.crate:nth-child(3) { background: #0e3d8a; animation-delay: 0.24s; }
.crate:nth-child(4) { background: #1a5fcc; animation-delay: 0.36s; }
.crate:nth-child(5) { background: #2177f3; animation-delay: 0.48s; }

.loading-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #3d5a80;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 1.2rem;
}
.loading-label span {
    color: #2177f3;
    animation: pulse-glow 1.5s ease-in-out infinite;
    display: inline-block;
}

/* Barra de progresso custom */
.prog-wrap {
    background: #0a0c10;
    border: 1px solid #1e2d4a;
    border-radius: 99px;
    height: 10px;
    overflow: hidden;
    margin: 0.5rem 0 1rem;
    animation: pulse-glow 2s ease-in-out infinite;
}
.prog-fill {
    height: 100%;
    background: linear-gradient(90deg, #0e3d8a 0%, #2177f3 50%, #60a5fa 100%);
    border-radius: 99px;
    transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
}

/* Stats em tempo real */
.stats-row {
    display: flex;
    justify-content: space-between;
    margin-top: 0.5rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: #3d5a80;
}
.stats-row .val { color: #60a5fa; }

/* Log terminal */
.terminal {
    background: #0d1117;
    border: 1px solid #1e2d4a;
    border-radius: 8px;
    padding: 1rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    max-height: 160px;
    overflow-y: auto;
    margin-top: 1rem;
}
.log-line { padding: 2px 0; color: #4a6080; }
.log-line.ok  { color: #3fb950; }
.log-line.err { color: #f85149; }
.log-line.info { color: #79c0ff; }
.log-prompt { color: #2177f3; margin-right: 6px; }

/* Botão de download (aparece só no final) */
[data-testid="stDownloadButton"] > button {
    width: 100%;
    background: #1a4731;
    border: 1px solid #3fb950;
    color: #3fb950;
    font-family: 'Barlow', sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    border-radius: 8px;
    padding: 0.85rem;
    transition: all 0.2s;
    animation: pulse-glow-green 1.5s ease-in-out infinite;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #22643e;
    transform: translateY(-2px);
}
@keyframes pulse-glow-green {
    0%, 100% { box-shadow: 0 0 8px #3fb95060; }
    50%       { box-shadow: 0 0 24px #3fb950aa; }
}

/* Divisor */
hr { border-color: #1e2d4a; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ESTADO DA SESSÃO — persiste entre re-renders do Streamlit
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "rodando":      False,   # True enquanto a thread Selenium está ativa
    "concluido":    False,   # True após a thread encerrar (com ou sem erro)
    "pag_atual":    0,       # Página sendo processada agora
    "total_pags":   0,       # Total de páginas configurado pelo usuário
    "total_xmls":   0,       # Contador acumulado de XMLs encontrados
    "logs":         [],      # Lista de dicts {msg, nivel}
    "zip_bytes":    None,    # Conteúdo do ZIP em memória para download
    "erro":         None,    # Mensagem de erro, se houver
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# CABEÇALHO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <p class="hero-title">MASTER<span>SAF</span> · XML</p>
    <p class="hero-sub">Automação de Download · Receptor CTEs</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FORMULÁRIO DE PARÂMETROS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="form-card"><h4>// Parâmetros de Extração</h4>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", format="DD/MM/YYYY",
                                disabled=st.session_state["rodando"])
with col2:
    data_fim = st.date_input("Data Final", format="DD/MM/YYYY",
                             disabled=st.session_state["rodando"])

col3, col4 = st.columns(2)
with col3:
    itens_por_pagina = st.selectbox(
        "Itens por página", ["50", "100", "200", "500"], index=2,
        disabled=st.session_state["rodando"]
    )
with col4:
    qtd_loops = st.number_input(
        "Páginas a processar", min_value=1, max_value=500, value=65, step=1,
        disabled=st.session_state["rodando"]
    )

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS — chamados pela thread do Selenium para atualizar o estado
# ─────────────────────────────────────────────────────────────────────────────
def cb_progresso(pag_atual: int, total_pags: int, xmls_pagina: int,
                 mensagem: str, nivel: str = "info"):
    """
    Atualiza o session_state com os dados mais recentes da execução.
    É seguro chamar de outra thread pois só escreve valores simples.
    """
    st.session_state["pag_atual"]  = pag_atual
    st.session_state["total_pags"] = total_pags
    st.session_state["total_xmls"] += xmls_pagina  # acumula o total
    st.session_state["logs"].append({"msg": mensagem, "nivel": nivel})

def cb_finalizado(zip_bytes: bytes | None, erro: str | None):
    """Chamado ao fim da execução — sucesso ou erro."""
    st.session_state["rodando"]   = False
    st.session_state["concluido"] = True
    st.session_state["erro"]      = erro
    st.session_state["zip_bytes"] = zip_bytes

# ─────────────────────────────────────────────────────────────────────────────
# BOTÃO INICIAR
# ─────────────────────────────────────────────────────────────────────────────
if st.button("▶  Iniciar Extração", disabled=st.session_state["rodando"]):
    # Reseta o estado para nova execução
    st.session_state.update({
        "rodando":    True,
        "concluido":  False,
        "pag_atual":  0,
        "total_pags": int(qtd_loops),
        "total_xmls": 0,
        "logs":       [],
        "zip_bytes":  None,
        "erro":       None,
    })

    # Converte datas para o formato esperado pelo sistema (DDMMAAAA)
    dt_ini_str = data_inicio.strftime("%d%m%Y")
    dt_fim_str = data_fim.strftime("%d%m%Y")

    # Inicia a automação em thread separada — a UI não trava
    t = threading.Thread(
        target=executar_automacao,
        kwargs={
            "dt_ini_str":      dt_ini_str,
            "dt_fim_str":      dt_fim_str,
            "num_itens_pag":   itens_por_pagina,
            "num_loops":       int(qtd_loops),
            "cb_progresso":    cb_progresso,
            "cb_finalizado":   cb_finalizado,
        },
        daemon=True,  # encerra com o processo se o usuário fechar o app
    )
    t.start()
    st.rerun()  # força re-render imediato para mostrar o painel de progresso

# ─────────────────────────────────────────────────────────────────────────────
# PAINEL DE PROGRESSO (visível durante e após a execução)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["rodando"] or st.session_state["concluido"]:

    pag     = st.session_state["pag_atual"]
    total   = st.session_state["total_pags"]
    xmls    = st.session_state["total_xmls"]
    pct     = int((pag / total) * 100) if total else 0

    # Animação de caixas saltando (só enquanto roda)
    if st.session_state["rodando"]:
        st.markdown("""
        <div class="loading-stage">
            <div class="crates-row">
                <div class="crate"></div>
                <div class="crate"></div>
                <div class="crate"></div>
                <div class="crate"></div>
                <div class="crate"></div>
            </div>
            <div class="loading-label">DESCARREGANDO XMLs <span>●</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Barra de progresso
    st.markdown(f"""
    <div class="stats-row">
        <span>Página <span class="val">{pag}</span> de <span class="val">{total}</span></span>
        <span>XMLs encontrados: <span class="val">{xmls}</span></span>
        <span class="val">{pct}%</span>
    </div>
    <div class="prog-wrap">
        <div class="prog-fill" style="width:{pct}%"></div>
    </div>
    """, unsafe_allow_html=True)

    # Terminal de log (últimas 8 entradas, mais recente no topo)
    logs_html = ""
    for entrada in reversed(st.session_state["logs"][-8:]):
        nivel  = entrada.get("nivel", "info")
        classe = "ok" if nivel == "ok" else ("err" if nivel == "err" else "info")
        prompt = "✔" if nivel == "ok" else ("✖" if nivel == "err" else "›")
        logs_html += (
            f'<div class="log-line {classe}">'
            f'<span class="log-prompt">{prompt}</span>{entrada["msg"]}'
            f'</div>'
        )

    st.markdown(f'<div class="terminal">{logs_html}</div>', unsafe_allow_html=True)

    # Re-renderiza a cada 2 s enquanto a thread ainda está viva
    if st.session_state["rodando"]:
        time.sleep(2)
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# RESULTADO FINAL
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["concluido"]:
    st.markdown("<hr>", unsafe_allow_html=True)

    if st.session_state["erro"]:
        # Exibe o erro com detalhes para facilitar a depuração
        st.error(f"❌ Falha na extração: {st.session_state['erro']}")
    else:
        total_xmls = st.session_state["total_xmls"]
        st.success(f"✅ Extração concluída! **{total_xmls} XML(s)** encontrados em "
                   f"{st.session_state['total_pags']} página(s).")

    # Botão de download — habilitado SOMENTE quando o ZIP está pronto
    if st.session_state["zip_bytes"]:
        st.download_button(
            label=f"⬇  Baixar todos os XMLs (.zip)",
            data=st.session_state["zip_bytes"],
            file_name="xmls_mastersaf.zip",
            mime="application/zip",
            use_container_width=True,
        )
