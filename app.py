import streamlit as st
import os
import shutil
import zipfile
import time
import re
import subprocess
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

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
# CSS GLOBAL — DARK MODE INDUSTRIAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=Syne:wght@400;600;800&display=swap');

#MainMenu, footer, header, [data-testid="collapsedControl"] { visibility: hidden; }

:root {
    --bg-primary: #0a0c10;
    --bg-secondary: #111318;
    --bg-tertiary: #161920;
    --bg-input: #0d0f14;
    --border-primary: #1f2329;
    --border-secondary: #2a2e35;
    --text-primary: #e4e6ea;
    --text-secondary: #8b8f98;
    --text-muted: #5a5e66;
    --acid: #c6ff00;
    --acid-hover: #d4ff1a;
    --rust: #e84a2b;
    --blue: #5b8fff;
    --amber: #f59e0b;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'Syne', sans-serif;
}

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: var(--sans) !important;
}

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {
    width: 4px;
    height: 4px;
}
::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}
::-webkit-scrollbar-thumb {
    background: var(--border-secondary);
    border-radius: 0;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
}

/* ── TOP BAR ── */
.topbar {
    background: var(--bg-secondary);
    padding: 0.6rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 2px solid var(--acid);
}
.topbar-brand {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: 0.22em;
    text-transform: uppercase;
}
.topbar-brand span { color: var(--acid); }
.topbar-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: var(--text-muted);
    letter-spacing: 0.12em;
}

/* ── PROGRESS BAR ── */
[data-testid="stProgress"] {
    background: transparent !important;
}
[data-testid="stProgress"] > div {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-secondary) !important;
    border-radius: 0 !important;
    height: 6px !important;
    padding: 0 !important;
}
[data-testid="stProgress"] > div > div {
    background: var(--acid) !important;
    border-radius: 0 !important;
}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.55rem 0.9rem !important;
    caret-color: var(--acid) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--acid) !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: var(--text-muted) !important;
    opacity: 0.5 !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.58rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}

/* ── SIDEBAR (hidden) ── */
[data-testid="stSidebar"] { display: none !important; }

/* ── MAIN BUTTON ── */
.stButton button {
    background: var(--acid) !important;
    color: #0a0c10 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.85rem 2rem !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
    margin-top: 0.5rem !important;
    cursor: pointer !important;
}
.stButton button:hover {
    background: var(--acid-hover) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(198, 255, 0, 0.15) !important;
}
.stButton button:active {
    transform: translateY(0) !important;
}

/* ── DOWNLOAD BUTTON ── */
.stDownloadButton button {
    background: transparent !important;
    color: var(--acid) !important;
    border: 1px solid var(--acid) !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.14em !important;
    padding: 0.75rem 1.5rem !important;
    text-transform: uppercase !important;
    margin-top: 1rem !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
}
.stDownloadButton button:hover {
    background: var(--acid) !important;
    color: #0a0c10 !important;
    box-shadow: 0 4px 12px rgba(198, 255, 0, 0.15) !important;
}

/* ── ALERTS / MESSAGES ── */
[data-testid="stAlert"] {
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.74rem !important;
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-secondary) !important;
    border-left: 3px solid var(--rust) !important;
    color: var(--text-primary) !important;
}

/* ── ERROR MESSAGE ── */
.stException {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--rust) !important;
    border-radius: 0 !important;
    color: var(--text-primary) !important;
}

/* ── NUMBER INPUT STEPPER ── */
[data-testid="stNumberInput"] button {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
    color: var(--text-secondary) !important;
    transition: all 0.15s ease !important;
}
[data-testid="stNumberInput"] button:hover {
    background: var(--border-secondary) !important;
    color: var(--text-primary) !important;
}

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
}
[data-testid="stExpander"] details summary {
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── RADIO / CHECKBOX ── */
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
    color: var(--text-primary) !important;
}

