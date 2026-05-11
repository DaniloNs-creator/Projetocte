import streamlit as st
import os
import shutil
import zipfile
import time
import tempfile
import io
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import subprocess
import requests
import re
import signal
import psutil

st.set_page_config(
    page_title="MasterSAF — Automação XML",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── INICIALIZAÇÃO DAS VARIÁVEIS DE SESSÃO ──
if 'ms_logs' not in st.session_state:
    st.session_state.ms_logs = []
if 'download_path' not in st.session_state:
    st.session_state.download_path = None
if 'execucao_ativa' not in st.session_state:
    st.session_state.execucao_ativa = False
if 'progresso_atual' not in st.session_state:
    st.session_state.progresso_atual = 0

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

#MainMenu, footer, header, [data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none !important;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #060810 !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stMainBlockContainer"] {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── TOP NAV ── */
.nav-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 2.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    background: rgba(6,8,16,0.95);
    backdrop-filter: blur(12px);
    position: sticky;
    top: 0;
    z-index: 100;
}
.nav-logo {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 1.05rem;
    color: #f8fafc;
    letter-spacing: -0.01em;
}
.nav-logo em { color: #22d3a5; font-style: normal; }
.nav-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #22d3a5;
    background: rgba(34,211,165,0.1);
    border: 1px solid rgba(34,211,165,0.25);
    border-radius: 20px;
    padding: 0.25rem 0.8rem;
    letter-spacing: 0.08em;
}

/* ── HERO ── */
.hero-wrap {
    padding: 3.5rem 2.5rem 2.5rem;
    max-width: 1100px;
    margin: 0 auto;
}
.hero-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #22d3a5;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.hero-eyebrow::before {
    content: '';
    display: inline-block;
    width: 24px; height: 1px;
    background: #22d3a5;
}
.hero-h1 {
    font-size: clamp(2rem, 4vw, 3.2rem);
    font-weight: 800;
    color: #f8fafc;
    line-height: 1.1;
    letter-spacing: -0.03em;
    margin: 0 0 0.8rem;
}
.hero-h1 span { 
    background: linear-gradient(135deg, #22d3a5, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    font-size: 1rem;
    color: #64748b;
    font-weight: 400;
    max-width: 560px;
    line-height: 1.6;
}

/* ── MAIN GRID ── */
.main-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 2.5rem 2rem;
}
@media (max-width: 768px) {
    .main-grid { grid-template-columns: 1fr; }
}

/* ── CARDS ── */
.card {
    background: #0d1117;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 1.5rem;
    transition: border-color 0.2s;
}
.card:hover { border-color: rgba(34,211,165,0.2); }
.card-title {
    font-size: 0.7rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.card-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.05);
}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stPasswordInput"] input {
    background: #070a0f !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    padding: 0.6rem 0.9rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stPasswordInput"] input:focus {
    border-color: rgba(34,211,165,0.5) !important;
    box-shadow: 0 0 0 3px rgba(34,211,165,0.08) !important;
    outline: none !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stPasswordInput"] label {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    color: #94a3b8 !important;
    margin-bottom: 0.3rem !important;
}

/* ── CHECKBOX ── */
[data-testid="stCheckbox"] label {
    font-size: 0.85rem !important;
    color: #94a3b8 !important;
    gap: 0.6rem !important;
}
[data-testid="stCheckbox"] span[data-baseweb="checkbox"] {
    background: #070a0f !important;
    border-color: rgba(255,255,255,0.15) !important;
    border-radius: 5px !important;
}

/* ── MAIN BUTTON ── */
.stButton > button {
    background: linear-gradient(135deg, #22d3a5 0%, #3b82f6 100%) !important;
    color: #020408 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2rem !important;
    width: 100% !important;
    letter-spacing: 0.01em !important;
    transition: opacity 0.2s, transform 0.15s !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }
.stButton > button:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
}

/* ── DOWNLOAD BUTTON ── */
.stDownloadButton > button {
    background: transparent !important;
    color: #22d3a5 !important;
    border: 1px solid rgba(34,211,165,0.4) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 10px !important;
    padding: 0.7rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: rgba(34,211,165,0.1) !important;
    border-color: #22d3a5 !important;
}

