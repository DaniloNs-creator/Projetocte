"""
app.py — Interface principal do app Streamlit para download de CTEs.
Executa o Selenium em background (thread separada) e exibe animação
de progresso. Ao finalizar, habilita o botão de download do ZIP.
"""

import streamlit as st
import threading
import time
import zipfile
import os
from io import BytesIO
from downloader import executar_download  # lógica de scraping isolada

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="CTE Downloader",
    page_icon="📦",
    layout="centered",
)

# ── CSS customizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: #0d0f1a;
    color: #e2e8f0;
}

/* Título */
.titulo {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.subtitulo {
    color: #64748b;
    font-size: 0.85rem;
    margin-bottom: 2rem;
}

/* Card de status */
.status-card {
    background: #1e2235;
    border: 1px solid #2d3555;
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
}

/* Barra de progresso customizada */
.progress-track {
    background: #0d0f1a;
    border-radius: 99px;
    height: 8px;
    overflow: hidden;
    margin: 0.8rem 0;
}
.progress-bar {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    transition: width 0.4s ease;
}

/* Spinner de descarga */
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-8px); }
}
.box-row {
    display: flex;
    gap: 8px;
    margin: 1rem 0;
}
.box {
    width: 22px; height: 22px;
    background: #38bdf8;
    border-radius: 4px;
    animation: bounce 0.8s ease-in-out infinite;
}
.box:nth-child(2) { animation-delay: 0.1s; background: #60a5fa; }
.box:nth-child(3) { animation-delay: 0.2s; background: #818cf8; }
.box:nth-child(4) { animation-delay: 0.3s; background: #a78bfa; }
.box:nth-child(5) { animation-delay: 0.4s; background: #c084fc; }

/* Badge de log */
.log-line {
    font-size: 0.78rem;
    color: #94a3b8;
    padding: 2px 0;
    border-left: 2px solid #2d3555;
    padding-left: 8px;
    margin: 2px 0;
}
.log-line.ok  { color: #4ade80; border-color: #4ade80; }
.log-line.err { color: #f87171; border-color: #f87171; }
</style>
""", unsafe_allow_html=True)

# ── Cabeçalho ───────────────────────────────────────────────────────────────
st.markdown('<div class="titulo">📦 CTE Downloader</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Automação de download de XMLs — MasterSAF DFE</div>', unsafe_allow_html=True)

# ── Estado de sessão (persiste entre re-renders) ─────────────────────────────
# Usamos st.session_state para guardar progresso, logs e arquivos baixados.
for key, default in {
    "rodando": False,
    "concluido": False,
    "progresso": 0,          # 0–100
    "total_ciclos": 0,
    "ciclo_atual": 0,
    "logs": [],
    "arquivos_zip": None,    # bytes do ZIP final
    "erro": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Formulário de parâmetros ─────────────────────────────────────────────────
with st.expander("⚙️ Parâmetros de busca", expanded=not st.session_state["rodando"]):
    col1, col2 = st.columns(2)
    with col1:
        dt_ini = st.text_input("Data inicial (DDMMAAAA)", value="01092025",
                               help="Formato: dia-mês-ano sem separadores")
    with col2:
        dt_fim = st.text_input("Data final (DDMMAAAA)", value="31012026")

    num_ciclos = st.slider("Número de páginas (ciclos)", min_value=1, max_value=100, value=65)
    itens_pag  = st.selectbox("Itens por página", [50, 100, 200], index=2)

# ── Callbacks de progresso (chamados pela thread do Selenium) ─────────────────
def cb_progresso(ciclo: int, total: int, mensagem: str, nivel: str = "info"):
    """Atualiza o estado de sessão; o Streamlit re-renderiza automaticamente."""
    st.session_state["ciclo_atual"] = ciclo
    st.session_state["total_ciclos"] = total
    st.session_state["progresso"]    = int((ciclo / total) * 100) if total else 0
    entrada = {"msg": mensagem, "nivel": nivel}
    st.session_state["logs"].append(entrada)

def cb_finalizado(caminho_zip: str | None, erro: str | None):
    """Chamado ao término — com sucesso ou falha."""
    st.session_state["rodando"]   = False
    st.session_state["concluido"] = True
    st.session_state["erro"]      = erro

    if caminho_zip and os.path.exists(caminho_zip):
        with open(caminho_zip, "rb") as f:
            st.session_state["arquivos_zip"] = f.read()

# ── Botão de início ──────────────────────────────────────────────────────────
iniciar = st.button(
    "🚀 Iniciar Download",
    disabled=st.session_state["rodando"],
    use_container_width=True,
)

if iniciar and not st.session_state["rodando"]:
    # Reseta estado para nova execução
    st.session_state.update({
        "rodando": True,
        "concluido": False,
        "progresso": 0,
        "ciclo_atual": 0,
        "total_ciclos": num_ciclos,
        "logs": [],
        "arquivos_zip": None,
        "erro": None,
    })

    # Executa o downloader em thread separada para não bloquear a UI
    t = threading.Thread(
        target=executar_download,
        kwargs={
            "dt_ini": dt_ini,
            "dt_fim": dt_fim,
            "num_ciclos": num_ciclos,
            "itens_pag": str(itens_pag),
            "cb_progresso": cb_progresso,
            "cb_finalizado": cb_finalizado,
        },
        daemon=True,  # encerra junto com o processo principal se necessário
    )
    t.start()
    st.rerun()

# ── Painel de progresso (visível durante a execução) ─────────────────────────
if st.session_state["rodando"] or st.session_state["concluido"]:

    ciclo = st.session_state["ciclo_atual"]
    total = st.session_state["total_ciclos"]
    pct   = st.session_state["progresso"]

    st.markdown('<div class="status-card">', unsafe_allow_html=True)

    # Animação de descarga enquanto está rodando
    if st.session_state["rodando"]:
        st.markdown("""
        <div class="box-row">
            <div class="box"></div><div class="box"></div>
            <div class="box"></div><div class="box"></div>
            <div class="box"></div>
        </div>
        """, unsafe_allow_html=True)

    # Barra de progresso
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#94a3b8;">
        <span>Ciclo {ciclo} de {total}</span>
        <span>{pct}%</span>
    </div>
    <div class="progress-track">
        <div class="progress-bar" style="width:{pct}%"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Log das últimas 10 linhas
    logs = st.session_state["logs"][-10:]
    for entrada in reversed(logs):
        nivel = entrada.get("nivel", "info")
        classe = "ok" if nivel == "ok" else ("err" if nivel == "err" else "")
        st.markdown(
            f'<div class="log-line {classe}">{entrada["msg"]}</div>',
            unsafe_allow_html=True,
        )

    # Re-renderiza a cada 2 s enquanto a thread está viva
    if st.session_state["rodando"]:
        time.sleep(2)
        st.rerun()

# ── Resultado final ───────────────────────────────────────────────────────────
if st.session_state["concluido"]:
    if st.session_state["erro"]:
        st.error(f"❌ Erro durante o download: {st.session_state['erro']}")
    else:
        st.success(f"✅ Download concluído! {st.session_state['total_ciclos']} ciclos processados.")

    # Botão de download — só aparece quando há arquivo disponível
    if st.session_state["arquivos_zip"]:
        st.download_button(
            label="⬇️  Baixar todos os XMLs (.zip)",
            data=st.session_state["arquivos_zip"],
            file_name="ctes_xml.zip",
            mime="application/zip",
            use_container_width=True,
        )