/* ── SELECT BOX ── */
[data-testid="stSelectbox"] select {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── DATAFRAME / TABLE ── */
[data-testid="stTable"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
}
[data-testid="stTable"] th {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    border-bottom: 2px solid var(--acid) !important;
}
[data-testid="stTable"] td {
    color: var(--text-secondary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    border-bottom: 1px solid var(--border-primary) !important;
}

/* ── TOOLTIP ── */
[data-testid="stTooltip"] {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-secondary) !important;
    border-radius: 0 !important;
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── MARKDOWN CODE ── */
code {
    background: var(--bg-tertiary) !important;
    color: var(--acid) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    padding: 0.2rem 0.5rem !important;
}

/* ── LINKS ── */
a {
    color: var(--acid) !important;
    text-decoration: none !important;
}
a:hover {
    text-decoration: underline !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <div class="topbar-brand">MASTER<span>SAF</span> &nbsp;// XML AUTOMATION ENGINE</div>
    <div class="topbar-meta">v2.5.0 &nbsp;·&nbsp; CT-e RECEPTOR &nbsp;·&nbsp; MÓDULO FISCAL</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LAYOUT — Two columns
# ─────────────────────────────────────────────
left_col, right_col = st.columns([1.05, 2], gap="small")

# ─────────────────────────────────────────────
# LEFT PANEL — Form (Dark)
# ─────────────────────────────────────────────
with left_col:
    st.markdown("""
    <div style="background:#111318; padding:2.2rem 2rem 1rem; border-right:1px solid #1f2329; min-height:100vh;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.25em; text-transform:uppercase; color:#c6ff00; margin-bottom:0.3rem;">Módulo de Captura</div>
        <div style="font-family:'Syne',sans-serif; font-size:1.55rem; font-weight:800; color:#e4e6ea; line-height:1.1; margin-bottom:0.4rem;">Captura<br>em Massa</div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.66rem; color:#8b8f98; line-height:1.6; margin-bottom:1.6rem;">Extração automatizada de CT-e<br>via portal MasterSAF · até 1000 págs.</div>
        <hr style="border:none; border-top:1px solid #1f2329; margin:0 0 1.2rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">Credenciais de Acesso</div>
    </div>
    """, unsafe_allow_html=True)

    usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="usr")
    senha   = st.text_input("Senha", type="password", placeholder="••••••••", key="pwd")

    st.markdown('<hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">Período de Consulta</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        data_ini = st.text_input("Data Inicial", value="08/05/2026", key="di")
    with col_b:
        data_fin = st.text_input("Data Final", value="08/05/2026", key="df")

    st.markdown('<hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">Parâmetros</div>', unsafe_allow_html=True)

    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5)

    st.markdown("<br>", unsafe_allow_html=True)
    iniciar = st.button("⚡ INICIAR AUTOMAÇÃO")

# ─────────────────────────────────────────────
# RIGHT PANEL — Console (Dark)
# ─────────────────────────────────────────────
with right_col:
    st.markdown("""
    <div style="padding:2.4rem 2.8rem 1.5rem;">
        <div style="display:flex; align-items:baseline; gap:1rem; margin-bottom:1.8rem; padding-bottom:1.2rem; border-bottom:1px solid #1f2329;">
            <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:800; color:#e4e6ea; text-transform:uppercase; letter-spacing:0.06em;">Console de Execução</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; color:#5a5e66; letter-spacing:0.12em;">REAL-TIME MONITOR</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stat cards
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown("""
        <div style="background:#111318; border:1px solid #1f2329; border-top:2px solid #e4e6ea; padding:1.2rem 1.4rem; margin-bottom:1.5rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:700; color:#e4e6ea; line-height:1;">00</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.15em; text-transform:uppercase; color:#5a5e66; margin-top:0.4rem;">Págs. Processadas</div>
        </div>""", unsafe_allow_html=True)
    with sc2:
        st.markdown("""
        <div style="background:#111318; border:1px solid #1f2329; border-top:2px solid #c6ff00; padding:1.2rem 1.4rem; margin-bottom:1.5rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:700; color:#e4e6ea; line-height:1;">000</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.15em; text-transform:uppercase; color:#5a5e66; margin-top:0.4rem;">Arquivos Capturados</div>
        </div>""", unsafe_allow_html=True)
    with sc3:
        st.markdown("""
        <div style="background:#111318; border:1px solid #1f2329; border-top:2px solid #e84a2b; padding:1.2rem 1.4rem; margin-bottom:1.5rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:700; color:#e84a2b; line-height:1;">IDLE</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.15em; text-transform:uppercase; color:#5a5e66; margin-top:0.4rem;">Status do Sistema</div>
        </div>""", unsafe_allow_html=True)

    log_placeholder      = st.empty()
    progress_placeholder = st.empty()
    download_placeholder = st.empty()

    log_placeholder.markdown("""
    <div style="background:#0d0f14; border:1px solid #1f2329; border-top:2px solid #c6ff00; padding:1.2rem 1.5rem; min-height:200px;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:1rem; display:flex; align-items:center; gap:0.6rem;">
            <span style="width:6px;height:6px;border-radius:50%;background:#2a2e35;display:inline-block;"></span>
            SYSTEM LOG — AGUARDANDO INICIALIZAÇÃO
        </div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem; color:#3a3e46; line-height:1.9;">
            [ — ] Sistema pronto. Configure as credenciais e clique em iniciar.<br>
            [ — ] Chrome/Selenium em standby (webdriver-manager).<br>
            [ — ] Diretório de saída: /tmp/downloads
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────

@st.cache_resource
def clear_wdm_cache():
    """Limpa o cache do webdriver-manager para forçar download da versão correta"""
    wdm_cache = os.path.expanduser("~/.wdm")
    if os.path.exists(wdm_cache):
        try:
            shutil.rmtree(wdm_cache)
            return True
        except Exception:
            return False
    return True


def get_chrome_version(binary_path):
    """Obtém a versão do Chrome/Chromium instalado"""
    try:
        result = subprocess.run(
            [binary_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_match = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
        if version_match:
            return version_match.group(0)
        version_match = re.search(r'(\d+)', result.stdout)
        if version_match:
            return version_match.group(0)
    except Exception:
        pass
    return None


def find_chrome_binary():
    """Localiza o executável do Chrome/Chromium no sistema"""
    system = platform.system()
    
    if system == "Windows":
        possible_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
            "C:\\Program Files\\Chromium\\Application\\chrome.exe",
        ]
    elif system == "Linux":
        possible_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
            "/usr/lib/chromium/chromium",
        ]
    elif system == "Darwin":
        possible_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:
        return None
    
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    
    if system != "Windows":
        for browser in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            try:
                result = subprocess.run(
                    ["which", browser],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass
    else:
        try:
            result = subprocess.run(
                ["where", "chrome.exe"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            if result.returncode == 0 and result.stdout.strip():
                paths = result.stdout.strip().split('\n')
                return paths[0].strip()
        except Exception:
            pass
    
    return None


def get_driver(download_path, chrome_binary=None, chrome_version=None):
    """Inicializa o ChromeDriver compatível com a versão do browser"""
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
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--remote-debugging-port=0")
    
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    if chrome_binary:
        chrome_options.binary_location = chrome_binary
    
    clear_wdm_cache()
    
    driver_kwargs = {}
    
    if chrome_binary and "chromium" in os.path.basename(chrome_binary).lower():
        driver_kwargs["chrome_type"] = ChromeType.CHROMIUM
    else:
        driver_kwargs["chrome_type"] = ChromeType.GOOGLE
    
    if chrome_version:
        major_version = chrome_version.split('.')[0]
        driver_kwargs["driver_version"] = major_version
    
    driver_path = ChromeDriverManager(**driver_kwargs).install()
    
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver


def render_log(lines, active=True):
    """Renderiza o log no estilo terminal dark"""
    dot_color   = "#c6ff00" if active else "#2a2e35"
    status_text = "EM EXECUÇÃO" if active else "CONCLUÍDO"
    status_color = "#c6ff00" if active else "#5a5e66"
    rows_html   = "".join(lines)
    return f"""
    <div style="background:#0d0f14; border:1px solid #1f2329; border-top:2px solid #c6ff00;
                padding:1.2rem 1.5rem; min-height:200px;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; letter-spacing:0.2em;
                    text-transform:uppercase; color:{status_color}; margin-bottom:1rem;
                    display:flex; align-items:center; gap:0.6rem;">
            <span style="width:6px;height:6px;border-radius:50%;background:{dot_color};
                         display:inline-block;"></span>
            SYSTEM LOG — {status_text}
        </div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem; line-height:1.9;">
            {rows_html}
        </div>
    </div>
    """


# ─────────────────────────────────────────────
# LÓGICA PRINCIPAL DE AUTOMAÇÃO
# ─────────────────────────────────────────────

if iniciar:
    if not usuario or not senha:
        with right_col:
            st.error("⚠️  Preencha usuário e senha para continuar.")
    else:
        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path):
            shutil.rmtree(dl_path)
        os.makedirs(dl_path, exist_ok=True)
        
        logs = []
        
        def log(msg, kind="dim"):
            colors   = {
                "ok": "#c6ff00",
                "err": "#e84a2b",
                "info": "#5b8fff",
                "dim": "#4a5568",
                "warn": "#f59e0b"
            }
            prefixes = {
                "ok": "[OK ]",
                "err": "[ERR]",
                "info": "[INF]",
                "dim": "[ — ]",
                "warn": "[WRN]"
            }
            color  = colors.get(kind, "#4a5568")
            prefix = prefixes.get(kind, "[ — ]")
            logs.append(
                f'<span style="color:{color};">{prefix}</span> '
                f'<span style="color:#8896a8;">{msg}</span><br>'
            )
            log_placeholder.markdown(render_log(logs), unsafe_allow_html=True)
        
        driver = None
        
        try:
            log("Procurando Chrome/Chromium no sistema...", "info")
            chrome_binary = find_chrome_binary()
            
            if not chrome_binary:
                raise Exception(
                    "Chrome/Chromium não encontrado. "
                    "Instale: sudo apt-get install chromium-browser"
                )
            
            log(f"Browser encontrado: {chrome_binary}", "info")
            
            chrome_version = get_chrome_version(chrome_binary)
            
            if chrome_version:
                log(f"Versão detectada: {chrome_version}", "info")
            else:
                log("Não foi possível detectar a versão do browser", "warn")
            
            log("Inicializando ChromeDriver (baixando versão compatível)...", "info")
            driver = get_driver(dl_path, chrome_binary, chrome_version)
            log("ChromeDriver inicializado com sucesso!", "ok")
            
            log("Acessando portal MasterSAF...", "info")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            time.sleep(3)
            
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="enter"]')
            )
            time.sleep(5)
            log("Autenticação realizada com sucesso.", "ok")
            
            log("Navegando até Listagem de CT-es (Receptor)...", "info")
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')
            )
            time.sleep(4)
            
            log(f"Configurando período: {data_ini} → {data_fin}", "info")
            
            el_ini = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
            el_ini.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
            el_ini.send_keys(data_ini)
            
            el_fin = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
            el_fin.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
            el_fin.send_keys(data_fin)
            
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]')
            )
            time.sleep(4)
            log("Base de dados atualizada com o período selecionado.", "ok")
            
            log("Configurando exibição: 100 registros por página...", "info")
            driver.find_element(
                By.XPATH,
                '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]'
            ).click()
            time.sleep(4)
            
            total_paginas = int(qtd_loops)
            log(f"Iniciando captura em massa: {total_paginas} página(s)...", "info")
            
            for i in range(total_paginas):
                pagina_atual = i + 1
                log(f"Processando página {pagina_atual}/{total_paginas}...", "dim")
                
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(
                        By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'
                    )
                )
                time.sleep(1)
                
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3')
                )
                time.sleep(1)
                
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]')
                )
                log(f"Download da página {pagina_atual} iniciado...", "dim")
                time.sleep(8)
                
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(
                        By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'
                    )
                )
                time.sleep(1)
                
                if pagina_atual < total_paginas:
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span')
                    )
                    time.sleep(3)
                
                progress_placeholder.progress(pagina_atual / total_paginas)
                log(f"Página {pagina_atual} concluída.", "ok")
                time.sleep(2)
            
            log("Compactando arquivos XML em ZIP...", "info")
            
            zip_filename = "/tmp/resultado.zip"
            total_arquivos = 0
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(dl_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, file)
                        total_arquivos += 1
            
            log(f"Compactação concluída: {total_arquivos} arquivo(s).", "ok")
            
            log("Processo finalizado com sucesso!", "ok")
            log_placeholder.markdown(render_log(logs, active=False), unsafe_allow_html=True)
            
            with open(zip_filename, "rb") as f:
                download_placeholder.download_button(
                    f"📥  BAIXAR {total_arquivos} ARQUIVOS XML (.ZIP)",
                    f,
                    "XMLs_MasterSaf.zip",
                    "application/zip",
                )
            
            driver.quit()
            driver = None
            
        except Exception as e:
            error_msg = str(e)
            log(f"Erro crítico: {error_msg}", "err")
            
            if "chromedriver" in error_msg.lower() or "chrome" in error_msg.lower():
                log("Sugestão: Execute 'sudo apt-get update && sudo apt-get install -y chromium-browser'", "warn")
                log("Depois reinicie o aplicativo Streamlit.", "warn")
            
            if 'driver' in locals() and driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            
            log_placeholder.markdown(render_log(logs, active=False), unsafe_allow_html=True)