/* ── PROGRESS ── */
[data-testid="stProgress"] > div {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 99px !important;
    height: 5px !important;
}
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #22d3a5, #3b82f6) !important;
    border-radius: 99px !important;
}

/* ── ALERT ── */
[data-testid="stAlert"] {
    background: #0d1117 !important;
    border-radius: 10px !important;
    border-left: 3px solid !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
}

/* ── STAT CARDS ── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 2.5rem 1.5rem;
}
@media (max-width: 768px) {
    .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
    background: #0d1117;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
}
.stat-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.5rem;
}
.stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    color: #22d3a5;
    line-height: 1;
}
.stat-sub {
    font-size: 0.72rem;
    color: #475569;
    margin-top: 0.3rem;
}

/* ── EXEC SECTION ── */
.exec-wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 2.5rem 2rem;
}
.exec-header {
    font-size: 0.7rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.exec-header .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #22d3a5;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

/* ── DL SECTION ── */
.dl-wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 2.5rem 3rem;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}
@media (max-width: 768px) { .dl-wrap { grid-template-columns: 1fr; } }

/* ── DIVIDER ── */
.divider {
    max-width: 1100px;
    margin: 0 auto 1.5rem;
    padding: 0 2.5rem;
}
.divider hr {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.05);
}

/* ── CODE BLOCK (log) ── */
[data-testid="stCode"] {
    background: #070a0f !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* ── SAFETY STATUS ── */
.safety-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 1rem;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
}
.safety-ok {
    background: rgba(34,211,165,0.1);
    border: 1px solid rgba(34,211,165,0.3);
    color: #22d3a5;
}
.safety-warn {
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.3);
    color: #fbbf24;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# NAMESPACES CT-e
# ─────────────────────────────────────────────
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

# ─────────────────────────────────────────────
# FUNÇÕES DE LOG E CONTROLE
# ─────────────────────────────────────────────
def add_log(msg):
    """Adiciona mensagem ao log com limite de segurança"""
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.ms_logs.append(f"[{ts}]  {msg}")
    # Limitar logs para não sobrecarregar memória (manter últimos 500)
    if len(st.session_state.ms_logs) > 500:
        st.session_state.ms_logs = st.session_state.ms_logs[-500:]

def kill_chrome_processes():
    """Mata todos os processos do Chrome/Chromium para liberar recursos"""
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and any(name in proc.info['name'].lower() 
                    for name in ['chrome', 'chromium', 'chromedriver']):
                    os.kill(proc.info['pid'], signal.SIGKILL)
            except:
                pass
        time.sleep(2)
    except:
        pass

