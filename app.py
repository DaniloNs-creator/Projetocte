import streamlit as st
import os
import shutil
import zipfile
import time
import re
import subprocess
import platform
import tempfile
import threading
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from io import BytesIO
from datetime import datetime
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

/* Força o container principal a usar flexbox em coluna */
[data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--border-secondary); border-radius: 0; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

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
[data-testid="stProgress"] { background: transparent !important; }
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

/* ── SIDEBAR ── */
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
.stButton button:active { transform: translateY(0) !important; }

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

/* ── ALERTS ── */
[data-testid="stAlert"] {
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.74rem !important;
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-secondary) !important;
    border-left: 3px solid var(--rust) !important;
    color: var(--text-primary) !important;
}

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

/* ── TABLES ── */
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

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
}

/* ── CODE ── */
code {
    background: var(--bg-tertiary) !important;
    color: var(--acid) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    padding: 0.2rem 0.5rem !important;
}

a { color: var(--acid) !important; text-decoration: none !important; }
a:hover { text-decoration: underline !important; }

/* ── CHECKBOX ── */
[data-testid="stCheckbox"] label {
    color: var(--text-primary) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
}

/* ── CAPTION ── */
.stCaption {
    color: var(--text-muted) !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Stat Cards ── */
.stat-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.8rem;
    margin: 1rem 0;
}
.stat-card {
    background: #111318;
    border: 1px solid #1f2329;
    border-radius: 0;
    padding: 1rem 1.2rem;
    position: relative;
    overflow: hidden;
}
.stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
}
.stat-card.green::before { background: var(--acid); }
.stat-card.blue::before { background: var(--blue); }
.stat-card.rust::before { background: var(--rust); }
.stat-card.white::before { background: var(--text-primary); }
.stat-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem;
    letter-spacing: 0.15em;
    color: #5a5e66;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.stat-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    color: #eef2ff;
}
.stat-value.green { color: var(--acid) !important; }
.stat-value.blue { color: var(--blue) !important; }
.stat-value.rust { color: var(--rust) !important; }

