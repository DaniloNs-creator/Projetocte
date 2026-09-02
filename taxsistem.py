# -*- coding: utf-8 -*-
"""
HÄFELE TAX SYSTEM — Versão Simplificada
Módulos: MasterSAF Automação + Processador TXT + Catálogo Siscomex
"""
from __future__ import annotations

import io
import re
import json
import zipfile
import tempfile
import shutil
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import pandas as pd
import streamlit as st
import chardet

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
except ImportError:
    webdriver = None

# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="HÄFELE TAX SYSTEM - MasterSAF & TXT",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# CSS GLOBAL
# ==============================================================================
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 1rem; max-width: 1400px; }
        .hero-home {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 60vh;
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #0A0E17 0%, #141B2D 100%);
            border-radius: 24px;
            margin-bottom: 2rem;
            border: 1px solid #1E293B;
        }
        .hero-home .logo {
            max-width: 200px;
            margin-bottom: 1.5rem;
        }
        .hero-home h1 {
            font-size: 2.5rem;
            font-weight: 800;
            color: #E2E8F0;
            margin: 0 0 0.5rem;
        }
        .hero-home .sub {
            font-size: 1rem;
            color: #94A3B8;
            margin-bottom: 2rem;
        }
        .home-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            width: 100%;
            max-width: 800px;
        }
        .home-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid #1E293B;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            color: #E2E8F0;
            text-decoration: none;
            display: block;
        }
        .home-card:hover {
            background: rgba(255,255,255,0.1);
            transform: translateY(-4px);
            border-color: #334155;
        }
        .home-card .icon { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
        .home-card .name { font-weight: 700; font-size: 1rem; }
        .home-card .desc { font-size: 0.78rem; color: #94A3B8; }
        .ph-hdr {
            display: flex;
            align-items: center;
            gap: 1rem;
            background: #141B2D;
            border: 1px solid #1E293B;
            border-left: 4px solid #3B82F6;
            border-radius: 10px;
            padding: 0.9rem 1.4rem;
            margin-bottom: 1.2rem;
        }
        .ph-icon { font-size: 2rem; }
        .ph-title { font-size: 1.3rem; font-weight: 800; color: #60A5FA; }
        .ph-sub { font-size: 0.8rem; color: #94A3B8; }
        .card {
            background: #141B2D;
            border-radius: 12px;
            border: 1px solid #1E293B;
            padding: 1.3rem 1.5rem;
            margin-bottom: 1rem;
        }
        .ms-stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .ms-stat-card {
            background: #141B2D;
            border: 1px solid #1E293B;
            border-radius: 12px;
            padding: 1rem 1.2rem;
        }
        .ms-stat-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .ms-stat-value {
            font-size: 1.6rem;
            font-weight: 600;
            color: #10B981;
            line-height: 1.2;
        }
        .ms-log-area {
            background: #080D18;
            border: 1px solid #1E293B;
            border-radius: 12px;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.75rem;
            color: #CBD5E1;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .ms-log-area .log-ok { color: #22D3EE; }
        .ms-log-area .log-warn { color: #F59E0B; }
        .ms-log-area .log-err { color: #F87171; }
        .ms-log-area .log-info { color: #60A5FA; }
        .flabel {
            font-size: 0.76rem;
            font-weight: 600;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }
        .btn-voltar {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(59,130,246,0.1);
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 8px;
            padding: 0.4rem 1rem;
            color: #60A5FA;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 1rem;
        }
        .btn-voltar:hover {
            background: rgba(59,130,246,0.2);
        }
        .sbox {
            padding: 0.7rem 1.1rem;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 500;
            margin: 0.4rem 0;
        }
        .sbox-ok {
            background: rgba(16,185,129,0.15);
            color: #34D399;
            border: 1px solid rgba(16,185,129,0.2);
        }
        .sbox-warn {
            background: rgba(245,158,11,0.15);
            color: #FBBF24;
            border: 1px solid rgba(245,158,11,0.2);
        }
        .sbox-err {
            background: rgba(239,68,68,0.15);
            color: #F87171;
            border: 1px solid rgba(239,68,68,0.2);
        }
        .empty {
            text-align: center;
            padding: 3rem 1.5rem;
            color: #94A3B8;
            border: 2px dashed #1E293B;
            border-radius: 16px;
            background: #0A0E17;
        }
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #3B82F6, #1E3A8A) !important;
            border: none !important;
            color: white !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 3px;
            background: #0A0E17;
            border-radius: 12px;
            padding: 5px;
            border: 1px solid #1E293B;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.4rem 1rem;
            color: #94A3B8;
        }
        .stTabs [aria-selected="true"] {
            background: #141B2D !important;
            color: #60A5FA !important;
        }
        [data-testid="stDataFrame"] {
            border-radius: 12px !important;
            border: 1px solid #1E293B !important;
            overflow: hidden;
        }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# SESSION STATE
# ==============================================================================
_defaults = {
    'ms_logs': [],
    'ms_download_path': None,
    'ms_processed_data': [],
    'ms_zip_bytes': None,
    'modulo_atual': 'home',
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================================
# HELPERS
# ==============================================================================
def ph(html: str):
    st.markdown(html, unsafe_allow_html=True)

def botao_voltar():
    if st.button("🏠 Voltar ao Início", key="btn_voltar"):
        st.query_params.clear()
        st.rerun()

def empty_state(icon: str, title: str, sub: str = ""):
    ph(f"""
    <div class="empty">
        <div class="empty-icon">{icon}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-sub">{sub}</div>
    </div>""")

def add_ms_log(msg, level='info'):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.ms_logs.append({'ts': ts, 'msg': msg, 'level': level})

# ==============================================================================
# PÁGINA INICIAL
# ==============================================================================
def pagina_home():
    load_css()
    ph("""
    <div class="hero-home">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png"
             class="logo" alt="Häfele Brasil">
        <h1>HÄFELE TAX SYSTEM</h1>
        <p class="sub">Sistema Integrado de Processamento Fiscal — Módulos Essenciais</p>
        <div class="home-grid">
            <a href="?modulo=processador_txt" class="home-card">
                <span class="icon">📄</span>
                <div class="name">Processador TXT</div>
                <div class="desc">Limpeza e padronização de arquivos texto</div>
            </a>
            <a href="?modulo=mastersaf" class="home-card">
                <span class="icon">⚡</span>
                <div class="name">MasterSAF Automação</div>
                <div class="desc">Download em massa de CT-es com WebDriver</div>
            </a>
            <a href="?modulo=siscomex" class="home-card">
                <span class="icon">🌐</span>
                <div class="name">Catálogo Siscomex</div>
                <div class="desc">JSON ⇄ Excel + Lotes para API</div>
            </a>
        </div>
    </div>
    """)

# ==============================================================================
# MÓDULO: PROCESSADOR TXT
# ==============================================================================
def modulo_processador_txt():
    botao_voltar()
    ph("""
    <div class="ph-hdr">
        <span class="ph-icon">📄</span>
        <div>
            <div class="ph-title">Processador de Arquivos TXT</div>
            <div class="ph-sub">Remova linhas indesejadas e substitua padrões</div>
        </div>
    </div>
    """)

    def detectar_encoding(conteudo):
        return chardet.detect(conteudo)['encoding']

    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]
    substituicoes = {
        "IMPOSTO IMPORTACAO": "IMP IMPORT",
        "TAXA SICOMEX": "TX SISCOMEX",
        "FRETE INTERNACIONAL": "FRET INTER",
        "SEGURO INTERNACIONAL": "SEG INTER",
    }

    col_up, col_cfg = st.columns([3, 2])
    with col_up:
        arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    with col_cfg:
        with st.expander("⚙️ Padrões de remoção"):
            padroes_add = st.text_input("Padrões (vírgula)", placeholder="Ex: TOTAL, SOMA")
            padroes = padroes_default + [p.strip() for p in padroes_add.split(",") if p.strip()] if padroes_add else padroes_default
        st.markdown(f'<div class="flabel">🔍 {len(padroes)} padrões ativos</div>', unsafe_allow_html=True)

    if arquivo is not None and st.button("🔄 Processar", type="primary"):
        try:
            conteudo = arquivo.read()
            encoding = detectar_encoding(conteudo)
            try:
                texto = conteudo.decode(encoding)
            except UnicodeDecodeError:
                texto = conteudo.decode('latin-1')
            linhas = texto.splitlines()
            out = []
            for linha in linhas:
                linha = linha.strip()
                if not any(p in linha for p in padroes):
                    for orig, sub in substituicoes.items():
                        linha = linha.replace(orig, sub)
                    out.append(linha)
            resultado = "\n".join(out)
            mantidas = len(resultado.splitlines())
            removidas = len(linhas) - mantidas

            c1, c2, c3 = st.columns(3)
            c1.metric("📋 Originais", len(linhas))
            c2.metric("✅ Mantidas", mantidas)
            c3.metric("🗑️ Removidas", removidas, delta=f"-{removidas}", delta_color="inverse")

            st.text_area("Prévia", resultado, height=250)
            buf = io.BytesIO(resultado.encode('utf-8'))
            st.download_button("⬇️ Baixar", data=buf, file_name=f"processado_{arquivo.name}", mime="text/plain")
        except Exception as e:
            st.error(f"Erro: {e}")

# ==============================================================================
# MÓDULO: MasterSAF AUTOMAÇÃO
# ==============================================================================
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

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
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
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

            nCT = find_text(root, './/cte:nCT')
            dhEmi = find_text(root, './/cte:dhEmi')
            cMunIni = find_text(root, './/cte:cMunIni')
            UFIni = find_text(root, './/cte:UFIni')
            cMunFim = find_text(root, './/cte:cMunFim')
            UFFim = find_text(root, './/cte:UFFim')
            emit_xNome = find_text(root, './/cte:emit/cte:xNome')
            vTPrest = find_text(root, './/cte:vTPrest')
            rem_xNome = find_text(root, './/cte:rem/cte:xNome')
            dest_xNome = find_text(root, './/cte:dest/cte:xNome')
            dest_CNPJ = find_text(root, './/cte:dest/cte:CNPJ')
            dest_CPF = find_text(root, './/cte:dest/cte:CPF')
            dest_xLgr = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_xMun = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_UF = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            dest_CEP = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')

            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            endereco = ""
            if dest_xLgr:
                endereco += dest_xLgr
                if dest_nro: endereco += f", {dest_nro}"
                if dest_xBairro: endereco += f" - {dest_xBairro}"
                if dest_xMun: endereco += f", {dest_xMun}"
                if dest_UF: endereco += f"/{dest_UF}"
                if dest_CEP: endereco += f" - CEP: {dest_CEP}"
            endereco = endereco or "N/A"

            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            peso_bruto = self.extract_peso_bruto(root)

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
                'Arquivo': filename,
                'nCT': nCT or 'N/A',
                'Data Emissao': data_formatada or dhEmi or 'N/A',
                'Cod Municipio Inicio': cMunIni or 'N/A',
                'UF Inicio': UFIni or 'N/A',
                'Cod Municipio Fim': cMunFim or 'N/A',
                'UF Fim': UFFim or 'N/A',
                'Emitente': emit_xNome or 'N/A',
                'Valor Prestacao': vTPrest,
                'Peso Bruto (kg)': peso_bruto,
                'Remetente': rem_xNome or 'N/A',
                'Destinatario': dest_xNome or 'N/A',
                'Documento Destinatario': documento_destinatario,
                'Endereco Destinatario': endereco,
                'Municipio Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Numero NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            }
        except Exception:
            return None

    def process_zip_bytes(self, zip_bytes, log_fn=None):
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                xml_names = [n for n in zf.namelist() if n.lower().endswith('.xml')]
                if log_fn:
                    log_fn(f"📄 {len(xml_names)} XML(s) no ZIP", 'info')
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
                log_fn(f"❌ Erro ao ler ZIP: {e}", 'err')

    def process_directory(self, directory, log_fn=None):
        base = Path(directory)
        zip_files = list(base.glob('*.zip'))
        if log_fn:
            log_fn(f"🔍 {len(zip_files)} ZIP(s) encontrado(s)", 'info')
        for zp in zip_files:
            if log_fn:
                log_fn(f"📦 Processando {zp.name}...", 'info')
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
        buf.seek(0)
        return buf.getvalue(), len(df)

    def summary(self):
        if not self.processed_data:
            return {}
        df = pd.DataFrame(self.processed_data)
        return {
            'total': len(df),
            'peso_total': df['Peso Bruto (kg)'].sum(),
            'valor_total': df['Valor Prestacao'].sum(),
            'emitentes': df['Emitente'].nunique(),
        }

def get_chrome_version():
    for cmd in (['chromium', '--version'], ['google-chrome', '--version'],
                ['google-chrome-stable', '--version']):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
    return None

def get_driver(download_path):
    if webdriver is None:
        raise RuntimeError("Selenium não está instalado. Execute: pip install selenium")
    opts = Options()
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
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    opts.add_experimental_option("prefs", prefs)

    for path in ['/usr/bin/chromedriver', '/usr/lib/chromium/chromedriver',
                  '/usr/bin/chromium-driver']:
        if os.path.exists(path):
            try:
                return webdriver.Chrome(service=Service(path), options=opts)
            except Exception:
                continue
    try:
        return webdriver.Chrome(options=opts)
    except Exception:
        pass
    for binary in ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']:
        if os.path.exists(binary):
            opts.binary_location = binary
            try:
                return webdriver.Chrome(options=opts)
            except Exception:
                continue
    raise RuntimeError("Nenhuma estratégia de ChromeDriver funcionou.")

def esperar_downloads(directory, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        if not list(Path(directory).glob('*.crdownload')):
            return True
        time.sleep(1)
    return False

def render_ms_log():
    logs = st.session_state.ms_logs[-40:]
    html_parts = ['<div class="ms-log-area">']
    for entry in logs:
        cls = f"log-{entry['level']}"
        html_parts.append(
            f'<span class="log-ts">[{entry["ts"]}]</span>'
            f' <span class="{cls}">{entry["msg"]}</span>\n'
        )
    html_parts.append('</div>')
    ph('\n'.join(html_parts))

def modulo_mastersaf():
    botao_voltar()
    ph("""
    <div class="ph-hdr">
        <span class="ph-icon">⚡</span>
        <div>
            <div class="ph-title">MasterSAF Automação</div>
            <div class="ph-sub">Download e processamento em massa de CT-es</div>
        </div>
    </div>
    """)

    tab_exec, tab_resultados, tab_export = st.tabs([
        "🚀 Executar", "📊 Resultados", "📥 Exportar"
    ])

    with tab_exec:
        col_a, col_b = st.columns(2)
        with col_a:
            usuario = st.text_input("Usuário", placeholder="login@empresa.com.br")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
        with col_b:
            data_ini = st.text_input("Data Inicial", value="08/05/2026")
            data_fin = st.text_input("Data Final", value="08/05/2026")
            qtd_loops = st.number_input("Páginas", min_value=1, max_value=100, value=5)

        if st.button("⚡ Iniciar Automação", type="primary"):
            if not usuario or not senha:
                st.error("Preencha usuário e senha.")
            else:
                st.session_state.ms_logs = []
                st.session_state.ms_processed_data = []
                dl_path = tempfile.mkdtemp(prefix="mastersaf_")
                st.session_state.ms_download_path = dl_path

                status_box = st.info("⏳ Inicializando...")
                progress_bar = st.progress(0)
                driver = None
                processor = CTeProcessor()

                try:
                    chrome_version = get_chrome_version()
                    if chrome_version:
                        add_ms_log(f"📊 Versão: {chrome_version}", 'info')
                    add_ms_log("🌐 Iniciando Chrome...", 'info')
                    driver = get_driver(dl_path)
                    add_ms_log("🔗 Acessando MasterSAF...", 'info')
                    driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
                    time.sleep(3)

                    driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
                    driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="enter"]'))
                    time.sleep(5)
                    add_ms_log("✅ Login OK", 'ok')
                    progress_bar.progress(0.05)

                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
                    time.sleep(5)
                    add_ms_log("📋 Listagem acessada", 'info')
                    progress_bar.progress(0.08)

                    for xpath, val in [
                        ('//*[@id="consultaDataInicial"]', data_ini),
                        ('//*[@id="consultaDataFinal"]', data_fin),
                    ]:
                        el = driver.find_element(By.XPATH, xpath)
                        el.click()
                        el.send_keys(Keys.CONTROL, 'a')
                        el.send_keys(Keys.BACKSPACE)
                        el.send_keys(val)
                    time.sleep(1)

                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
                    time.sleep(5)
                    progress_bar.progress(0.12)

                    sel = driver.find_element(
                        By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
                    sel.click()
                    sel.find_element(By.XPATH, './/option[@value="200"]').click()
                    time.sleep(3)

                    for i in range(qtd_loops):
                        add_ms_log(f"━━ Página {i+1}/{qtd_loops}", 'info')
                        try:
                            cb = driver.find_element(
                                By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                            if not cb.is_selected():
                                cb.click()
                            time.sleep(2)
                        except Exception:
                            add_ms_log("   ⚠ Checkbox não encontrado", 'warn')
                        try:
                            driver.execute_script("arguments[0].click();",
                                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                            time.sleep(2)
                            driver.execute_script("arguments[0].click();",
                                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                        except Exception:
                            add_ms_log("   ⚠ Botão download não encontrado", 'warn')
                        add_ms_log("   ⏳ Aguardando download...", 'info')
                        esperar_downloads(dl_path, timeout=120)
                        time.sleep(2)
                        if i < qtd_loops - 1:
                            try:
                                driver.find_element(
                                    By.XPATH, '//*[@id="next_plistagem"]/span').click()
                                time.sleep(5)
                            except Exception:
                                add_ms_log("   ⚠ Fim das páginas", 'warn')
                                break
                        progress_bar.progress(0.15 + ((i+1)/qtd_loops)*0.60)

                    add_ms_log("✅ Downloads concluídos", 'ok')
                    driver.quit()
                    driver = None
                    progress_bar.progress(0.78)

                    zip_found = list(Path(dl_path).glob('*.zip'))
                    add_ms_log(f"🔍 {len(zip_found)} ZIP(s) localizado(s)", 'info')
                    if zip_found:
                        status_box.info("📊 Processando XMLs...")
                        processor.process_directory(dl_path, add_ms_log)
                        add_ms_log(f"📊 CT-es identificados: {len(processor.processed_data)}", 'ok')

                    st.session_state.ms_processed_data = processor.processed_data.copy()

                    # ZIP dos XMLs brutos
                    buf_io = io.BytesIO()
                    with zipfile.ZipFile(buf_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root_dir, _, files in os.walk(dl_path):
                            for file in files:
                                zipf.write(os.path.join(root_dir, file), file)
                    buf_io.seek(0)
                    st.session_state.ms_zip_bytes = buf_io.getvalue()

                    progress_bar.progress(1.0)
                    status_box.success("✅ Concluído!")
                    add_ms_log("🏁 Pipeline completo.", 'ok')

                    shutil.rmtree(dl_path, ignore_errors=True)

                    if processor.processed_data:
                        summ = processor.summary()
                        st.markdown("---")
                        ph(f"""
                        <div class="ms-stat-grid">
                            <div class="ms-stat-card"><div class="ms-stat-label">CT-es</div>
                            <div class="ms-stat-value">{summ['total']:,}</div></div>
                            <div class="ms-stat-card"><div class="ms-stat-label">Peso Total</div>
                            <div class="ms-stat-value">{summ['peso_total']:,.0f} kg</div></div>
                            <div class="ms-stat-card"><div class="ms-stat-label">Valor Total</div>
                            <div class="ms-stat-value">R$ {summ['valor_total']:,.2f}</div></div>
                            <div class="ms-stat-card"><div class="ms-stat-label">Emitentes</div>
                            <div class="ms-stat-value">{summ['emitentes']}</div></div>
                        </div>
                        """)
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
                    add_ms_log(f"❌ EXCEÇÃO: {e}", 'err')
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                    if dl_path and os.path.exists(dl_path):
                        shutil.rmtree(dl_path, ignore_errors=True)

                render_ms_log()

    with tab_resultados:
        if st.session_state.ms_processed_data:
            df = pd.DataFrame(st.session_state.ms_processed_data)
            st.dataframe(df, use_container_width=True)
        else:
            empty_state("📊", "Nenhum CT-e processado", "Execute a automação primeiro")

    with tab_export:
        if st.session_state.ms_processed_data:
            df = pd.DataFrame(st.session_state.ms_processed_data)
            st.metric("📋 Registros", len(df))
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar CSV", data=csv, file_name="cte_mastersaf.csv", mime="text/csv")
            if st.session_state.get('ms_zip_bytes'):
                st.download_button(
                    "📥 XMLs brutos (.zip)",
                    data=st.session_state.ms_zip_bytes,
                    file_name="XMLs_MasterSaf.zip",
                    mime="application/zip",
                )
        else:
            empty_state("📥", "Nenhum dado disponível")

# ==============================================================================
# MÓDULO: CATÁLOGO SISCOMEX (JSON ⇄ Excel + Lotes API)
# ==============================================================================
# Colunas do catálogo Siscomex
COLUNAS_SIMPLES = [
    "seq", "codigo", "descricao", "denominacao", "cpfCnpjRaiz",
    "situacao", "modalidade", "ncm", "versao", "inicioVigencia", "dataReferencia"
]
COLUNA_LISTA_SIMPLES = "codigosInterno"
COLUNAS_LISTA_JSON = ["atributos", "atributosMultivalorados", "atributosCompostos", "atributosCompostosMultivalorados"]
TODAS_COLUNAS = COLUNAS_SIMPLES + [COLUNA_LISTA_SIMPLES] + COLUNAS_LISTA_JSON
SEPARADOR_CODIGOS = ";"
MAX_ITENS_POR_LOTE = 100
SITUACOES_VALIDAS = {"ATIVADO", "DESATIVADO", "RASCUNHO"}
MODALIDADES_VALIDAS = {"IMPORTACAO", "EXPORTACAO"}

def json_para_dataframe(itens: list[dict]) -> pd.DataFrame:
    linhas = []
    for item in itens:
        linha = {c: item.get(c, "") for c in COLUNAS_SIMPLES}
        codigos = item.get(COLUNA_LISTA_SIMPLES, [])
        linha[COLUNA_LISTA_SIMPLES] = SEPARADOR_CODIGOS.join(str(c) for c in codigos) if isinstance(codigos, list) else ""
        for campo in COLUNAS_LISTA_JSON:
            valor = item.get(campo, [])
            linha[campo] = json.dumps(valor, ensure_ascii=False) if valor else ""
        linhas.append(linha)
    return pd.DataFrame(linhas, columns=TODAS_COLUNAS)

def dataframe_para_json(df: pd.DataFrame) -> tuple[list[dict], list[str]]:
    erros = []
    itens = []
    for i, row in df.iterrows():
        row_dict = row.to_dict()
        item = {}
        for campo in COLUNAS_SIMPLES:
            valor = row_dict.get(campo, "")
            if pd.isna(valor):
                valor = ""
            if campo == "seq":
                try:
                    valor = int(valor) if valor else None
                except ValueError:
                    erros.append(f"Linha {i+2}: 'seq' inválido")
            if campo in ("descricao", "dataReferencia") and valor == "":
                continue
            item[campo] = valor
        codigos_raw = row_dict.get(COLUNA_LISTA_SIMPLES, "")
        item[COLUNA_LISTA_SIMPLES] = [c.strip() for c in str(codigos_raw).split(SEPARADOR_CODIGOS) if c.strip()] if codigos_raw else []
        for campo in COLUNAS_LISTA_JSON:
            bruto = row_dict.get(campo, "")
            try:
                item[campo] = json.loads(bruto) if bruto else []
            except json.JSONDecodeError:
                erros.append(f"Linha {i+2}: JSON inválido em '{campo}'")
                item[campo] = []
        itens.append(item)
    return itens, erros

def validar_item_envio(item: dict, linha: int) -> tuple[dict | None, list[str]]:
    erros = []
    pronto = {}
    codigo = item.get("codigo")
    if codigo:
        try:
            pronto["codigo"] = int(codigo)
        except ValueError:
            erros.append(f"Linha {linha}: 'codigo' não é numérico")
    denominacao = str(item.get("denominacao", ""))
    if not (1 <= len(denominacao) <= 120):
        erros.append(f"Linha {linha}: 'denominacao' deve ter 1-120 caracteres")
    pronto["denominacao"] = denominacao
    cpf_cnpj = re.sub(r"\D", "", str(item.get("cpfCnpjRaiz", "")))
    if len(cpf_cnpj) not in (8, 11):
        erros.append(f"Linha {linha}: 'cpfCnpjRaiz' deve ter 8 ou 11 dígitos")
    pronto["cpfCnpjRaiz"] = cpf_cnpj.zfill(8) if len(cpf_cnpj) == 8 else cpf_cnpj
    situacao = str(item.get("situacao", "")).upper()
    if situacao not in SITUACOES_VALIDAS:
        erros.append(f"Linha {linha}: 'situacao' inválida")
    pronto["situacao"] = situacao
    modalidade = str(item.get("modalidade", "")).upper()
    if modalidade not in MODALIDADES_VALIDAS:
        erros.append(f"Linha {linha}: 'modalidade' inválida")
    pronto["modalidade"] = modalidade
    ncm = re.sub(r"\D", "", str(item.get("ncm", "")))
    if len(ncm) != 8:
        erros.append(f"Linha {linha}: 'ncm' deve ter 8 dígitos")
    pronto["ncm"] = ncm
    pronto["atributos"] = item.get("atributos", [])
    pronto["atributosMultivalorados"] = item.get("atributosMultivalorados", [])
    pronto["atributosCompostos"] = item.get("atributosCompostos", [])
    pronto["atributosCompostosMultivalorados"] = item.get("atributosCompostosMultivalorados", [])
    pronto["codigosInterno"] = item.get("codigosInterno", [])
    return (pronto, erros) if not erros else (None, erros)

def gerar_lotes(itens: list[dict]) -> tuple[list[list[dict]], list[str]]:
    lotes, relatorio = [], []
    validos = []
    for i, item in enumerate(itens):
        pronto, erros = validar_item_envio(item, i+2)
        if pronto:
            validos.append(pronto)
        else:
            relatorio.append(f"Linha {i+2}: {', '.join(erros)}")
    for inicio in range(0, len(validos), MAX_ITENS_POR_LOTE):
        lote = [{"seq": j+1, **item} for j, item in enumerate(validos[inicio:inicio+MAX_ITENS_POR_LOTE])]
        lotes.append(lote)
    return lotes, relatorio

def modulo_siscomex():
    botao_voltar()
    ph("""
    <div class="ph-hdr">
        <span class="ph-icon">🌐</span>
        <div>
            <div class="ph-title">Catálogo de Itens Siscomex</div>
            <div class="ph-sub">Conversor JSON ⇄ Excel + Lotes para API</div>
        </div>
    </div>
    """)

    tab1, tab2, tab3 = st.tabs(["📤 JSON → Excel", "📥 Excel → JSON", "📦 Lotes API"])

    with tab1:
        arquivo = st.file_uploader("JSON do catálogo", type=["json"])
        if arquivo:
            try:
                dados = json.loads(arquivo.read().decode("utf-8-sig"))
                if isinstance(dados, dict):
                    for chave in ("itens", "items", "data"):
                        if chave in dados and isinstance(dados[chave], list):
                            dados = dados[chave]
                            break
                if not isinstance(dados, list):
                    st.error("JSON não é uma lista de itens.")
                else:
                    df = json_para_dataframe(dados)
                    st.success(f"{len(df)} itens carregados")
                    st.dataframe(df.head(50), use_container_width=True)
                    excel = io.BytesIO()
                    with pd.ExcelWriter(excel, engine="xlsxwriter") as writer:
                        df.to_excel(writer, index=False, sheet_name="Catalogo")
                    st.download_button("⬇️ Baixar Excel", data=excel.getvalue(), file_name="catalogo.xlsx")
            except Exception as e:
                st.error(f"Erro: {e}")

    with tab2:
        arquivo = st.file_uploader("Excel editado", type=["xlsx"])
        if arquivo:
            try:
                df = pd.read_excel(arquivo, dtype=str).fillna("")
                itens, erros = dataframe_para_json(df)
                if erros:
                    for e in erros[:10]:
                        st.warning(e)
                st.json(itens[:3] if itens else [], expanded=False)
                st.download_button("⬇️ Baixar JSON", data=json.dumps(itens, ensure_ascii=False, indent=2).encode(),
                                   file_name="catalogo.json", mime="application/json")
            except Exception as e:
                st.error(f"Erro: {e}")

    with tab3:
        arquivo = st.file_uploader("Excel para envio", type=["xlsx"])
        if arquivo:
            try:
                df = pd.read_excel(arquivo, dtype=str).fillna("")
                itens, _ = dataframe_para_json(df)
                lotes, relatorio = gerar_lotes(itens)
                st.metric("Lotes gerados", len(lotes))
                if relatorio:
                    with st.expander("📋 Relatório"):
                        st.text("\n".join(relatorio))
                if lotes:
                    zip_bytes = io.BytesIO()
                    with zipfile.ZipFile(zip_bytes, "w") as zf:
                        for i, lote in enumerate(lotes):
                            zf.writestr(f"lote_{i+1:03d}.json", json.dumps(lote, ensure_ascii=False, indent=2))
                        zf.writestr("relatorio.txt", "\n".join(relatorio))
                    st.download_button("⬇️ Baixar ZIP com lotes", data=zip_bytes.getvalue(),
                                       file_name="lotes_siscomex.zip", mime="application/zip")
            except Exception as e:
                st.error(f"Erro: {e}")

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    load_css()
    query_params = st.query_params
    modulo = query_params.get("modulo", "home")

    if modulo == "home" or not modulo:
        pagina_home()
    elif modulo == "processador_txt":
        modulo_processador_txt()
    elif modulo == "mastersaf":
        modulo_mastersaf()
    elif modulo == "siscomex":
        modulo_siscomex()
    else:
        pagina_home()

if __name__ == "__main__":
    main()