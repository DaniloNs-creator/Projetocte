import streamlit as st
import os
import shutil
import zipfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MasterSAF — Automação XML",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS GLOBAL — Aesthetic: Editorial Industrial
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=Syne:wght@400;600;800&display=swap');

#MainMenu, footer, header, [data-testid="collapsedControl"] { visibility: hidden; }

:root {
    --ink:     #0d0f13;
    --paper:   #f5f2eb;
    --cream:   #ede9df;
    --acid:    #c6ff00;
    --rust:    #e84a2b;
    --steel:   #3a3f4b;
    --mist:    #9aa0ad;
    --rule:    #d6d0c4;
    --mono:    'IBM Plex Mono', monospace;
    --sans:    'Syne', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--paper) !important;
    color: var(--ink) !important;
    font-family: var(--sans) !important;
}

/* Remove default padding */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── TOP BAR ── */
.topbar {
    background: var(--ink);
    padding: 0.6rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 3px solid var(--acid);
}
.topbar-brand {
    font-family: var(--mono);
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--paper);
    letter-spacing: 0.22em;
    text-transform: uppercase;
}
.topbar-brand span { color: var(--acid); }
.topbar-meta {
    font-family: var(--mono);
    font-size: 0.62rem;
    color: var(--mist);
    letter-spacing: 0.12em;
}

/* ── MAIN GRID ── */
.main-grid {
    display: grid;
    grid-template-columns: 360px 1fr;
    min-height: calc(100vh - 48px);
}

/* ── LEFT PANEL ── */
.left-panel {
    background: var(--ink);
    padding: 2.2rem 2rem;
    border-right: 1px solid #1f2430;
    display: flex;
    flex-direction: column;
    gap: 0;
}
.panel-eyebrow {
    font-family: var(--mono);
    font-size: 0.58rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--acid);
    margin-bottom: 0.3rem;
}
.panel-title {
    font-family: var(--sans);
    font-size: 1.55rem;
    font-weight: 800;
    color: var(--paper);
    line-height: 1.1;
    margin-bottom: 0.4rem;
}
.panel-desc {
    font-family: var(--mono);
    font-size: 0.66rem;
    color: var(--mist);
    line-height: 1.6;
    margin-bottom: 2rem;
    letter-spacing: 0.02em;
}
.divider {
    border: none;
    border-top: 1px solid #1f2430;
    margin: 1.4rem 0;
}
.field-label {
    font-family: var(--mono);
    font-size: 0.58rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--mist);
    margin-bottom: 0.4rem;
    display: block;
}

/* ── RIGHT PANEL ── */
.right-panel {
    background: var(--paper);
    padding: 2.5rem 3rem;
}
.right-header {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    margin-bottom: 2.5rem;
    padding-bottom: 1.2rem;
    border-bottom: 1px solid var(--rule);
}
.right-title {
    font-family: var(--sans);
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--ink);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.right-subtitle {
    font-family: var(--mono);
    font-size: 0.62rem;
    color: var(--mist);
    letter-spacing: 0.1em;
}

/* ── STAT CARDS ── */
.stats-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--rule);
    border: 1px solid var(--rule);
    margin-bottom: 2.5rem;
}
.stat-card {
    background: var(--paper);
    padding: 1.2rem 1.4rem;
}
.stat-num {
    font-family: var(--mono);
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--ink);
    line-height: 1;
    margin-bottom: 0.3rem;
}
.stat-num.accent { color: var(--rust); }
.stat-label {
    font-family: var(--mono);
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--mist);
}

/* ── LOG TERMINAL ── */
.log-area {
    background: var(--ink);
    border: 1px solid #1f2430;
    border-top: 3px solid var(--acid);
    padding: 1.2rem 1.5rem;
    font-family: var(--mono);
    font-size: 0.72rem;
    color: #7a8494;
    min-height: 180px;
    line-height: 1.8;
    letter-spacing: 0.02em;
}
.log-area .log-ok    { color: var(--acid); }
.log-area .log-err   { color: var(--rust); }
.log-area .log-info  { color: #5b8fff; }
.log-area .log-dim   { color: #3a4050; }
.log-header {
    font-family: var(--mono);
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--mist);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.log-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--acid);
    display: inline-block;
    animation: pulse 1.4s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.2; }
}

/* ── PROGRESS ── */
[data-testid="stProgress"] > div {
    background: #e0dbd0 !important;
    border-radius: 0 !important;
    height: 4px !important;
}
[data-testid="stProgress"] > div > div {
    background: var(--ink) !important;
    border-radius: 0 !important;
}

/* ── INPUTS — LEFT PANEL STYLE ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #0d0f13 !important;
    border: 1px solid #2a2f3d !important;
    border-radius: 0 !important;
    color: #c8cdd6 !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.55rem 0.9rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--acid) !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
    font-family: var(--mono) !important;
    font-size: 0.58rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: #5a6070 !important;
}

/* Hide sidebar completely */
[data-testid="stSidebar"] { display: none !important; }