/* ── LOG BOX ── */
.log-box {
    background: #0d0f14;
    border: 1px solid #1f2329;
    border-top: 2px solid var(--acid);
    padding: 1.2rem 1.5rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #8896a8;
    max-height: 400px;
    overflow-y: auto;
    line-height: 1.9;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <div class="topbar-brand">MASTER<span>SAF</span> &nbsp;// XML AUTOMATION ENGINE</div>
    <div class="topbar-meta">v4.0.0 &nbsp;·&nbsp; CAPTURA EM MASSA &nbsp;·&nbsp; MÓDULO FISCAL</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────
for k, v in {
    "running": False, "done": False, "error_msg": "", 
    "page_atual": 0, "page_total": 0, "status_msg": "", 
    "stage": "idle", "xml_count": 0, "excel_bytes": None, 
    "logs": [], "arquivos_capturados": 0
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# LAYOUT — Two columns
# ─────────────────────────────────────────────
left_col, right_col = st.columns([1.05, 2], gap="small")

# ─────────────────────────────────────────────
# LEFT PANEL — CREDENCIAIS NO TOPO ABSOLUTO
# ─────────────────────────────────────────────
with left_col:
    # Container escuro que envolve todo o painel esquerdo
    with st.container():
        st.markdown("""
        <div style="background:#111318; padding:2.2rem 2rem 0.5rem; border-right:1px solid #1f2329;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.25em; text-transform:uppercase; color:#c6ff00; margin-bottom:0.3rem;">Módulo de Captura</div>
            <div style="font-family:'Syne',sans-serif; font-size:1.55rem; font-weight:800; color:#e4e6ea; line-height:1.1; margin-bottom:0.4rem;">Captura<br>em Massa</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.66rem; color:#8b8f98; line-height:1.6; margin-bottom:1.2rem;">Extração automatizada de XMLs<br>via portal MasterSAF · até 1000 págs.</div>
        </div>
        """, unsafe_allow_html=True)

    # ── CREDENCIAIS (PRIMEIRO CAMPO) ──
    st.markdown("""
    <div style="background:#111318; padding:0 2rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#c6ff00; margin-bottom:0.5rem;">🔐 Credenciais de Acesso</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div style="background:#111318; padding:0 2rem;">
        """, unsafe_allow_html=True)
        usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="usr", disabled=st.session_state.running)
        senha = st.text_input("Senha", type="password", placeholder="••••••••", key="pwd", disabled=st.session_state.running)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── PERÍODO ──
    st.markdown("""
    <div style="background:#111318; padding:0 2rem;">
        <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">📅 Período de Consulta</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        data_ini = st.text_input("Data Inicial", value="08/05/2026", key="di", disabled=st.session_state.running)
    with col_b:
        data_fin = st.text_input("Data Final", value="08/05/2026", key="df", disabled=st.session_state.running)

    # ── PARÂMETROS ──
    st.markdown("""
    <div style="background:#111318; padding:0 2rem;">
        <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">⚙️ Parâmetros</div>
    </div>
    """, unsafe_allow_html=True)

    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5, disabled=st.session_state.running)

    # ── PÓS-PROCESSAMENTO ──
    st.markdown("""
    <div style="background:#111318; padding:0 2rem;">
        <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">📊 Pós-Processamento</div>
    </div>
    """, unsafe_allow_html=True)

    processar_xml = st.checkbox("Extrair ZIPs e processar XMLs para Excel", value=True, key="processar", disabled=st.session_state.running)

    st.markdown("""
    <div style="background:#111318; padding:0 2rem 2rem;">
        <br>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.running:
        iniciar = st.button("⚡ INICIAR AUTOMAÇÃO")
    else:
        st.button("⏳ PROCESSANDO...", disabled=True)
        iniciar = False

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

    # Stat cards dinâmicos
    sc1, sc2, sc3, sc4 = st.columns(4)
    
    with sc1:
        pag_atual = st.session_state.page_atual
        pag_total = st.session_state.page_total or 0
        st.markdown(f"""
        <div class="stat-card green">
            <div class="stat-label">Págs. Processadas</div>
            <div class="stat-value green">{pag_atual:02d}</div>
        </div>""", unsafe_allow_html=True)
    
    with sc2:
        st.markdown(f"""
        <div class="stat-card blue">
            <div class="stat-label">Total Programado</div>
            <div class="stat-value blue">{pag_total:03d}</div>
        </div>""", unsafe_allow_html=True)
    
    with sc3:
        st.markdown(f"""
        <div class="stat-card white">
            <div class="stat-label">Arquivos Capturados</div>
            <div class="stat-value">{st.session_state.arquivos_capturados:03d}</div>
        </div>""", unsafe_allow_html=True)
    
    with sc4:
        status_text = st.session_state.stage.upper() if st.session_state.stage != "idle" else "IDLE"
        status_color = "rust" if st.session_state.error_msg else ("green" if st.session_state.stage == "done" else "white")
        st.markdown(f"""
        <div class="stat-card rust">
            <div class="stat-label">Status do Sistema</div>
            <div class="stat-value rust" style="font-size:0.9rem; padding-top:0.4rem;">{status_text}</div>
        </div>""", unsafe_allow_html=True)

    # Progress bar
    if st.session_state.running or st.session_state.done:
        total = st.session_state.page_total or 1
        atual = st.session_state.page_atual
        stage = st.session_state.stage
        
        pct = {"download": (atual/total)*0.65, "extract": 0.78, "excel": 0.92, "done": 1.0}.get(stage, 0.0)
        st.progress(pct)
    
    # Alertas
    if st.session_state.error_msg:
        st.error(f"❌ {st.session_state.error_msg}")
    elif st.session_state.stage == "done" and st.session_state.excel_bytes:
        st.success(f"✅ {st.session_state.status_msg}")
    elif st.session_state.stage == "done":
        st.warning(f"⚠️ {st.session_state.status_msg}")
    elif st.session_state.running:
        st.info(f"⏳ {st.session_state.status_msg}")

    # Log box
    log_text = "\n".join(st.session_state.logs[-100:]) if st.session_state.logs else "[ — ] Sistema pronto. Configure as credenciais e clique em iniciar.\n[ — ] Chrome/Selenium em standby (webdriver-manager).\n[ — ] Diretório de saída: /tmp/downloads"
    st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

    # Download Excel
    if st.session_state.stage == "done" and st.session_state.excel_bytes:
        st.markdown("---")
        periodo = f"{data_ini.replace('/','_')}_a_{data_fin.replace('/','_')}"
        st.download_button(
            label=f"📥  BAIXAR EXCEL CONSOLIDADO — {st.session_state.xml_count} registro(s)",
            data=st.session_state.excel_bytes,
            file_name=f"MasterSAF_Captura_{periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ─────────────────────────────────────────────
# XML PROCESSOR (Genérico - sem namespace CT-e)
# ─────────────────────────────────────────────

class XMLProcessor:
    """Processa arquivos XML extraindo todos os campos disponíveis"""
    
    def __init__(self):
        self.processed_data = []
    
    def extract_all_fields(self, root, parent_path=''):
        """Extrai recursivamente todos os campos do XML"""
        fields = {}
        
        def recursive_extract(element, path=''):
            # Adiciona atributos
            if element.attrib:
                for attr_key, attr_val in element.attrib.items():
                    full_path = f"{path}/@{attr_key}" if path else f"@{attr_key}"
                    fields[full_path] = attr_val
            
            # Se tem filhos, processa recursivamente
            children = list(element)
            if children:
                for child in children:
                    # Extrai o nome da tag sem namespace
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    child_path = f"{path}/{tag}" if path else tag
                    recursive_extract(child, child_path)
            else:
                # Elemento folha - adiciona valor
                if element.text and element.text.strip():
                    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                    full_path = f"{path}/{tag}" if path else tag
                    fields[full_path] = element.text.strip()
        
        recursive_extract(root)
        return fields
    
    def process_xml_files_from_directory(self, directory_path, log_callback):
        """Processa todos os arquivos XML em um diretório"""
        xml_files = list(Path(directory_path).glob('*.xml'))
        log_callback(f"   📄 {len(xml_files)} XMLs encontrados")
        
        all_fields_set = set()
        file_data_list = []
        
        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                root = ET.fromstring(content)
                fields = self.extract_all_fields(root)
                fields['_arquivo_origem'] = xml_file.name
                
                all_fields_set.update(fields.keys())
                file_data_list.append(fields)
            except Exception as e:
                log_callback(f"   ⚠ Erro ao processar {xml_file.name}: {str(e)[:50]}")
        
        # Cria DataFrame com todas as colunas encontradas
        if file_data_list:
            df = pd.DataFrame(file_data_list)
            
            # Garante que _arquivo_origem seja a primeira coluna
            cols = ['_arquivo_origem'] + [c for c in df.columns if c != '_arquivo_origem']
            df = df[cols]
            
            # Adiciona ao processado_data
            self.processed_data = df.to_dict('records')
        
        return len(file_data_list), len(xml_files)
    
    def export_to_excel(self):
        """Exporta os dados processados para Excel (BytesIO)"""
        if self.processed_data:
            df = pd.DataFrame(self.processed_data)
            buf = BytesIO()
            df.to_excel(buf, index=False, sheet_name='Dados_XML')
            buf.seek(0)
            return buf.getvalue(), len(df)
        return None, 0
    
    def clear_data(self):
        self.processed_data = []


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────

@st.cache_resource
def clear_wdm_cache():
    """Limpa o cache do webdriver-manager"""
    wdm_cache = os.path.expanduser("~/.wdm")
    if os.path.exists(wdm_cache):
        try:
            shutil.rmtree(wdm_cache)
            return True
        except Exception:
            return False
    return True


def get_chrome_version(binary_path):
    """Obtém a versão do Chrome/Chromium"""
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
    """Localiza o Chrome/Chromium no sistema"""
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
                result = subprocess.run(["which", browser], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass
    else:
        try:
            result = subprocess.run(["where", "chrome.exe"], capture_output=True, text=True, timeout=5, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0].strip()
        except Exception:
            pass
    
    return None


def get_driver(download_path, chrome_binary=None, chrome_version=None):
    """Inicializa o ChromeDriver compatível"""
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


def esperar_downloads(directory, timeout=120):
    """Aguarda downloads terminarem"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        crdownload_files = list(Path(directory).glob('*.crdownload'))
        if not crdownload_files:
            return True
        time.sleep(1)
    return False


# ─────────────────────────────────────────────
# PROCESSAMENTO PÓS-DOWNLOAD
# ─────────────────────────────────────────────

def processar_arquivos_baixados(base_dir, log_callback, state):
    """Processa os ZIPs baixados e gera Excel"""
    log_callback("=" * 50)
    log_callback("📦 INICIANDO PROCESSAMENTO DOS ARQUIVOS")
    log_callback("=" * 50)
    
    state["stage"] = "extract"
    
    zip_files = list(Path(base_dir).glob('*.zip'))
    log_callback(f"🔍 {len(zip_files)} arquivos ZIP encontrados")
    
    if not zip_files:
        log_callback("⚠ Nenhum arquivo ZIP para processar!")
        state["error_msg"] = "Nenhum ZIP baixado. Verifique login e datas."
        state["stage"] = "done"
        return
    
    # Cria diretório de extração
    extract_dir = tempfile.mkdtemp(prefix="mastersaf_extracted_")
    all_xml_dirs = []
    
    # Extrai ZIPs
    log_callback("📂 Extraindo arquivos ZIP...")
    for zip_file in zip_files:
        try:
            zip_name = zip_file.stem
            extract_path = os.path.join(extract_dir, zip_name)
            os.makedirs(extract_path, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            all_xml_dirs.append(extract_path)
            log_callback(f"   ✔ {zip_file.name}")
        except Exception as e:
            log_callback(f"   ❌ Erro ao extrair {zip_file.name}: {e}")
    
    # Processa XMLs
    state["stage"] = "excel"
    log_callback("📄 Processando arquivos XML...")
    
    processor = XMLProcessor()
    
    for xml_dir in all_xml_dirs:
        processor.process_xml_files_from_directory(xml_dir, log_callback)
    
    total_processados = len(processor.processed_data)
    log_callback(f"📊 Total de registros extraídos: {total_processados}")
    state["xml_count"] = total_processados
    
    if total_processados > 0:
        log_callback("📊 Gerando Excel consolidado...")
        
        excel_bytes, num_registros = processor.export_to_excel()
        processor.clear_data()
        
        state["excel_bytes"] = excel_bytes
        state["xml_count"] = num_registros
        state["stage"] = "done"
        state["status_msg"] = f"Processamento concluído! {num_registros} registros extraídos."
        
        log_callback(f"✅ Excel gerado com sucesso!")
        log_callback(f"📈 Total de registros: {num_registros}")
    else:
        processor.clear_data()
        log_callback("⚠ Nenhum registro extraído dos XMLs")
        state["error_msg"] = "Nenhum dado válido encontrado nos XMLs."
        state["stage"] = "done"
    
    # Limpa diretório de extração
    shutil.rmtree(extract_dir, ignore_errors=True)
    log_callback("=" * 50)


# ─────────────────────────────────────────────
# THREAD DE AUTOMAÇÃO
# ─────────────────────────────────────────────

def rodar_automacao(usuario, senha, dt_ini, dt_fin, loops, processar, state):
    """Função principal executada em thread separada"""
    
    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        state["logs"].append(f"[{ts}] {msg}")
        state["status_msg"] = msg
    
    driver = None
    dl_path = "/tmp/downloads"
    
    try:
        # Prepara diretório de downloads
        if os.path.exists(dl_path):
            shutil.rmtree(dl_path)
        os.makedirs(dl_path, exist_ok=True)
        
        # ── ETAPA 1: Localizar browser ──
        log("Procurando Chrome/Chromium no sistema...")
        chrome_binary = find_chrome_binary()
        
        if not chrome_binary:
            raise Exception(
                "Chrome/Chromium não encontrado. "
                "Instale: sudo apt-get install chromium-browser"
            )
        
        log(f"Browser encontrado: {chrome_binary}")
        
        # ── ETAPA 2: Detectar versão ──
        chrome_version = get_chrome_version(chrome_binary)
        
        if chrome_version:
            log(f"Versão detectada: {chrome_version}")
        else:
            log("Não foi possível detectar a versão do browser")
        
        # ── ETAPA 3: Inicializar driver ──
        log("Inicializando ChromeDriver...")
        driver = get_driver(dl_path, chrome_binary, chrome_version)
        log("ChromeDriver inicializado com sucesso!")
        
        # ── ETAPA 4: Login ──
        log("Acessando portal MasterSAF...")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        time.sleep(3)
        
        driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
        driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
        
        driver.execute_script(
            "arguments[0].click();",
            driver.find_element(By.XPATH, '//*[@id="enter"]')
        )
        time.sleep(5)
        log("Autenticação realizada com sucesso.")
        
        # ── ETAPA 5: Navegar ──
        log("Navegando até Listagem de CT-es (Receptor)...")
        driver.execute_script(
            "arguments[0].click();",
            driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')
        )
        time.sleep(4)
        
        # ── ETAPA 6: Configurar período ──
        log(f"Configurando período: {dt_ini} → {dt_fin}")
        
        el_ini = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
        el_ini.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
        el_ini.send_keys(dt_ini)
        
        el_fin = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        el_fin.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
        el_fin.send_keys(dt_fin)
        
        driver.execute_script(
            "arguments[0].click();",
            driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]')
        )
        time.sleep(4)
        log("Base de dados atualizada.")
        
        # ── ETAPA 7: Selecionar 100 registros ──
        log("Configurando exibição: 100 registros por página...")
        driver.find_element(
            By.XPATH,
            '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]'
        ).click()
        time.sleep(4)
        
        # ── ETAPA 8: Loop de captura ──
        total_paginas = int(loops)
        log(f"Iniciando captura em massa: {total_paginas} página(s)...")
        
        for i in range(total_paginas):
            pagina_atual = i + 1
            state["page_atual"] = pagina_atual
            state["stage"] = "download"
            
            log(f"Processando página {pagina_atual}/{total_paginas}...")
            
            # Seleciona todos os checkboxes
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(
                    By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'
                )
            )
            time.sleep(1)
            
            # Clica no botão de download múltiplo
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3')
            )
            time.sleep(1)
            
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]')
            )
            log(f"Download da página {pagina_atual} iniciado...")
            
            # Aguarda downloads
            esperar_downloads(dl_path)
            time.sleep(5)
            
            # Desmarca checkbox
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(
                    By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'
                )
            )
            time.sleep(1)
            
            # Avança para próxima página
            if pagina_atual < total_paginas:
                driver.execute_script(
                    "arguments[0].click();",
                    driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span')
                )
                time.sleep(3)
            
            log(f"Página {pagina_atual} concluída.")
            time.sleep(2)
        
        log("Captura finalizada!")
        
        # ── ETAPA 9: Pós-processamento ──
        if processar:
            processar_arquivos_baixados(dl_path, log, state)
        else:
            log("⚠ Processamento desativado. Arquivos disponíveis em /tmp/downloads")
            state["stage"] = "done"
            state["status_msg"] = "Downloads concluídos. Processamento desativado."
        
        # Conta arquivos capturados
        zip_files = list(Path(dl_path).glob('*.zip'))
        state["arquivos_capturados"] = len(zip_files)
        
    except Exception as e:
        import traceback
        log(f"❌ ERRO CRÍTICO: {str(e)}")
        log(traceback.format_exc())
        state["error_msg"] = str(e)
        state["stage"] = "done"
        
        if "chromedriver" in str(e).lower() or "chrome" in str(e).lower():
            log("Sugestão: Execute 'sudo apt-get update && sudo apt-get install -y chromium-browser'")
            log("Depois reinicie o aplicativo Streamlit.")
    
    finally:
        # Fecha o navegador
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        
        state["running"] = False
        state["done"] = True
        log("Processo finalizado.")


# ─────────────────────────────────────────────
# DISPARO DA THREAD
# ─────────────────────────────────────────────

if iniciar:
    if not usuario or not senha:
        with right_col:
            st.error("⚠️ Preencha usuário e senha para continuar.")
    else:
        # Reseta estado
        st.session_state.running = True
        st.session_state.done = False
        st.session_state.error_msg = ""
        st.session_state.page_atual = 0
        st.session_state.page_total = int(qtd_loops)
        st.session_state.status_msg = "Iniciando..."
        st.session_state.stage = "download"
        st.session_state.xml_count = 0
        st.session_state.excel_bytes = None
        st.session_state.logs = []
        st.session_state.arquivos_capturados = 0
        
        # Inicia thread
        t = threading.Thread(
            target=rodar_automacao,
            args=(usuario, senha, data_ini, data_fin, int(qtd_loops), processar_xml, st.session_state),
            daemon=True,
        )
        t.start()
        st.rerun()

# ─────────────────────────────────────────────
# AUTO-REFRESH DURANTE EXECUÇÃO
# ─────────────────────────────────────────────
if st.session_state.running:
    time.sleep(3)
    st.rerun()