# ─────────────────────────────────────────────
# CTeProcessor
# ─────────────────────────────────────────────
class CTeProcessor:
    def __init__(self):
        self.processed_data = []

    def extract_nfe_number_from_key(self, chave_acesso):
        if not chave_acesso or len(chave_acesso) != 44:
            return None
        try:
            return chave_acesso[25:34]
        except Exception:
            return None

    def extract_peso_bruto(self, root):
        try:
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CALCCULO', 'PESO']
            for prefix, uri in CTE_NAMESPACES.items():
                for infQ in root.findall(f'.//{{{uri}}}infQ'):
                    tpMed  = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        for tp in tipos_peso:
                            if tp in tpMed.text.upper():
                                return float(qCarga.text)
            for infQ in root.findall('.//infQ'):
                tpMed  = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tp in tipos_peso:
                        if tp in tpMed.text.upper():
                            return float(qCarga.text)
            return 0.0
        except Exception:
            return 0.0

    def extract_cte_data(self, xml_content, filename):
        try:
            root = ET.fromstring(xml_content)

            def find_text(element, xpath):
                try:
                    for prefix, uri in CTE_NAMESPACES.items():
                        found = element.find(xpath.replace('cte:', f'{{{uri}}}'))
                        if found is not None and found.text:
                            return found.text
                    found = element.find(xpath.replace('cte:', ''))
                    return found.text if found is not None and found.text else None
                except Exception:
                    return None

            nCT          = find_text(root, './/cte:nCT')
            dhEmi        = find_text(root, './/cte:dhEmi')
            cMunIni      = find_text(root, './/cte:cMunIni')
            UFIni        = find_text(root, './/cte:UFIni')
            cMunFim      = find_text(root, './/cte:cMunFim')
            UFFim        = find_text(root, './/cte:UFFim')
            emit_xNome   = find_text(root, './/cte:emit/cte:xNome')
            vTPrest      = find_text(root, './/cte:vTPrest')
            rem_xNome    = find_text(root, './/cte:rem/cte:xNome')
            dest_xNome   = find_text(root, './/cte:dest/cte:xNome')
            dest_CNPJ    = find_text(root, './/cte:dest/cte:CNPJ')
            dest_CPF     = find_text(root, './/cte:dest/cte:CPF')
            dest_xLgr    = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro     = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_xMun    = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_UF      = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            dest_CEP     = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')

            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            endereco = ""
            if dest_xLgr:
                endereco += dest_xLgr
                if dest_nro:     endereco += f", {dest_nro}"
                if dest_xBairro: endereco += f" - {dest_xBairro}"
                if dest_xMun:    endereco += f", {dest_xMun}"
                if dest_UF:      endereco += f"/{dest_UF}"
                if dest_CEP:     endereco += f" - CEP: {dest_CEP}"
            endereco = endereco or "N/A"

            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            numero_nfe   = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            peso_bruto   = self.extract_peso_bruto(root)

            data_formatada = None
            if dhEmi:
                for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        data_formatada = datetime.strptime(dhEmi[:10], fmt).strftime('%d/%m/%y')
                        break
                    except Exception:
                        pass
                if not data_formatada:
                    data_formatada = dhEmi[:10]

            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0

            return {
                'Arquivo':                filename,
                'nCT':                    nCT or 'N/A',
                'Data Emissao':           data_formatada or dhEmi or 'N/A',
                'Cod Municipio Inicio':   cMunIni or 'N/A',
                'UF Inicio':              UFIni or 'N/A',
                'Cod Municipio Fim':      cMunFim or 'N/A',
                'UF Fim':                 UFFim or 'N/A',
                'Emitente':               emit_xNome or 'N/A',
                'Valor Prestacao':        vTPrest,
                'Peso Bruto (kg)':        peso_bruto,
                'Remetente':              rem_xNome or 'N/A',
                'Destinatario':           dest_xNome or 'N/A',
                'Documento Destinatario': documento_destinatario,
                'Endereco Destinatario':  endereco,
                'Municipio Destino':      dest_xMun or 'N/A',
                'UF Destino':             dest_UF or 'N/A',
                'Chave NFe':              infNFe_chave or 'N/A',
                'Numero NFe':             numero_nfe or 'N/A',
                'Data Processamento':     datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            }
        except Exception:
            return None

    def process_zip_bytes(self, zip_bytes, log_fn=None):
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                xml_names = [n for n in zf.namelist() if n.lower().endswith('.xml')]
                if log_fn:
                    log_fn(f"      📄 {len(xml_names)} XML(s) no ZIP")
                for name in xml_names:
                    try:
                        content = zf.read(name).decode('utf-8', errors='replace')
                        if 'CTe' in content or 'conhecimento' in content.lower():
                            data = self.extract_cte_data(content, Path(name).name)
                            if data:
                                self.processed_data.append(data)
                    except Exception:
                        pass
        except Exception as e:
            if log_fn:
                log_fn(f"      ❌ Erro ao ler ZIP: {e}")

    def process_directory(self, directory, log_fn=None):
        base = Path(directory)
        zip_files = list(base.glob('*.zip'))
        if log_fn:
            log_fn(f"🔍 {len(zip_files)} ZIP(s) encontrado(s)")
        for zp in zip_files:
            if log_fn:
                log_fn(f"   📦 Processando {zp.name}...")
            with open(zp, 'rb') as f:
                self.process_zip_bytes(f.read(), log_fn)
        for xf in base.glob('*.xml'):
            try:
                content = xf.read_text(encoding='utf-8', errors='replace')
                if 'CTe' in content or 'conhecimento' in content.lower():
                    data = self.extract_cte_data(content, xf.name)
                    if data:
                        self.processed_data.append(data)
            except Exception:
                pass

    def export_to_excel_bytes(self):
        if not self.processed_data:
            return None, 0
        df = pd.DataFrame(self.processed_data)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados_CTe')
            ws = writer.sheets['Dados_CTe']
            from openpyxl.styles import Font, PatternFill, Alignment
            hf    = PatternFill('solid', start_color='0D1B2A', end_color='0D1B2A')
            hfont = Font(bold=True, color='22D3A5', name='Inter', size=10)
            for cell in ws[1]:
                cell.fill = hf
                cell.font = hfont
                cell.alignment = Alignment(horizontal='center', vertical='center')
            for col in ws.columns:
                w = max((len(str(c.value)) if c.value else 0) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(w + 4, 50)
            for idx, cell in enumerate(ws[1], 1):
                if cell.value == 'Valor Prestacao':
                    for row in ws.iter_rows(min_row=2, min_col=idx, max_col=idx):
                        for c in row:
                            c.number_format = '#,##0.00'
                    break
        buf.seek(0)
        return buf.getvalue(), len(df)

    def summary(self):
        if not self.processed_data:
            return {}
        df = pd.DataFrame(self.processed_data)
        return {
            'total':       len(df),
            'peso_total':  df['Peso Bruto (kg)'].sum(),
            'valor_total': df['Valor Prestacao'].sum(),
            'emitentes':   df['Emitente'].nunique(),
        }

# ─────────────────────────────────────────────
# GERENCIAMENTO DO CHROMEDRIVER (ROBUSTO)
# ─────────────────────────────────────────────
def find_chrome_binary():
    """Encontra o binário do Chrome/Chromium instalado"""
    for binary in ['/usr/bin/chromium', '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium-browser']:
        if os.path.exists(binary):
            return binary
    return None

def get_chrome_version():
    """Obtém a versão principal do Chrome/Chromium"""
    binary = find_chrome_binary()
    if not binary:
        return None
    
    try:
        result = subprocess.run([binary, '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_text = result.stdout.strip()
            match = re.search(r'(\d+)\.', version_text)
            if match:
                major_version = int(match.group(1))
                return major_version
    except:
        pass
    
    return None

def download_chromedriver_chrome_for_testing(chrome_version):
    """Baixa o ChromeDriver da API Chrome for Testing (Chrome 115+)"""
    try:
        api_url = "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
        add_log(f"🌐 Buscando ChromeDriver para Chrome v{chrome_version}...")
        
        response = requests.get(api_url, timeout=15)
        data = response.json()
        
        version_key = str(chrome_version)
        if version_key not in data.get('milestones', {}):
            add_log(f"⚠️ Versão {chrome_version} não encontrada, tentando versão mais próxima...")
            # Tenta versões próximas
            for v in range(chrome_version - 2, chrome_version + 3):
                if str(v) in data.get('milestones', {}):
                    version_key = str(v)
                    break
        
        if version_key not in data.get('milestones', {}):
            return None
        
        downloads = data['milestones'][version_key]['downloads'].get('chromedriver', [])
        download_url = None
        for d in downloads:
            if d['platform'] == 'linux64':
                download_url = d['url']
                break
        
        if not download_url:
            return None
        
        add_log(f"📥 Baixando ChromeDriver...")
        response = requests.get(download_url, timeout=120)
        
        driver_dir = tempfile.mkdtemp(prefix="cd_")
        zip_path = os.path.join(driver_dir, "cd.zip")
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(driver_dir)
        
        for root, dirs, files in os.walk(driver_dir):
            for file in files:
                if file == 'chromedriver':
                    driver_path = os.path.join(root, file)
                    os.chmod(driver_path, 0o755)
                    return driver_path
        
        return None
        
    except Exception as e:
        add_log(f"❌ Erro download: {str(e)[:80]}")
        return None

def create_driver_with_retry(download_path, max_retries=3):
    """Cria o driver com tentativas e recuperação"""
    
    chrome_binary = find_chrome_binary()
    if not chrome_binary:
        raise Exception("Chrome/Chromium não encontrado")
    
    chrome_version = get_chrome_version()
    if not chrome_version:
        raise Exception("Versão do Chrome não detectada")
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                add_log(f"🔄 Tentativa {attempt + 1}/{max_retries} de criar driver...")
                kill_chrome_processes()
                time.sleep(3)
            
            opts = Options()
            opts.binary_location = chrome_binary
            opts.add_argument("--headless=new")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-software-rasterizer")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-infobars")
            opts.add_argument("--disable-notifications")
            opts.add_argument("--disable-popup-blocking")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--disable-web-security")
            opts.add_argument("--disable-features=VizDisplayCompositor")
            opts.add_argument("--disable-background-networking")
            opts.add_argument("--disable-sync")
            opts.add_argument("--disable-default-apps")
            opts.add_argument("--disable-translate")
            opts.add_argument("--metrics-recording-only")
            opts.add_argument("--mute-audio")
            opts.add_argument("--no-first-run")
            opts.add_argument("--safebrowsing-disable-auto-update")
            
            # Configurar memória para evitar crashes
            opts.add_argument("--max_old_space_size=4096")
            opts.add_argument("--disable-javascript-harmony-shipping")
            opts.add_argument("--js-flags=--max-old-space-size=4096")
            
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option('useAutomationExtension', False)
            
            prefs = {
                "download.default_directory": download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            }
            opts.add_experimental_option("prefs", prefs)
            
            # Tentar chromedriver do sistema primeiro
            system_drivers = ['/usr/bin/chromedriver', '/usr/lib/chromium-browser/chromedriver']
            for driver_path in system_drivers:
                if os.path.exists(driver_path):
                    try:
                        service = Service(executable_path=driver_path)
                        driver = webdriver.Chrome(service=service, options=opts)
                        return driver
                    except:
                        continue
            
            # Baixar driver compatível
            driver_path = download_chromedriver_chrome_for_testing(chrome_version)
            if driver_path:
                service = Service(executable_path=driver_path)
                driver = webdriver.Chrome(service=service, options=opts)
                return driver
            else:
                raise Exception("Não foi possível obter o ChromeDriver")
                
        except Exception as e:
            add_log(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)[:80]}")
            if attempt == max_retries - 1:
                raise
    
    raise Exception("Falha ao criar driver após múltiplas tentativas")

def esperar_downloads(directory, timeout=180):
    """Aguarda downloads terminarem com timeout estendido"""
    start = time.time()
    while time.time() - start < timeout:
        crdownloads = list(Path(directory).glob('*.crdownload'))
        if not crdownloads:
            # Verificar se tem arquivos ZIP
            zips = list(Path(directory).glob('*.zip'))
            if zips:
                return True
        time.sleep(2)
    return len(list(Path(directory).glob('*.zip'))) > 0

# ─────────────────────────────────────────────
# NAV BAR
# ─────────────────────────────────────────────
st.markdown("""
<div class="nav-bar">
    <div class="nav-logo">MASTER<em>SAF</em> <span style="color:#334155;font-weight:300;">//</span></div>
    <div class="nav-badge">⚡ AUTOMAÇÃO FISCAL v3 — MODO LONGA DURAÇÃO</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-eyebrow">Sistema de Automação CT-e</div>
    <h1 class="hero-h1">Download e <span>processamento</span><br>de XMLs em massa</h1>
    <p class="hero-sub">
        Motor otimizado para processar <strong>1000+ páginas sem interrupções</strong>.
        Sistema de recuperação automática contra falhas de rede e memória.
    </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FORMULÁRIO — GRID 2 COLUNAS
# ─────────────────────────────────────────────
st.markdown('<div class="main-grid">', unsafe_allow_html=True)

col_a, col_b = st.columns(2, gap="large")

with col_a:
    st.markdown('<div class="card"><div class="card-title">🔑 Credenciais de Acesso</div>', unsafe_allow_html=True)
    usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="usuario")
    senha   = st.text_input("Senha",   type="password", placeholder="••••••••", key="senha")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card" style="margin-top:1.5rem"><div class="card-title">📅 Período de Busca</div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1:
        data_ini = st.text_input("Data Inicial", value="08/05/2026", key="dt_ini")
    with p2:
        data_fin = st.text_input("Data Final",   value="08/05/2026", key="dt_fin")
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="card"><div class="card-title">⚙️ Parâmetros de Execução</div>', unsafe_allow_html=True)
    qtd_loops = st.number_input(
        "Quantidade de Páginas",
        min_value=1, max_value=5000, value=1000,
        help="Para 1000 páginas, estimativa de 4-6 horas de execução."
    )
    
    intervalo_seguranca = st.number_input(
        "Intervalo entre páginas (segundos)",
        min_value=1, max_value=30, value=8,
        help="Maior intervalo = mais estabilidade. Recomendado: 8-10s para 1000+ páginas."
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    gerar_excel = st.checkbox("Gerar Excel consolidado dos CT-es", value=True)
    gerar_zip   = st.checkbox("Disponibilizar ZIP com XMLs brutos", value=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card" style="margin-top:1.5rem"><div class="card-title">🚀 Controle de Execução</div>', unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        iniciar = st.button("⚡ Iniciar Automação", key="btn_iniciar", disabled=st.session_state.execucao_ativa)
    with col_btn2:
        parar = st.button("🛑 Parar Execução", key="btn_parar", disabled=not st.session_state.execucao_ativa)
    
    if st.session_state.execucao_ativa:
        st.markdown('<span class="safety-badge safety-ok">🟢 SISTEMA EM EXECUÇÃO</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="safety-badge safety-warn">⚪ SISTEMA EM ESPERA</span>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL (OTIMIZADA PARA 1000+ PÁGINAS)
# ─────────────────────────────────────────────
if iniciar and not st.session_state.execucao_ativa:
    if not usuario or not senha:
        st.error("⚠️ Preencha o usuário e a senha para continuar.")
    else:
        st.session_state.execucao_ativa = True
        st.session_state.ms_logs = []
        st.session_state.progresso_atual = 0
        
        dl_path = tempfile.mkdtemp(prefix="mastersaf_")
        st.session_state.download_path = dl_path

        st.markdown('<div class="divider"><hr></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="exec-wrap">
            <div class="exec-header"><span class="dot"></span>Execução em Tempo Real — Modo Longa Duração</div>
        </div>
        """, unsafe_allow_html=True)

        # Placeholders para UI
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        log_placeholder = st.empty()
        stats_placeholder = st.empty()
        
        driver = None
        total_paginas_processadas = 0
        reinicios_driver = 0
        MAX_REINICIOS = 5
        PAGINAS_POR_SESSAO = 50  # Reiniciar driver a cada 50 páginas
        
        def update_ui():
            """Atualiza todos os elementos da UI"""
            with status_placeholder.container():
                if st.session_state.execucao_ativa:
                    st.info(f"⏳ Processando... {total_paginas_processadas} de {int(qtd_loops)} páginas | Driver reiniciado {reinicios_driver}x")
            
            with progress_placeholder.container():
                if int(qtd_loops) > 0:
                    st.progress(min(total_paginas_processadas / int(qtd_loops), 1.0))
            
            with log_placeholder.container():
                st.code("\n".join(st.session_state.ms_logs[-40:]), language=None)
        
        def executar_ciclo_download(driver, pagina_atual, total_paginas):
            """Executa um ciclo de download para uma página"""
            try:
                # Selecionar todos os checkboxes
                try:
                    cb = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                    )
                    if not cb.is_selected():
                        cb.click()
                    time.sleep(2)
                except:
                    add_log(f"   ⚠️ Checkbox não encontrado na página {pagina_atual}")
                    return False
                
                # Iniciar download em massa
                try:
                    btn_xml = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                    )
                    driver.execute_script("arguments[0].click();", btn_xml)
                    time.sleep(2)
                    
                    btn_download = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                    )
                    driver.execute_script("arguments[0].click();", btn_download)
                    add_log(f"   📥 Download página {pagina_atual} iniciado")
                except:
                    add_log(f"   ⚠️ Botão download não encontrado na página {pagina_atual}")
                    return False
                
                # Aguardar download
                if esperar_downloads(dl_path, timeout=180):
                    add_log(f"   ✅ Página {pagina_atual} concluída")
                    time.sleep(1)
                    
                    # Desmarcar checkbox
                    try:
                        cb = driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                        if cb.is_selected():
                            cb.click()
                    except:
                        pass
                    
                    return True
                else:
                    add_log(f"   ⚠️ Timeout no download da página {pagina_atual}")
                    return False
                    
            except Exception as e:
                add_log(f"   ❌ Erro na página {pagina_atual}: {str(e)[:80]}")
                return False
        
        try:
            update_ui()
            
            # Criar driver inicial
            add_log("🚀 Inicializando navegador...")
            driver = create_driver_with_retry(dl_path)
            update_ui()
            
            # Login
            add_log("🔑 Realizando login...")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            time.sleep(5)
            
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.find_element(By.XPATH, '//*[@id="enter"]').click()
            time.sleep(5)
            add_log("✅ Login realizado")
            update_ui()
            
            # Navegar para listagem
            add_log("📋 Acessando listagem de CT-es...")
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(5)
            update_ui()
            
            # Configurar datas
            add_log(f"📅 Período: {data_ini} → {data_fin}")
            for xpath, val in [
                ('//*[@id="consultaDataInicial"]', data_ini),
                ('//*[@id="consultaDataFinal"]', data_fin),
            ]:
                el = driver.find_element(By.XPATH, xpath)
                el.clear()
                el.send_keys(val)
            time.sleep(2)
            
            # Atualizar listagem
            driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
            time.sleep(5)
            
            # Configurar 200 itens
            try:
                sel = driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
                sel.click()
                time.sleep(1)
                sel.find_element(By.XPATH, './/option[@value="200"]').click()
                time.sleep(3)
                add_log("⚙️ Configurado 200 itens/página")
            except:
                add_log("⚠️ Não foi possível configurar 200 itens/página")
            
            update_ui()
            
            # Loop principal
            pagina = 0
            while pagina < int(qtd_loops) and st.session_state.execucao_ativa:
                
                # Verificar se precisa reiniciar o driver
                if pagina > 0 and pagina % PAGINAS_POR_SESSAO == 0:
                    add_log(f"🔄 Reiniciando driver (página {pagina})...")
                    try:
                        driver.quit()
                    except:
                        pass
                    kill_chrome_processes()
                    time.sleep(5)
                    driver = create_driver_with_retry(dl_path)
                    reinicios_driver += 1
                    
                    # Refazer login e navegação
                    driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
                    time.sleep(3)
                    driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
                    driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
                    driver.find_element(By.XPATH, '//*[@id="enter"]').click()
                    time.sleep(5)
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
                    time.sleep(5)
                    
                    # Reconfigurar
                    for xpath, val in [
                        ('//*[@id="consultaDataInicial"]', data_ini),
                        ('//*[@id="consultaDataFinal"]', data_fin),
                    ]:
                        el = driver.find_element(By.XPATH, xpath)
                        el.clear()
                        el.send_keys(val)
                    time.sleep(2)
                    driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
                    time.sleep(5)
                    
                    # Navegar até a página atual
                    for _ in range(pagina):
                        try:
                            driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span').click()
                            time.sleep(3)
                        except:
                            break
                
                # Processar página atual
                add_log(f"━━━ Página {pagina + 1}/{int(qtd_loops)} ━━━")
                update_ui()
                
                sucesso = executar_ciclo_download(driver, pagina + 1, int(qtd_loops))
                
                if sucesso:
                    total_paginas_processadas += 1
                
                # Intervalo de segurança
                add_log(f"⏸️ Aguardando {int(intervalo_seguranca)}s...")
                update_ui()
                
                for _ in range(int(intervalo_seguranca)):
                    if not st.session_state.execucao_ativa:
                        break
                    time.sleep(1)
                
                # Próxima página
                if pagina < int(qtd_loops) - 1 and st.session_state.execucao_ativa:
                    try:
                        next_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, '//*[@id="next_plistagem"]/span'))
                        )
                        next_btn.click()
                        time.sleep(3)
                        pagina += 1
                    except:
                        add_log("⚠️ Não foi possível avançar para próxima página")
                        break
                else:
                    pagina += 1
                
                update_ui()
            
            # Finalização
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            kill_chrome_processes()
            
            add_log(f"✅ Downloads concluídos! {total_paginas_processadas} páginas processadas")
            st.session_state.execucao_ativa = False
            update_ui()
            
            # Processamento dos XMLs
            processor = CTeProcessor()
            zip_found = list(Path(dl_path).glob('*.zip'))
            add_log(f"📊 {len(zip_found)} arquivos ZIP encontrados")
            
            if gerar_excel and zip_found:
                processor.process_directory(dl_path, add_log)
                add_log(f"📊 Total CT-es processados: {len(processor.processed_data)}")
            
            # Gerar ZIP de saída
            zip_buf = None
            if gerar_zip and zip_found:
                buf_io = io.BytesIO()
                with zipfile.ZipFile(buf_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, _, files in os.walk(dl_path):
                        for file in files:
                            zipf.write(os.path.join(root_dir, file), file)
                buf_io.seek(0)
                zip_buf = buf_io.getvalue()
            
            update_ui()
            
            # Exibir estatísticas
            if gerar_excel and processor.processed_data:
                summ = processor.summary()
                with stats_placeholder.container():
                    st.markdown('<div class="divider"><hr></div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="stat-grid">
                        <div class="stat-card">
                            <div class="stat-label">Páginas Processadas</div>
                            <div class="stat-value">{total_paginas_processadas:,}</div>
                            <div class="stat-sub">de {int(qtd_loops)} planejadas</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">CT-es Extraídos</div>
                            <div class="stat-value">{summ['total']:,}</div>
                            <div class="stat-sub">documentos fiscais</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Peso Bruto Total</div>
                            <div class="stat-value">{summ['peso_total']:,.0f}</div>
                            <div class="stat-sub">quilogramas</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Valor Total</div>
                            <div class="stat-value">R$ {summ['valor_total']:,.2f}</div>
                            <div class="stat-sub">prestação de serviço</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Botões de download
            if gerar_excel or (gerar_zip and zip_buf):
                st.markdown('<div class="divider"><hr></div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    if gerar_excel and processor.processed_data:
                        excel_bytes, n_reg = processor.export_to_excel_bytes()
                        if excel_bytes:
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            st.download_button(
                                label=f"📊 Excel — {n_reg} CT-es",
                                data=excel_bytes,
                                file_name=f"CTe_{ts}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                
                with col2:
                    if gerar_zip and zip_buf:
                        st.download_button(
                            label="📥 ZIP XMLs brutos",
                            data=zip_buf,
                            file_name="XMLs_MasterSaf.zip",
                            mime="application/zip",
                        )
            
            # Limpeza
            shutil.rmtree(dl_path, ignore_errors=True)
            add_log("🏁 Pipeline finalizado com sucesso")
            update_ui()
            
        except Exception as e:
            add_log(f"❌ ERRO CRÍTICO: {str(e)[:200]}")
            st.session_state.execucao_ativa = False
            update_ui()
            
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            kill_chrome_processes()
            
            if 'dl_path' in locals() and os.path.exists(dl_path):
                shutil.rmtree(dl_path, ignore_errors=True)
            
            st.error(f"❌ A execução foi interrompida. Verifique os logs acima.")

# Botão de parada
if parar and st.session_state.execucao_ativa:
    st.session_state.execucao_ativa = False
    add_log("🛑 PARADA SOLICITADA - Finalizando ciclo atual...")
    st.warning("Parada solicitada. O sistema finalizará o ciclo atual e encerrará.")
    st.rerun()