/* ── BUTTON ── */
.stButton button {
    background: var(--acid) !important;
    color: var(--ink) !important;
    font-family: var(--mono) !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.85rem 2rem !important;
    width: 100% !important;
    transition: all 0.15s !important;
    margin-top: 0.5rem !important;
}
.stButton button:hover {
    background: #d4ff1a !important;
    transform: translateY(-1px) !important;
}
.stButton button:active { transform: translateY(0) !important; }

/* ── DOWNLOAD BUTTON ── */
.stDownloadButton button {
    background: transparent !important;
    color: var(--acid) !important;
    border: 1px solid var(--acid) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.14em !important;
    padding: 0.75rem 1.5rem !important;
    text-transform: uppercase !important;
    margin-top: 1rem !important;
    transition: all 0.15s !important;
}
.stDownloadButton button:hover {
    background: var(--acid) !important;
    color: var(--ink) !important;
}

/* ── ALERTS ── */
[data-testid="stAlert"] {
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.74rem !important;
    background: var(--cream) !important;
    border-left: 3px solid var(--rust) !important;
}

/* ── NUMBER INPUT stepper ── */
[data-testid="stNumberInput"] button {
    background: #1a1e2a !important;
    border: 1px solid #2a2f3d !important;
    border-radius: 0 !important;
    color: #7a8494 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <div class="topbar-brand">MASTER<span>SAF</span> &nbsp;// XML AUTOMATION ENGINE</div>
    <div class="topbar-meta">v2.4.1 &nbsp;·&nbsp; CT-e RECEPTOR &nbsp;·&nbsp; MÓDULO FISCAL</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LAYOUT — Two columns simulated with st.columns
# ─────────────────────────────────────────────
left_col, right_col = st.columns([1.05, 2], gap="small")

# ─────────────────────────────────────────────
# LEFT PANEL — Form
# ─────────────────────────────────────────────
with left_col:
    st.markdown("""
    <div style="background:#0d0f13; padding:2.2rem 2rem 2.5rem; min-height:calc(100vh - 52px); border-right:1px solid #1a1e2a;">
        <div class="panel-eyebrow">Módulo de Captura</div>
        <div class="panel-title">Captura<br>em Massa</div>
        <div class="panel-desc">Extração automatizada de CT-e<br>via portal MasterSAF · até 1000 págs.</div>
        <hr class="divider">
        <div class="panel-eyebrow" style="margin-bottom:1.4rem;">Credenciais de Acesso</div>
    </div>
    """, unsafe_allow_html=True)

    usuario  = st.text_input("Usuário", placeholder="login@empresa.com.br", key="usr")
    senha    = st.text_input("Senha", type="password", placeholder="••••••••", key="pwd")

    st.markdown('<hr class="divider" style="border-top:1px solid #1f2430; margin:1.4rem 0;">', unsafe_allow_html=True)
    st.markdown('<div class="panel-eyebrow" style="color:#5a6070; font-size:0.58rem; letter-spacing:0.18em; font-family:\'IBM Plex Mono\',monospace; text-transform:uppercase;">Período de Consulta</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        data_ini = st.text_input("Data Inicial", value="08/05/2026", key="di")
    with col_b:
        data_fin = st.text_input("Data Final", value="08/05/2026", key="df")

    st.markdown('<hr class="divider" style="border-top:1px solid #1f2430; margin:1.4rem 0;">', unsafe_allow_html=True)
    st.markdown('<div class="panel-eyebrow" style="color:#5a6070; font-size:0.58rem; letter-spacing:0.18em; font-family:\'IBM Plex Mono\',monospace; text-transform:uppercase;">Parâmetros</div>', unsafe_allow_html=True)

    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5)

    st.markdown("<br>", unsafe_allow_html=True)
    iniciar = st.button("⚡ INICIAR AUTOMAÇÃO")

# ─────────────────────────────────────────────
# RIGHT PANEL — Dashboard
# ─────────────────────────────────────────────
with right_col:
    st.markdown("""
    <div style="padding:2.4rem 2.8rem 2rem;">
        <div style="display:flex; align-items:baseline; gap:1rem; margin-bottom:2rem; padding-bottom:1.2rem; border-bottom:1px solid #d6d0c4;">
            <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:800; color:#0d0f13; text-transform:uppercase; letter-spacing:0.06em;">Console de Execução</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; color:#9aa0ad; letter-spacing:0.12em;">REAL-TIME MONITOR</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stat cards (static defaults)
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    with stat_col1:
        st.markdown("""
        <div style="background:#f5f2eb; border:1px solid #d6d0c4; border-top:3px solid #0d0f13; padding:1.2rem 1.4rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:700; color:#0d0f13; line-height:1;">00</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.15em; text-transform:uppercase; color:#9aa0ad; margin-top:0.4rem;">Págs. Processadas</div>
        </div>
        """, unsafe_allow_html=True)
    with stat_col2:
        st.markdown("""
        <div style="background:#f5f2eb; border:1px solid #d6d0c4; border-top:3px solid #c6ff00; padding:1.2rem 1.4rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:700; color:#0d0f13; line-height:1;">000</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.15em; text-transform:uppercase; color:#9aa0ad; margin-top:0.4rem;">Arquivos Capturados</div>
        </div>
        """, unsafe_allow_html=True)
    with stat_col3:
        st.markdown("""
        <div style="background:#f5f2eb; border:1px solid #d6d0c4; border-top:3px solid #e84a2b; padding:1.2rem 1.4rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:700; color:#e84a2b; line-height:1;">IDLE</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.15em; text-transform:uppercase; color:#9aa0ad; margin-top:0.4rem;">Status do Sistema</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Terminal log area
    log_placeholder = st.empty()
    log_placeholder.markdown("""
    <div style="background:#0d0f13; border:1px solid #1f2430; border-top:3px solid #c6ff00; padding:1.2rem 1.5rem; min-height:200px;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; letter-spacing:0.2em; text-transform:uppercase; color:#3a4050; margin-bottom:1rem; display:flex; align-items:center; gap:0.6rem;">
            <span style="width:6px; height:6px; border-radius:50%; background:#3a4050; display:inline-block;"></span>
            SYSTEM LOG — AGUARDANDO INICIALIZAÇÃO
        </div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem; color:#2a3040; line-height:1.9;">
            [ — ] Sistema pronto. Configure as credenciais e clique em iniciar.<br>
            [ — ] Chromium/Selenium em standby.<br>
            [ — ] Diretório de downloads: /tmp/downloads
        </div>
    </div>
    """, unsafe_allow_html=True)

    progress_placeholder = st.empty()
    download_placeholder = st.empty()

# ─────────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────────
def get_driver(download_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--js-flags=--expose-gc")
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)

def render_log(lines, active=True):
    dot_color = "#c6ff00" if active else "#3a4050"
    status_text = "EM EXECUÇÃO" if active else "CONCLUÍDO"
    rows_html = "".join(lines)
    return f"""
    <div style="background:#0d0f13; border:1px solid #1f2430; border-top:3px solid #c6ff00; padding:1.2rem 1.5rem; min-height:200px;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; letter-spacing:0.2em; text-transform:uppercase; color:#9aa0ad; margin-bottom:1rem; display:flex; align-items:center; gap:0.6rem;">
            <span style="width:6px; height:6px; border-radius:50%; background:{dot_color}; display:inline-block;"></span>
            SYSTEM LOG — {status_text}
        </div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem; line-height:1.9;">{rows_html}</div>
    </div>
    """

# ─────────────────────────────────────────────
# LÓGICA PRINCIPAL
# ─────────────────────────────────────────────
if iniciar:
    if not usuario or not senha:
        with right_col:
            st.error("⚠️  Preencha usuário e senha para continuar.")
    else:
        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path):
            shutil.rmtree(dl_path)
        os.makedirs(dl_path)

        logs = []

        def log(msg, kind="dim"):
            color = {"ok": "#c6ff00", "err": "#e84a2b", "info": "#5b8fff", "dim": "#4a5568"}.get(kind, "#4a5568")
            prefix = {"ok": "[OK ]", "err": "[ERR]", "info": "[INF]", "dim": "[ — ]"}.get(kind, "[ — ]")
            logs.append(f'<span style="color:{color};">{prefix}</span> <span style="color:#8896a8;">{msg}</span><br>')
            log_placeholder.markdown(render_log(logs), unsafe_allow_html=True)

        try:
            log("Inicializando driver Chromium/Selenium...", "info")
            driver = get_driver(dl_path)

            log("Acessando portal MasterSAF...", "info")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="enter"]'))
            time.sleep(4)
            log("Autenticação realizada com sucesso.", "ok")

            log("Navegando até Listagem de CT-es...", "info")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(3)

            for xpath, val in [('//*[@id="consultaDataInicial"]', data_ini), ('//*[@id="consultaDataFinal"]', data_fin)]:
                el = driver.find_element(By.XPATH, xpath)
                el.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
                el.send_keys(val)

            log(f"Período definido: {data_ini} → {data_fin}", "info")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
            time.sleep(3)
            log("Base de dados atualizada.", "ok")

            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
            time.sleep(3)

            for i in range(int(qtd_loops)):
                log(f"Processando página {i+1}/{int(qtd_loops)}...", "dim")

                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))

                time.sleep(8)

                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))

                progress_placeholder.progress((i + 1) / int(qtd_loops))
                log(f"Página {i+1} concluída.", "ok")
                time.sleep(4)

            log("Compactando arquivos em ZIP...", "info")
            zip_filename = "/tmp/resultado.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, _, files in os.walk(dl_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            log("Processo finalizado com sucesso!", "ok")
            log_placeholder.markdown(render_log(logs, active=False), unsafe_allow_html=True)

            with open(zip_filename, "rb") as f:
                download_placeholder.download_button(
                    "📥  BAIXAR ARQUIVOS XML (.ZIP)",
                    f,
                    "XMLs_MasterSaf.zip",
                    "application/zip"
                )

            driver.quit()

        except Exception as e:
            log(f"Erro: {e}", "err")
            if 'driver' in locals():
                driver.quit()
