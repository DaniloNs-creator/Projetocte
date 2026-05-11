import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any
import chardet
from io import BytesIO
import time
import xml.etree.ElementTree as ET
import os
import traceback
import numpy as np
import fitz
import pdfplumber
import re
from lxml import etree
import tempfile
import logging
import gc
import sqlite3
from datetime import timedelta, date
from typing import List, Tuple
import io
import contextlib
import base64
import hashlib
import xml.dom.minidom
from pathlib import Path
import random
import zipfile
import shutil
import threading
import subprocess
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# ==============================================================================
# CONFIGURAÇÃO AUTOMÁTICA DO SERVIDOR STREAMLIT
# ==============================================================================
_PDF_CHUNK_PAGES = 50

def setup_streamlit_config():
    try:
        os.makedirs(".streamlit", exist_ok=True)
        config_path = os.path.join(".streamlit", "config.toml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("[server]\nmaxUploadSize = 2000\nmaxMessageSize = 2000\n")
    except Exception:
        pass

setup_streamlit_config()

# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Sistema de Processamento Unificado 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# SESSION STATE
# ==============================================================================
_defaults = {
    'selected_xml': None,
    'parsed_duimp': None, 'parsed_sigraweb': None,
    'merged_df': None, 'last_duimp': None,
    'layout_app2': 'sigraweb',
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================================
# HELPERS UI
# ==============================================================================
def show_loading_animation(message="Processando..."):
    with st.spinner(message):
        pb = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            pb.progress(i + 1)
        pb.empty()

def show_processing_animation(message="Analisando dados..."):
    ph_anim = st.empty()
    with ph_anim.container():
        _, c, _ = st.columns([1, 2, 1])
        with c:
            st.info(f"⏳ {message}")
            sp = st.empty()
            chars = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]
            for i in range(20):
                sp.markdown(f"<div style='text-align:center;font-size:24px;color:#c6ff00;'>{chars[i%8]}</div>",
                            unsafe_allow_html=True)
                time.sleep(0.1)
    ph_anim.empty()

def show_success_animation(message="Concluído!"):
    ph_anim = st.empty()
    with ph_anim.container():
        st.success(f"✅ {message}")
        time.sleep(1.2)
    ph_anim.empty()

def ph(html: str):
    st.markdown(html, unsafe_allow_html=True)

def page_header(icon: str, title: str, sub: str):
    ph(f"""
    <div class="ph">
        <span class="ph-icon">{icon}</span>
        <div><div class="ph-title">{title}</div>
        <div class="ph-sub">{sub}</div></div>
    </div>""")

def section_title(text: str):
    ph(f'<div class="stitle">{text}</div>')

def empty_state(icon: str, title: str, sub: str = ""):
    ph(f"""
    <div class="empty">
        <div class="empty-icon">{icon}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-sub">{sub}</div>
    </div>""")

def status_ok(text: str):
    ph(f'<div class="sbox sbox-ok">✅ {text}</div>')

def status_warn(text: str):
    ph(f'<div class="sbox sbox-warn">⚠️ {text}</div>')

# ==============================================================================
# CSS — DARK MODE COMPLETO
# ==============================================================================
def load_css():
    ph("""<style>
    /* ══════════════════════════════════════════════════════════════════════
       DARK THEME COMPLETO — TODOS OS TEXTOS VISÍVEIS
       ════════════════════════════════════════════════════════════════════ */
    
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #0a0c10 !important;
        color: #d4dbe8 !important;
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }
    
    .block-container { padding-top: 1.2rem !important; }
    
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #0a0c10; border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: #2a2e35; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #3a3e46; }
    
    [data-testid="stSidebar"] { background: #0a0c10 !important; border-right: 1px solid #1f2329 !important; }
    [data-testid="stSidebar"] * { color: #c4ccd8 !important; }
    [data-testid="stSidebar"] label { color: #8b8f98 !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
        background: #0d0f14 !important; border: 1px solid #1f2329 !important; color: #d4dbe8 !important;
    }
    
    .hero {
        position: relative; background: linear-gradient(135deg, #0a0c10 0%, #111318 52%, #161920 100%);
        border: 1px solid #1f2329; border-radius: 16px; padding: 2.4rem 3rem 2rem;
        margin-bottom: 1.4rem; text-align: center; overflow: hidden;
    }
    .hero::before {
        content: ''; position: absolute; inset: 0;
        background-image: linear-gradient(rgba(198,255,0,.03) 1px, transparent 1px),
                         linear-gradient(90deg, rgba(198,255,0,.03) 1px, transparent 1px);
        background-size: 40px 40px; pointer-events: none;
    }
    .hero::after {
        content: ''; position: absolute; right: -60px; top: -60px;
        width: 260px; height: 260px; border-radius: 50%;
        background: radial-gradient(circle, rgba(198,255,0,.08) 0%, transparent 70%); pointer-events: none;
    }
    .hero-logo { max-width: 190px; margin-bottom: .9rem; filter: drop-shadow(0 4px 14px rgba(0,0,0,.5)); position: relative; z-index: 1; }
    .hero-title { font-size: 2.1rem; font-weight: 800; color: #e4e6ea; margin: 0 0 .35rem; letter-spacing: -.6px; line-height: 1.15; position: relative; z-index: 1; }
    .hero-sub { font-size: .92rem; color: #8b8f98; margin: 0 0 1.2rem; position: relative; z-index: 1; }
    .hero-chips { display: flex; justify-content: center; gap: .45rem; flex-wrap: wrap; position: relative; z-index: 1; }
    .chip {
        display: inline-flex; align-items: center; gap: .3rem;
        background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
        color: #8b8f98; border-radius: 20px; padding: .2rem .72rem; font-size: .75rem; font-weight: 600; letter-spacing: .3px;
    }
    .chip:hover { background: rgba(198,255,0,.1); border-color: #c6ff00; color: #c6ff00; }
    
    .ph {
        display: flex; align-items: center; gap: .9rem; background: #111318;
        border: 1px solid #1f2329; border-radius: 8px; padding: .9rem 1.2rem; margin-bottom: 1.1rem;
    }
    .ph-icon { font-size: 1.9rem; flex-shrink: 0; line-height: 1; }
    .ph-title { font-size: 1.25rem; font-weight: 800; color: #c6ff00; line-height: 1.2; }
    .ph-sub { font-size: .8rem; color: #8b8f98; margin-top: .1rem; }
    
    .stitle {
        display: flex; align-items: center; font-size: .92rem; font-weight: 700; color: #c6ff00;
        padding: .45rem 0 .45rem .75rem; border-left: 3px solid #c6ff00;
        margin: 1rem 0 .6rem; background: linear-gradient(90deg, rgba(198,255,0,.04), transparent);
        border-radius: 0 8px 8px 0;
    }
    
    .card { background: #111318; border-radius: 8px; border: 1px solid #1f2329; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
    .card:hover { border-color: #c6ff00; }
    
    .uzone { background: #0d0f14; border: 2px dashed #2a2e35; border-radius: 8px; padding: .85rem 1rem; text-align: center; margin-bottom: .5rem; }
    .uzone:hover { border-color: #c6ff00; background: #111318; }
    .uzone-icon { font-size: 1.5rem; line-height: 1; }
    .uzone-title { font-weight: 700; color: #c6ff00; font-size: .88rem; margin-top: .2rem; }
    .uzone-sub { font-size: .75rem; color: #8b8f98; margin-top: .1rem; }
    
    .sbox { padding: .65rem 1rem; border-radius: 8px; font-size: .88rem; font-weight: 500; margin: .4rem 0; }
    .sbox-ok { background: rgba(5,150,105,.15); color: #6EE7B7; border-left: 3px solid #059669; }
    .sbox-warn { background: rgba(217,119,6,.15); color: #FCD34D; border-left: 3px solid #D97706; }
    
    .lbadge { display: inline-flex; align-items: center; gap: .35rem; background: #2563EB; color: #fff; border-radius: 8px; padding: .3rem .8rem; font-size: .8rem; font-weight: 700; margin-top: .45rem; }
    .lbadge.amber { background: #D97706; }
    
    .empty { text-align: center; padding: 2.8rem 1rem; }
    .empty-icon { font-size: 2.8rem; margin-bottom: .5rem; opacity: .55; }
    .empty-title { font-size: 1rem; font-weight: 700; color: #8b8f98; margin-bottom: .25rem; }
    .empty-sub { font-size: .82rem; color: #5a5e66; }
    
    .ipill {
        display: inline-flex; align-items: center; gap: .35rem;
        background: rgba(198,255,0,.08); border: 1px solid rgba(198,255,0,.2); color: #c6ff00;
        border-radius: 20px; padding: .22rem .8rem; font-size: .78rem; font-weight: 600; margin-bottom: .5rem;
    }
    
    .flabel { font-size: .78rem; font-weight: 600; color: #8b8f98; text-transform: uppercase; letter-spacing: .5px; margin-bottom: .2rem; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 3px; background: #0a0c10; border-radius: 8px; padding: 4px; border: 1px solid #1f2329; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; font-weight: 600; font-size: .86rem; padding: .4rem .95rem; color: #8b8f98 !important; }
    .stTabs [data-baseweb="tab"]:hover { color: #c6ff00 !important; background: rgba(198,255,0,.08); }
    .stTabs [aria-selected="true"] { background: #111318 !important; color: #c6ff00 !important; }
    
    .stButton > button { width: 100%; border-radius: 8px; font-weight: 600; font-size: .86rem; background: #1f2329 !important; color: #d4dbe8 !important; border: 1px solid #2a2e35 !important; }
    .stButton > button:hover { background: #2a2e35 !important; border-color: #c6ff00 !important; color: #c6ff00 !important; }
    .stButton > button[kind="primary"] { background: #c6ff00 !important; color: #0a0c10 !important; border: none !important; font-weight: 700 !important; }
    .stButton > button[kind="primary"]:hover { background: #d4ff1a !important; color: #0a0c10 !important; }
    
    .stDownloadButton > button { border-radius: 8px; font-weight: 600; font-size: .86rem; background: transparent !important; color: #c6ff00 !important; border: 1px solid #c6ff00 !important; }
    .stDownloadButton > button:hover { background: #c6ff00 !important; color: #0a0c10 !important; }
    
    div[data-testid="stRadio"] > div { gap: .45rem; }
    div[data-testid="stRadio"] label { background: #111318; border: 1.5px solid #1f2329; border-radius: 8px; padding: .5rem .9rem; font-weight: 500; font-size: .86rem; color: #d4dbe8 !important; }
    div[data-testid="stRadio"] label:hover { border-color: #c6ff00; background: #161920; }
    
    .streamlit-expanderHeader { font-weight: 600; font-size: .88rem; color: #c6ff00 !important; background: #111318; border-radius: 6px; padding: .45rem .75rem !important; }
    .streamlit-expanderContent { background: #0d0f14; border: 1px solid #1f2329; border-radius: 0 0 6px 6px; }
    
    [data-testid="metric-container"] { background: #111318; border: 1px solid #1f2329; border-radius: 8px; padding: .7rem .9rem; }
    [data-testid="metric-container"]:hover { border-color: #c6ff00; }
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700 !important; color: #c6ff00 !important; }
    [data-testid="stMetricLabel"] { font-size: .74rem !important; font-weight: 600 !important; color: #8b8f98 !important; text-transform: uppercase; letter-spacing: .45px; }
    
    .stTextInput input, .stNumberInput input, .stTextArea textarea { background: #0d0f14 !important; border: 1.5px solid #1f2329 !important; border-radius: 8px !important; font-size: .86rem !important; color: #d4dbe8 !important; }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus { border-color: #c6ff00 !important; }
    .stTextInput label, .stNumberInput label, .stTextArea label { color: #8b8f98 !important; }
    
    .stSelectbox div[data-baseweb="select"] > div { background: #0d0f14 !important; border: 1.5px solid #1f2329 !important; color: #d4dbe8 !important; }
    .stMultiSelect div[data-baseweb="select"] > div { background: #0d0f14 !important; border: 1.5px solid #1f2329 !important; color: #d4dbe8 !important; }
    
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] { background: #0d0f14 !important; border: 1px solid #1f2329 !important; border-radius: 8px; overflow: hidden; }
    [data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th { background: #111318 !important; color: #c6ff00 !important; border-bottom: 2px solid #c6ff00 !important; }
    [data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td { background: #0d0f14 !important; color: #d4dbe8 !important; border-bottom: 1px solid #1f2329 !important; }
    
    .stAlert { background: #111318 !important; border: 1px solid #1f2329 !important; border-radius: 8px !important; color: #d4dbe8 !important; }
    
    code, pre { background: #0d0f14 !important; color: #c6ff00 !important; border: 1px solid #1f2329 !important; border-radius: 8px !important; }
    
    hr { border: none; border-top: 1px solid #1f2329; margin: .9rem 0; }
    
    [data-testid="stProgress"] > div { background: #111318 !important; border: 1px solid #1f2329 !important; border-radius: 4px !important; height: 6px !important; }
    [data-testid="stProgress"] > div > div { background: #c6ff00 !important; border-radius: 4px !important; }
    
    .stSpinner > div { border-color: #c6ff00 transparent transparent transparent !important; }
    
    /* ══════════════════════════════════════════════════════════════════════
       MASTERSAF CONSOLE STYLES
       ════════════════════════════════════════════════════════════════════ */
    
    .ms-console {
        background: #0d0f14; border: 1px solid #1f2329; border-top: 2px solid #c6ff00;
        padding: 1.2rem 1.5rem; font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 0.7rem; color: #8896a8; max-height: 500px; overflow-y: auto;
        line-height: 1.9; white-space: pre-wrap; word-break: break-all;
    }
    
    .ms-topbar {
        background: #111318; padding: 0.6rem 2.5rem; display: flex;
        align-items: center; justify-content: space-between;
        border-bottom: 2px solid #c6ff00; margin-bottom: 1rem;
    }
    
    .ms-topbar-brand {
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 0.78rem; font-weight: 700; color: #e4e6ea;
        letter-spacing: 0.22em; text-transform: uppercase;
    }
    .ms-topbar-brand span { color: #c6ff00; }
    
    .ms-topbar-meta {
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 0.62rem; color: #5a5e66; letter-spacing: 0.12em;
    }
    
    .ms-stat-card { background: #111318; border: 1px solid #1f2329; padding: 1rem 1.2rem; position: relative; overflow: hidden; }
    .ms-stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
    .ms-stat-card.acid::before { background: #c6ff00; }
    .ms-stat-card.blue-accent::before { background: #5b8fff; }
    .ms-stat-card.rust::before { background: #e84a2b; }
    
    .ms-stat-label {
        font-family: 'IBM Plex Mono', 'Courier New', monospace;
        font-size: 0.58rem; letter-spacing: 0.15em; color: #5a5e66;
        text-transform: uppercase; margin-bottom: 0.3rem;
    }
    
    .ms-stat-value { font-family: 'IBM Plex Mono', 'Courier New', monospace; font-size: 1.5rem; font-weight: 700; color: #eef2ff; }
    .ms-stat-value.acid { color: #c6ff00 !important; }
    .ms-stat-value.blue-accent { color: #5b8fff !important; }
    .ms-stat-value.rust { color: #e84a2b !important; }
    
    @media (max-width: 900px) {
        .hero { padding: 1.8rem 1.4rem 1.5rem; }
        .hero-title { font-size: 1.55rem; }
        .hero-logo { max-width: 140px; }
    }
    @media (max-width: 600px) {
        .hero-title { font-size: 1.3rem; }
        .hero { padding: 1.3rem 1rem 1.1rem; border-radius: 12px; }
        .stTabs [data-baseweb="tab"] { padding: .32rem .55rem; font-size: .78rem; }
        .chip { font-size: .68rem; padding: .15rem .55rem; }
    }
    </style>""")


# ==============================================================================
# PARTE 1 — PROCESSADOR TXT (INALTERADO)
# ==============================================================================
def processador_txt():
    page_header("📄", "Processador de Arquivos TXT",
                "Remova linhas indesejadas e substitua padrões em arquivos TXT")

    def detectar_encoding(conteudo):
        return chardet.detect(conteudo)['encoding']

    def processar_arquivo(conteudo, padroes):
        try:
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTERN",
            }
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
            return "\n".join(out), len(linhas)
        except Exception as e:
            st.error(f"Erro ao processar: {str(e)}")
            return None, 0

    padroes_default = ["-------", "SPED EFD-ICMS/IPI"]

    col_up, col_cfg = st.columns([3, 2], gap="large")
    with col_up:
        ph('<p class="flabel">📁 Selecione o arquivo TXT</p>')
        arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])
    with col_cfg:
        with st.expander("⚙️ Padrões adicionais de remoção"):
            padroes_add = st.text_input("Padrões (vírgula)", placeholder="Ex: TOTAL, SOMA")
            padroes = padroes_default + [p.strip() for p in padroes_add.split(",") if p.strip()] if padroes_add else padroes_default
        ph(f'<div class="ipill">🔍 {len(padroes)} padrões ativos</div>')

    if arquivo is not None:
        st.markdown("")
        if st.button("🔄 Processar Arquivo TXT", type="primary", use_container_width=True):
            try:
                show_loading_animation("Analisando arquivo...")
                conteudo = arquivo.read()
                show_processing_animation("Processando linhas...")
                resultado, total = processar_arquivo(conteudo, padroes)
                if resultado is not None:
                    show_success_animation("Processamento concluído!")
                    mantidas = len(resultado.splitlines())
                    removidas = total - mantidas
                    k1, k2, k3 = st.columns(3)
                    k1.metric("📋 Originais", total)
                    k2.metric("✅ Mantidas", mantidas)
                    k3.metric("🗑️ Removidas", removidas, delta=f"-{removidas}", delta_color="inverse")
                    section_title("👁️ Prévia")
                    st.text_area("Conteúdo processado", resultado, height=260)
                    buf = BytesIO()
                    buf.write(resultado.encode('utf-8'))
                    buf.seek(0)
                    st.download_button("⬇️ Baixar arquivo processado", data=buf,
                                       file_name=f"processado_{arquivo.name}",
                                       mime="text/plain", use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {str(e)}")
    else:
        empty_state("📂", "Nenhum arquivo carregado", "Selecione um arquivo .TXT acima para começar")


# ==============================================================================
# PARTE 2 — CAPTURA EM MASSA MASTERSAF (MODIFICADO PARA LOGS EM TEMPO REAL)
# ==============================================================================

class XMLProcessor:
    """Processa arquivos XML extraindo todos os campos disponíveis"""
    def __init__(self):
        self.processed_data = []
    
    def extract_all_fields(self, root):
        fields = {}
        def recursive_extract(element, path=''):
            if element.attrib:
                for attr_key, attr_val in element.attrib.items():
                    full_path = f"{path}/@{attr_key}" if path else f"@{attr_key}"
                    fields[full_path] = attr_val
            children = list(element)
            if children:
                for child in children:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    child_path = f"{path}/{tag}" if path else tag
                    recursive_extract(child, child_path)
            else:
                if element.text and element.text.strip():
                    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
                    full_path = f"{path}/{tag}" if path else tag
                    fields[full_path] = element.text.strip()
        recursive_extract(root)
        return fields
    
    def process_xml_files_from_directory(self, directory_path, log_list):
        xml_files = list(Path(directory_path).glob('*.xml'))
        log_list.append(f"   📄 {len(xml_files)} XMLs encontrados")
        file_data_list = []
        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                root = ET.fromstring(content)
                fields = self.extract_all_fields(root)
                fields['_arquivo_origem'] = xml_file.name
                file_data_list.append(fields)
            except Exception as e:
                pass
        if file_data_list:
            df = pd.DataFrame(file_data_list)
            cols = ['_arquivo_origem'] + [c for c in df.columns if c != '_arquivo_origem']
            df = df[cols]
            self.processed_data = df.to_dict('records')
        return len(file_data_list), len(xml_files)
    
    def export_to_excel(self):
        if self.processed_data:
            df = pd.DataFrame(self.processed_data)
            buf = BytesIO()
            df.to_excel(buf, index=False, sheet_name='Dados_XML')
            buf.seek(0)
            return buf.getvalue(), len(df)
        return None, 0
    
    def clear_data(self):
        self.processed_data = []


def esperar_downloads_mastersaf(directory, timeout=120):
    start_time = time.time()
    while time.time() - start_time < timeout:
        crdownload_files = list(Path(directory).glob('*.crdownload'))
        if not crdownload_files:
            return True
        time.sleep(1)
    return False


def processar_arquivos_baixados_mastersaf(base_dir, log_list):
    log_list.append("=" * 50)
    log_list.append("📦 INICIANDO PROCESSAMENTO DOS ARQUIVOS")
    log_list.append("=" * 50)
    
    zip_files = list(Path(base_dir).glob('*.zip'))
    log_list.append(f"🔍 {len(zip_files)} arquivos ZIP encontrados")
    
    if not zip_files:
        log_list.append("⚠ Nenhum arquivo ZIP para processar!")
        return None, 0, "Nenhum ZIP baixado. Verifique login e datas."
    
    extract_dir = tempfile.mkdtemp(prefix="mastersaf_extracted_")
    all_xml_dirs = []
    
    log_list.append("📂 Extraindo arquivos ZIP...")
    for zip_file in zip_files:
        try:
            zip_name = zip_file.stem
            extract_path = os.path.join(extract_dir, zip_name)
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            all_xml_dirs.append(extract_path)
            log_list.append(f"   ✔ {zip_file.name}")
        except Exception as e:
            log_list.append(f"   ❌ Erro ao extrair {zip_file.name}: {e}")
    
    log_list.append("📄 Processando arquivos XML...")
    processor = XMLProcessor()
    for xml_dir in all_xml_dirs:
        processor.process_xml_files_from_directory(xml_dir, log_list)
    
    total_processados = len(processor.processed_data)
    log_list.append(f"📊 Total de registros extraídos: {total_processados}")
    
    if total_processados > 0:
        log_list.append("📊 Gerando Excel consolidado...")
        excel_bytes, num_registros = processor.export_to_excel()
        processor.clear_data()
        log_list.append(f"✅ Excel gerado com sucesso!")
        log_list.append(f"📈 Total de registros: {num_registros}")
    else:
        processor.clear_data()
        log_list.append("⚠ Nenhum registro extraído dos XMLs")
        excel_bytes, num_registros = None, 0
    
    shutil.rmtree(extract_dir, ignore_errors=True)
    log_list.append("=" * 50)
    return excel_bytes, num_registros, None


# Classe wrapper para execução em thread com callback de logs
class MasterSAFThread(threading.Thread):
    def __init__(self, usuario, senha, dt_ini, dt_fin, loops, processar):
        super().__init__()
        self.usuario = usuario
        self.senha = senha
        self.dt_ini = dt_ini
        self.dt_fin = dt_fin
        self.loops = loops
        self.processar = processar
        self.logs = []
        self.excel_bytes = None
        self.num_registros = 0
        self.error_msg = None
        self.arquivos_capturados = 0
        self.status_final = "running"
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
    
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.logs.append(f"[{ts}] {msg}")
    
    def stop(self):
        self._stop_event.set()
    
    def run(self):
        driver = None
        dl_path = "/tmp/downloads"
        
        try:
            if os.path.exists(dl_path):
                shutil.rmtree(dl_path)
            os.makedirs(dl_path, exist_ok=True)
            
            # Encontrar Chrome
            self.log("Procurando Chrome/Chromium no sistema...")
            chrome_binary = None
            possible_paths = [
                "/usr/bin/chromium", "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", "/snap/bin/chromium"
            ]
            for path in possible_paths:
                if os.path.isfile(path):
                    chrome_binary = path                    break
            
            if not chrome_binary:
                raise Exception("Chrome/Chromium não encontrado. Instale: sudo apt-get install chromium-browser")
            
            self.log(f"Browser encontrado: {chrome_binary}")
            
            # Configurar Chrome
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920x1080")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.binary_location = chrome_binary
            
            prefs = {
                "download.default_directory": dl_path,
                "download.prompt_for_download": False,
                "directory_upgrade": True,
                "safebrowsing.enabled": False,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.log("Inicializando ChromeDriver...")
            driver = webdriver.Chrome(options=chrome_options)
            self.log("ChromeDriver inicializado com sucesso!")
            
            # Login
            self.log("Acessando portal MasterSAF...")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            time.sleep(3)
            
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(self.usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(self.senha)
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="enter"]'))
            time.sleep(5)
            self.log("Autenticação realizada com sucesso.")
            
            # Navegar
            self.log("Navegando até Listagem de CT-es (Receptor)...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(4)
            
            # Configurar período
            self.log(f"Configurando período: {self.dt_ini} → {self.dt_fin}")
            el_ini = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
            el_ini.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
            el_ini.send_keys(self.dt_ini)
            el_fin = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
            el_fin.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
            el_fin.send_keys(self.dt_fin)
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
            time.sleep(4)
            self.log("Base de dados atualizada.")
            
            # Selecionar 100 registros
            self.log("Configurando exibição: 100 registros por página...")
            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
            time.sleep(4)
            
            # Loop de captura
            total_paginas = int(self.loops)
            self.log(f"Iniciando captura em massa: {total_paginas} página(s)...")
            
            for i in range(total_paginas):
                if self._stop_event.is_set():
                    self.log("⚠ Captura interrompida pelo usuário.")
                    break
                    
                pagina_atual = i + 1
                self.log(f"Processando página {pagina_atual}/{total_paginas}...")
                
                # Seleciona todos
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                time.sleep(1)
                
                # Download múltiplo
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                time.sleep(1)
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                self.log(f"Download da página {pagina_atual} iniciado...")
                
                esperar_downloads_mastersaf(dl_path)
                time.sleep(5)
                
                # Desmarca
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                time.sleep(1)
                
                # Próxima página
                if pagina_atual < total_paginas:
                    driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))
                    time.sleep(3)
                
                self.log(f"Página {pagina_atual} concluída.")
                time.sleep(2)
            
            self.log("Captura finalizada!")
            
            # Contar arquivos
            zip_files = list(Path(dl_path).glob('*.zip'))
            self.arquivos_capturados = len(zip_files)
            
            # Pós-processamento
            if self.processar:
                excel_bytes, num_registros, err = processar_arquivos_baixados_mastersaf(dl_path, self.logs)
                self.excel_bytes = excel_bytes
                self.num_registros = num_registros
                if err:
                    self.error_msg = err
            else:
                self.log("⚠ Processamento desativado. Arquivos disponíveis em /tmp/downloads")
            
            self.status_final = "done"
            
        except Exception as e:
            self.log(f"❌ ERRO CRÍTICO: {str(e)}")
            self.log(traceback.format_exc())
            self.error_msg = str(e)
            self.status_final = "done"
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            self.log("Processo finalizado.")


def processador_mastersaf():
    # Inicializa session state específico
    ms_defaults = {
        'ms_running': False, 'ms_done': False,
        'ms_error_msg': '', 'ms_logs': [],
        'ms_excel_bytes': None, 'ms_xml_count': 0,
        'ms_arquivos_capturados': 0, 'ms_status_final': 'idle',
        'ms_total_paginas': 0, 'ms_resultado_pronto': False,
        'ms_thread': None,
    }
    for k, v in ms_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    # Topbar
    ph("""
    <div class="ms-topbar">
        <div class="ms-topbar-brand">MASTER<span>SAF</span> &nbsp;// XML AUTOMATION ENGINE</div>
        <div class="ms-topbar-meta">v4.0.0 &nbsp;·&nbsp; CAPTURA EM MASSA &nbsp;·&nbsp; MÓDULO FISCAL</div>
    </div>
    """)
    
    left_col, right_col = st.columns([1.05, 2], gap="small")
    
    with left_col:
        with st.container():
            ph("""
            <div style="background:#111318; padding:2.2rem 2rem 0.5rem; border-right:1px solid #1f2329;">
                <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.25em; text-transform:uppercase; color:#c6ff00; margin-bottom:0.3rem;">Módulo de Captura</div>
                <div style="font-family:'Syne',sans-serif; font-size:1.55rem; font-weight:800; color:#e4e6ea; line-height:1.1; margin-bottom:0.4rem;">Captura<br>em Massa</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:0.66rem; color:#8b8f98; line-height:1.6; margin-bottom:1.2rem;">Extração automatizada de XMLs<br>via portal MasterSAF · até 1000 págs.</div>
            </div>
            """)
        
        ph("""
        <div style="background:#111318; padding:0 2rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#c6ff00; margin-bottom:0.5rem;">🔐 Credenciais de Acesso</div>
        </div>
        """)
        
        usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="ms_usr", disabled=st.session_state.ms_running)
        senha = st.text_input("Senha", type="password", placeholder="••••••••", key="ms_pwd", disabled=st.session_state.ms_running)
        
        ph("""
        <div style="background:#111318; padding:0 2rem;">
            <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">📅 Período de Consulta</div>
        </div>
        """)
        
        col_a, col_b = st.columns(2)
        with col_a:
            data_ini = st.text_input("Data Inicial", value="08/05/2026", key="ms_di", disabled=st.session_state.ms_running)
        with col_b:
            data_fin = st.text_input("Data Final", value="08/05/2026", key="ms_df", disabled=st.session_state.ms_running)
        
        ph("""
        <div style="background:#111318; padding:0 2rem;">
            <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">⚙️ Parâmetros</div>
        </div>
        """)
        
        qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5, key="ms_loops", disabled=st.session_state.ms_running)
        
        ph("""
        <div style="background:#111318; padding:0 2rem;">
            <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">📊 Pós-Processamento</div>
        </div>
        """)
        
        processar_xml = st.checkbox("Extrair ZIPs e processar XMLs para Excel", value=True, key="ms_processar", disabled=st.session_state.ms_running)
        
        ph('<div style="background:#111318; padding:0 2rem 2rem;"><br></div>')
        
        if not st.session_state.ms_running:
            iniciar = st.button("⚡ INICIAR AUTOMAÇÃO", key="ms_iniciar", type="primary")
        else:
            # Botão de parar durante execução
            st.button("🛑 PARAR AUTOMAÇÃO", key="ms_parar", type="secondary", on_click=lambda: st.session_state.ms_thread.stop() if st.session_state.ms_thread else None)
            iniciar = False
    
    with right_col:
        ph("""
        <div style="padding:2.4rem 2.8rem 1.5rem;">
            <div style="display:flex; align-items:baseline; gap:1rem; margin-bottom:1.8rem; padding-bottom:1.2rem; border-bottom:1px solid #1f2329;">
                <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:800; color:#e4e6ea; text-transform:uppercase; letter-spacing:0.06em;">Console de Execução</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; color:#5a5e66; letter-spacing:0.12em;">REAL-TIME MONITOR</div>
            </div>
        </div>
        """)
        
        # Stats placeholder
        stats_placeholder = st.empty()
        
        # Alertas placeholder
        alert_placeholder = st.empty()
        
        # Log console placeholder
        console_placeholder = st.empty()
        
        # Download placeholder
        download_placeholder = st.empty()
    
    # ═══════════════════════════════════════════════════════════════
    # LÓGICA DE LOGS EM TEMPO REAL - POLLING DA THREAD
    # ═══════════════════════════════════════════════════════════════
    
    if st.session_state.ms_running and not st.session_state.ms_done:
        # Atualiza os stat cards e console com os logs atuais da thread
        thread = st.session_state.ms_thread
        if thread:
            # Copia os logs atuais com lock
            with thread._lock:
                current_logs = list(thread.logs)
                current_status = thread.status_final
                current_error = thread.error_msg
                current_excel = thread.excel_bytes
                current_xml_count = thread.num_registros
                current_arquivos = thread.arquivos_capturados
            
            # Atualiza stat cards
            with stats_placeholder.container():
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    ph(f"""
                    <div class="ms-stat-card acid">
                        <div class="ms-stat-label">Págs. Processadas</div>
                        <div class="ms-stat-value acid">{int(qtd_loops):02d}</div>
                    </div>""")
                with sc2:
                    ph(f"""
                    <div class="ms-stat-card blue-accent">
                        <div class="ms-stat-label">ZIPs Capturados</div>
                        <div class="ms-stat-value blue-accent">{current_arquivos:03d}</div>
                    </div>""")
                with sc3:
                    ph(f"""
                    <div class="ms-stat-card">
                        <div class="ms-stat-label">Registros XML</div>
                        <div class="ms-stat-value">{current_xml_count:04d}</div>
                    </div>""")
                with sc4:
                    status_display = "RUNNING" if current_status == "running" else "DONE"
                    ph(f"""
                    <div class="ms-stat-card rust">
                        <div class="ms-stat-label">Status</div>
                        <div class="ms-stat-value rust" style="font-size:0.9rem; padding-top:0.4rem;">{status_display}</div>
                    </div>""")
            
            # Atualiza alertas
            with alert_placeholder.container():
                if current_error:
                    st.error(f"❌ {current_error}")
                elif current_status == "done" and current_excel:
                    st.success(f"✅ Captura concluída! {current_xml_count} registros extraídos.")
                elif current_status == "done":
                    st.info(f"Captura finalizada. {current_xml_count} registros.")
                else:
                    st.info("⏳ Automação em andamento...")
            
            # Atualiza console
            with console_placeholder.container():
                log_text = "\n".join(current_logs[-80:]) if current_logs else "[ — ] Aguardando início..."
                ph(f'<div class="ms-console">{log_text}</div>')
            
            # Verifica se terminou
            if current_status == "done":
                # Atualiza session state com resultados finais
                st.session_state.ms_logs = current_logs
                st.session_state.ms_excel_bytes = current_excel
                st.session_state.ms_xml_count = current_xml_count
                st.session_state.ms_error_msg = current_error or ''
                st.session_state.ms_arquivos_capturados = current_arquivos
                st.session_state.ms_total_paginas = int(qtd_loops)
                st.session_state.ms_done = True
                st.session_state.ms_running = False
                st.session_state.ms_status_final = "done"
                
                # Download
                if current_excel:
                    with download_placeholder.container():
                        st.markdown("---")
                        periodo = f"{data_ini.replace('/','_')}_a_{data_fin.replace('/','_')}"
                        st.download_button(
                            label=f"📥  BAIXAR EXCEL CONSOLIDADO — {current_xml_count} registro(s)",
                            data=current_excel,
                            file_name=f"MasterSAF_Captura_{periodo}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="ms_download"
                        )
                
                time.sleep(1)
                st.rerun()
            else:
                # Ainda rodando - faz polling
                time.sleep(1)
                st.rerun()
        else:
            # Thread não existe mais (erro?)
            with console_placeholder.container():
                ph('<div class="ms-console">[ — ] Thread não encontrada. Reinicie o processo.</div>')
            time.sleep(1)
            st.rerun()
    
    # Estado inicial ou após conclusão (sem thread rodando)
    if not st.session_state.ms_running:
        # Exibe stats finais ou zerados
        with stats_placeholder.container():
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                ph(f"""
                <div class="ms-stat-card acid">
                    <div class="ms-stat-label">Págs. Processadas</div>
                    <div class="ms-stat-value acid">{st.session_state.ms_total_paginas:02d}</div>
                </div>""")
            with sc2:
                ph(f"""
                <div class="ms-stat-card blue-accent">
                    <div class="ms-stat-label">ZIPs Capturados</div>
                    <div class="ms-stat-value blue-accent">{st.session_state.ms_arquivos_capturados:03d}</div>
                </div>""")
            with sc3:
                ph(f"""
                <div class="ms-stat-card">
                    <div class="ms-stat-label">Registros XML</div>
                    <div class="ms-stat-value">{st.session_state.ms_xml_count:04d}</div>
                </div>""")
            with sc4:
                status_display = "IDLE"
                if st.session_state.ms_done:
                    status_display = "DONE"
                ph(f"""
                <div class="ms-stat-card rust">
                    <div class="ms-stat-label">Status</div>
                    <div class="ms-stat-value rust" style="font-size:0.9rem; padding-top:0.4rem;">{status_display}</div>
                </div>""")
        
        # Exibe alertas
        if st.session_state.ms_error_msg:
            with alert_placeholder.container():
                st.error(f"❌ {st.session_state.ms_error_msg}")
        elif st.session_state.ms_done and st.session_state.ms_excel_bytes:
            with alert_placeholder.container():
                st.success(f"✅ Captura concluída! {st.session_state.ms_xml_count} registros extraídos.")
        elif st.session_state.ms_done:
            with alert_placeholder.container():
                st.info(f"Captura finalizada. {st.session_state.ms_xml_count} registros.")
        
        # Exibe console
        with console_placeholder.container():
            log_text = "\n".join(st.session_state.ms_logs[-80:]) if st.session_state.ms_logs else "[ — ] Sistema pronto. Configure as credenciais e clique em iniciar.\n[ — ] Chrome/Selenium em standby.\n[ — ] Diretório de saída: /tmp/downloads"
            ph(f'<div class="ms-console">{log_text}</div>')
        
        # Download se existir
        if st.session_state.ms_done and st.session_state.ms_excel_bytes:
            with download_placeholder.container():
                st.markdown("---")
                periodo = f"{data_ini.replace('/','_')}_a_{data_fin.replace('/','_')}"
                st.download_button(
                    label=f"📥  BAIXAR EXCEL CONSOLIDADO — {st.session_state.ms_xml_count} registro(s)",
                    data=st.session_state.ms_excel_bytes,
                    file_name=f"MasterSAF_Captura_{periodo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="ms_download"
                )
    
    # Disparo da execução
    if iniciar:
        if not usuario or not senha:
            st.error("⚠️ Preencha usuário e senha para continuar.")
        else:
            # Resetar state
            st.session_state.ms_running = True
            st.session_state.ms_done = False
            st.session_state.ms_error_msg = ''
            st.session_state.ms_logs = []
            st.session_state.ms_excel_bytes = None
            st.session_state.ms_xml_count = 0
            st.session_state.ms_arquivos_capturados = 0
            st.session_state.ms_total_paginas = 0
            st.session_state.ms_status_final = "running"
            
            # Criar e iniciar thread
            thread = MasterSAFThread(usuario, senha, data_ini, data_fin, int(qtd_loops), processar_xml)
            thread.start()
            st.session_state.ms_thread = thread
            
            # Primeiro rerun para iniciar o loop de polling
            time.sleep(0.5)
            st.rerun()


# ==============================================================================
# PARTE 3 — HAFELE PDF PARSER (INALTERADO)
# ==============================================================================
class HafelePDFParser:
    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}
        self._buffer = ""

    @staticmethod
    def _parse_valor(v: str) -> float:
        try: return float(v.strip().replace('.','').replace(',','.')) if v else 0.0
        except: return 0.0

    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            prog_txt = st.empty()
            prog_bar = st.progress(0)
            items_found: list = []
            self._buffer = ""
            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                chunk = _PDF_CHUNK_PAGES
                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(f"Processando páginas {start+1}–{end} de {total} (Extrato DUIMP)...")
                    prog_bar.progress(end / total)
                    chunk_lines = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t: chunk_lines.append(t)
                    chunk_text = self._buffer + "\n".join(chunk_lines)
                    is_last = (end == total)
                    new_items, self._buffer = self._extract_items_from_chunk(chunk_text, is_last=is_last)
                    items_found.extend(new_items)
                    del chunk_lines, chunk_text
                    gc.collect()
            prog_txt.empty(); prog_bar.empty()
            if self._buffer.strip():
                new_items, _ = self._extract_items_from_chunk(self._buffer, is_last=True)
                items_found.extend(new_items)
            if not items_found:
                st.warning("⚠️ Padrão 'ITENS DA DUIMP' não encontrado.")
            self.documento['itens'] = items_found
            self._calculate_totals()
            return self.documento
        except Exception as e:
            logger.error(f"Erro HafelePDFParser: {e}")
            st.error(f"Erro ao ler PDF: {str(e)}")
            return self.documento

    def _extract_items_from_chunk(self, text: str, is_last: bool):
        pattern = r'(ITENS\s+DA\s+DUIMP\s*-\s*\d+)'
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        items_found = []
        if len(parts) <= 1:
            return items_found, (text if not is_last else "")
        n_complete = len(parts) - 1 if not is_last else len(parts)
        for i in range(1, n_complete, 2):
            header = parts[i]
            content = parts[i+1] if (i+1) < len(parts) else ''
            m = re.search(r'(\d+)', header)
            num = int(m.group(1)) if m else (i // 2)
            item = self._parse_item_block(num, content)
            if item: items_found.append(item)
        if not is_last and len(parts) >= 2:
            last_header = parts[-2] if len(parts) % 2 == 0 else ""
            last_content = parts[-1]
            residual = last_header + last_content
        else:
            residual = ""
        return items_found, residual

    def _parse_item_block(self, item_num: int, text: str) -> Dict:
        try:
            pv = self._parse_valor
            item = {
                'numero_item': item_num, 'numeroAdicao': str(item_num).zfill(3),
                'ncm':'', 'codigo_interno':'', 'nome_produto':'',
                'quantidade':0.0, 'quantidade_comercial':0.0,
                'peso_liquido':0.0, 'valor_total':0.0,
                'ii_valor_devido':0.0,'ii_base_calculo':0.0,'ii_aliquota':0.0,
                'ipi_valor_devido':0.0,'ipi_base_calculo':0.0,'ipi_aliquota':0.0,
                'pis_valor_devido':0.0,'pis_base_calculo':0.0,'pis_aliquota':0.0,
                'cofins_valor_devido':0.0,'cofins_base_calculo':0.0,'cofins_aliquota':0.0,
                'frete_internacional':0.0,'seguro_internacional':0.0,
                'local_aduaneiro':0.0,'aduaneiro_reais':0.0,'valorAduaneiroReal':0.0,
                'paisOrigem':'','fornecedor_raw':'','endereco_raw':'',
                'unidade':'UNIDADE','pesoLiq':'0','valorTotal':'0','valorUnit':'0',
                'moeda':'EURO/COM.EUROPEIA',
            }
            m = re.search(r'Código interno\s*([\d\.]+)', text, re.IGNORECASE)
            if m: item['codigo_interno'] = m.group(1).replace('.','')
            m = re.search(r'(\d{4}\.\d{2}\.\d{2})', text)
            if m: item['ncm'] = m.group(1).replace('.','')
            m = re.search(r'Qtde Unid\. Comercial\s*([\d\.,]+)', text)
            if m: item['quantidade_comercial'] = pv(m.group(1))
            m = re.search(r'Qtde Unid\. Estatística\s*([\d\.,]+)', text)
            item['quantidade'] = pv(m.group(1)) if m else item['quantidade_comercial']
            m = re.search(r'Valor Tot\. Cond Venda\s*([\d\.,]+)', text)
            if m: item['valor_total'] = pv(m.group(1)); item['valorTotal'] = m.group(1)
            m = re.search(r'Peso Líquido \(KG\)\s*([\d\.,]+)', text, re.IGNORECASE)
            if m: item['peso_liquido'] = pv(m.group(1)); item['pesoLiq'] = m.group(1)
            m = re.search(r'Frete Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if m: item['frete_internacional'] = pv(m.group(1))
            m = re.search(r'Seguro Internac\. \(R\$\)\s*([\d\.,]+)', text)
            if m: item['seguro_internacional'] = pv(m.group(1))
            m = re.search(r'Local Aduaneiro \(R\$\)\s*([\d\.,]+)', text)
            if m:
                item['local_aduaneiro'] = pv(m.group(1))
                item['aduaneiro_reais'] = item['local_aduaneiro']
                item['valorAduaneiroReal'] = item['local_aduaneiro']
            tax_pats = re.findall(
                r'Base de Cálculo.*?\(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+).*?Valor.*?\(R\$\)\s*([\d\.,]+)',
                text, re.DOTALL | re.IGNORECASE)
            for base_s, aliq_s, val_s in tax_pats:
                base = pv(base_s); aliq = pv(aliq_s); val = pv(val_s)
                if 1.60 <= aliq <= 3.00:
                    item['pis_aliquota']=aliq; item['pis_base_calculo']=base; item['pis_valor_devido']=val
                elif 7.00 <= aliq <= 12.00:
                    item['cofins_aliquota']=aliq; item['cofins_base_calculo']=base; item['cofins_valor_devido']=val
                elif aliq > 12.00:
                    item['ii_aliquota']=aliq; item['ii_base_calculo']=base; item['ii_valor_devido']=val
                elif aliq >= 0 and item['ipi_aliquota']==0:
                    item['ipi_aliquota']=aliq; item['ipi_base_calculo']=base; item['ipi_valor_devido']=val
            item['total_impostos']=(item['ii_valor_devido']+item['ipi_valor_devido']
                                    +item['pis_valor_devido']+item['cofins_valor_devido'])
            item['valor_total_com_impostos']=item['valor_total']+item['total_impostos']
            return item
        except Exception as e:
            logger.error(f"Erro item {item_num}: {e}"); return None

    def _calculate_totals(self):
        if self.documento['itens']:
            itens = self.documento['itens']
            self.documento['totais'] = {
                'valor_total_mercadoria': sum(i['valor_total'] for i in itens),
                'total_valor_aduaneiro': sum(i.get('aduaneiro_reais',0) for i in itens),
                'total_ii': sum(i['ii_valor_devido'] for i in itens),
                'total_ipi': sum(i['ipi_valor_devido'] for i in itens),
                'total_pis': sum(i['pis_valor_devido'] for i in itens),
                'total_cofins': sum(i['cofins_valor_devido'] for i in itens),
                'total_frete': sum(i['frete_internacional'] for i in itens),
                'total_seguro': sum(i['seguro_internacional'] for i in itens),
                'quantidade_adicoes': len(itens),
            }


# ==============================================================================
# PARTE 4 — SIGRAWEB PDF PARSER (INALTERADO)
# ==============================================================================
class SigrawebPDFParser:
    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}

    @staticmethod
    def _parse_valor(v: str) -> float:
        try: return float(str(v).strip().replace('.','').replace(',','.')) if v else 0.0
        except: return 0.0

    @staticmethod
    def _fmt_date(d: str) -> str:
        try: return datetime.strptime(d.strip(), '%d/%m/%Y').strftime('%Y%m%d')
        except: return d.replace('/','').replace('-','')[:8]

    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            prog_txt = st.empty(); prog_bar = st.progress(0)
            items_found: list = []; buffer = ""
            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages); chunk = _PDF_CHUNK_PAGES
                p1 = pdf.pages[0].extract_text(layout=False) or "" if total > 0 else ""
                p2 = pdf.pages[1].extract_text(layout=False) or "" if total > 1 else ""
                self._extract_header(p1, p2); del p1, p2
                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(f"Processando páginas {start+1}–{end} de {total} (Sigraweb)...")
                    prog_bar.progress(end / total)
                    chunk_pages = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t: chunk_pages.append(t)
                    chunk_text = buffer + "\n".join(chunk_pages)
                    is_last = (end == total)
                    new_items, buffer = self._extract_items_from_chunk(chunk_text, is_last=is_last)
                    items_found.extend(new_items)
                    del chunk_pages, chunk_text; gc.collect()
            prog_txt.empty(); prog_bar.empty()
            if buffer.strip():
                new_items, _ = self._extract_items_from_chunk(buffer, is_last=True)
                items_found.extend(new_items)
            if not items_found:
                st.warning("⚠️ Nenhuma adição detectada no PDF Sigraweb.")
            self.documento['itens'] = items_found
            self._calculate_totals()
            return self.documento
        except Exception as e:
            logger.error(f"Erro SigrawebPDFParser: {e}")
            st.error(f"Erro ao ler PDF Sigraweb: {str(e)}")
            return self.documento

    def _extract_items_from_chunk(self, text: str, is_last: bool):
        pattern = r'Informações da Adição Nº:\s*(\d+)'
        parts = re.split(pattern, text)
        items_found = []
        if len(parts) <= 1:
            return items_found, (text if not is_last else "")
        n_complete = len(parts) - 1 if not is_last else len(parts)
        for i in range(1, n_complete, 2):
            num_str = parts[i].strip()
            content = parts[i+1] if (i+1) < len(parts) else ''
            item = self._parse_item_block(num_str, content)
            if item: items_found.append(item)
        if not is_last and len(parts) >= 2:
            last_num = parts[-2] if len(parts) % 2 == 0 else ""
            last_content = parts[-1]
            residual = (f"Informações da Adição Nº: {last_num}\n" if last_num else "") + last_content
        else:
            residual = ""
        return items_found, residual

    def _extract_header(self, p1: str, p2: str):
        def _f(pat, text, default=''):
            m = re.search(pat, text)
            return m.group(1).strip() if m else default
        h = {}
        h['numeroDI'] = _f(r'Número DI:\s*([\w]+)', p1)
        h['sigraweb'] = _f(r'SIGRAWEB:\s*([\w]+)', p1)
        h['cnpj'] = _f(r'CNPJ:\s*([\d\.\/\-]+)', p1)
        h['nomeImportador'] = _f(r'Nome da Empresa:\s*(.+?)(?:\n|CNPJ)', p1)
        dr = _f(r'Data Registro:([\d\-T:\.+]+)', p1)
        h['dataRegistro'] = dr[:10].replace('-','') if dr else ''
        h['pesoBruto'] = _f(r'Peso Bruto:([\d\.,]+)', p1)
        h['pesoLiquido'] = _f(r'Peso Líquido:([\d\.,]+)', p1)
        h['volumes'] = _f(r'Volumes:([\d]+)', p1)
        h['embalagem'] = _f(r'Embalagem:(\w+)', p1)
        h['urf'] = _f(r'URF de Entrada:\s*(\d+)', p1, '0917900')
        h['urfDespacho'] = _f(r'URF de Despacho:\s*(\d+)', p1, '0917900')
        h['modalidade'] = _f(r'Modalidade de Despacho:\s*(.+?)(?:\n)', p1, 'Normal')
        h['viaTransporte'] = _f(r'Via Transporte:\s*(.+?)(?:\n)', p1, 'Aéreo')
        pais_raw = _f(r'País de Procedência:\s*\d+\s*(.+?)(?:\n|Local|Incoterms)', p1)
        h['paisProcedencia'] = pais_raw.strip() if pais_raw else 'Alemanha'
        h['localEmbarque'] = _f(r'Local de Embarque:\s*(.+?)(?:\n|Data)', p1)
        h['dataEmbarque'] = _f(r'Data de Embarque:\s*([\d\/]+)', p1)
        h['dataChegada'] = _f(r'Data de Chegada no Brasil:\s*([\d\/]+)', p1)
        h['incoterms'] = _f(r'Incoterms:\s*(\w+)', p1, 'FCA')
        h['idtConhecimento'] = _f(r'IDT\. Conhecimento:\s*([\w]+)', p1)
        h['idtMaster'] = _f(r'IDT\. Master:\s*([\w]+)', p1)
        h['transportador'] = _f(r'Transportador:\s*(.+?)(?:\n|Agente)', p1)
        h['agenteCarga'] = _f(r'Agente de Carga:\s*(.+?)(?:\n|CE)', p1)
        combined = p1 + "\n" + p2
        h['taxaEUR'] = _f(r'Taxa EUR:\s*([\d\.,]+)', combined)
        h['taxaDolar'] = _f(r'Taxa do Dólar:\s*([\d\.,]+)', combined)
        h['fobEUR'] = _f(r'FOB:\s*([\d\.,]+)\s*\(EUR\)', combined)
        h['fobUSD'] = _f(r'FOB:.*?\(EUR\)\s*;\s*([\d\.,]+)\s*\(USD\)', combined)
        h['fobBRL'] = _f(r'FOB:.*?\(USD\);\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['freteEUR'] = _f(r'Frete:\s*([\d\.,]+)\s*\(EUR\)', combined)
        h['freteUSD'] = _f(r'Frete:.*?\(EUR\)\s*;\s*([\d\.,]+)\s*\(USD\)', combined)
        h['freteBRL'] = _f(r'Frete:.*?\(USD\);\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['seguroUSD'] = _f(r'Seguro:\s*([\d\.,]+)\s*\(USD\)', combined)
        h['seguroBRL'] = _f(r'Seguro:.*?;\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['cifUSD'] = _f(r'CIF:\s*([\d\.,]+)\s*\(USD\)', combined)
        h['cifBRL'] = _f(r'CIF:.*?;\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['valorAduaneiroUSD'] = _f(r'Valor Aduaneiro:\s*([\d\.,]+)\s*\(USD\)', combined)
        h['valorAduaneiroBRL'] = _f(r'Valor Aduaneiro:.*?;\s*([\d\.,]+)\s*\(BRL\)', combined)
        tm = re.search(r'([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+Itau\s+(\d+)\s+([\d\-]+)', p1)
        if tm:
            h['totalII']=tm.group(1); h['totalIPI']=tm.group(2)
            h['totalPIS']=tm.group(3); h['totalCOFINS']=tm.group(4)
            h['totalSiscomex']=tm.group(5); h['banco']='Itau'
            h['agencia']=tm.group(6); h['conta']=tm.group(7)
        else:
            h['totalII']=h['totalIPI']=h['totalPIS']=h['totalCOFINS']='0'
            h['totalSiscomex']='0'
        h['dataEmbarqueISO'] = self._fmt_date(h['dataEmbarque']) if h['dataEmbarque'] else ''
        h['dataChegadaISO'] = self._fmt_date(h['dataChegada']) if h['dataChegada'] else ''
        self.documento['cabecalho'] = h

    def _parse_item_block(self, num_str: str, text: str) -> Optional[Dict]:
        try:
            pv = self._parse_valor
            item = {
                'numero_item': int(num_str), 'numeroAdicao': num_str.zfill(3),
                'ncm':'', 'codigo_interno':'', 'descricao':'',
                'paisOrigem':'', 'fornecedor_raw':'HAFELE SE & CO KG', 'endereco_raw':'',
                'quantidade':'0', 'quantidade_comercial':'0', 'unidade':'PECA',
                'pesoLiq':'0', 'valorTotal':'0', 'valorUnit':'0',
                'valorAduaneiroReal':0.0, 'valorAduaneiroUSD':0.0, 'aduaneiro_reais':0.0,
                'moeda':'EURO/COM.EUROPEIA',
                'freteUSD':0.0,'freteReal':0.0,'seguroUSD':0.0,'seguroReal':0.0,
                'frete_internacional':0.0,'seguro_internacional':0.0,'local_aduaneiro':0.0,
                'ii_aliquota':0.0,'ii_base_calculo':0.0,'ii_valor_devido':0.0,
                'ipi_aliquota':0.0,'ipi_base_calculo':0.0,'ipi_valor_devido':0.0,
                'pis_aliquota':0.0,'pis_base_calculo':0.0,'pis_valor_devido':0.0,
                'cofins_aliquota':0.0,'cofins_base_calculo':0.0,'cofins_valor_devido':0.0,
            }
            m = re.search(r'NR NCM:\s*(\d+)', text)
            if m: item['ncm'] = m.group(1)
            m = re.search(r'Part Number:\s*([\S]+)\s*\|\s*Descrição:\s*(.+?)(?=\nFabricante:|$)', text, re.DOTALL)
            if m:
                item['codigo_interno'] = m.group(1).strip()
                item['descricao'] = re.sub(r'\s+',' ', m.group(2).strip())
            else:
                m2 = re.search(r'Descrição:\s*(.+?)(?=\nFabricante:|$)', text, re.DOTALL)
                if m2: item['descricao'] = re.sub(r'\s+',' ', m2.group(1).strip())
            m = re.search(r'Peso Líquido:\s*([\d\.,]+)', text)
            if m: item['pesoLiq'] = m.group(1)
            m = re.search(r'Qnt\. Estatística:\s*([\d\.,]+)', text)
            if m: item['quantidade'] = m.group(1)
            m = re.search(r'Quantidade:\s*([\d\.,]+)\s+Unidade:', text)
            item['quantidade_comercial'] = m.group(1) if m else item['quantidade']
            m = re.search(r'Unidade:\s*(\S+)', text)
            if m: item['unidade'] = m.group(1).upper()
            m = re.search(r'Valor FOB:\s*([\d\.,]+)\s+EUR', text)
            if m: item['valorTotal'] = m.group(1)
            m = re.search(r'Valor Unitário:\s*([\d\.,]+)', text)
            if m: item['valorUnit'] = m.group(1)
            m = re.search(r'Valor Aduaneiro USD:\s*([\d\.,]+)', text)
            if m: item['valorAduaneiroUSD'] = pv(m.group(1))
            m = re.search(r'Valor Aduaneiro Real:\s*([\d\.,]+)', text)
            if m:
                item['valorAduaneiroReal'] = pv(m.group(1))
                item['aduaneiro_reais'] = pv(m.group(1))
                item['ii_base_calculo'] = pv(m.group(1))
            m = re.search(r'Valor Frete:\s*([\d\.,]+)\s+USD', text)
            if m: item['freteUSD'] = pv(m.group(1))
            m = re.search(r'Valor Frete Real:\s*([\d\.,]+)', text)
            if m: item['freteReal'] = pv(m.group(1)); item['frete_internacional'] = item['freteReal']
            m = re.search(r'Valor Seguro:\s*([\d\.,]+)\s+USD', text)
            if m: item['seguroUSD'] = pv(m.group(1))
            m = re.search(r'Valor Seguro Real:\s*([\d\.,]+)', text)
            if m: item['seguroReal'] = pv(m.group(1)); item['seguro_internacional'] = item['seguroReal']
            m = re.search(r'Moeda LI:\s*(.+?)(?:\n|Valor)', text)
            if m: item['moeda'] = m.group(1).strip()
            m = re.search(r'País Origem:\s*(.+?)(?:\n|Fabricante)', text)
            if m: item['paisOrigem'] = m.group(1).strip()
            m = re.search(r'Fornecedor:\s*(.+?)(?:\n|País)', text)
            if m: item['fornecedor_raw'] = m.group(1).strip()
            m = re.search(r'^II\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m: item['ii_aliquota']=pv(m.group(1)); item['ii_base_calculo']=pv(m.group(2)); item['ii_valor_devido']=pv(m.group(3))
            m = re.search(r'^IPI\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m: item['ipi_aliquota']=pv(m.group(1)); item['ipi_valor_devido']=pv(m.group(3))
            m = re.search(r'^PIS\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m: item['pis_aliquota']=pv(m.group(1)); item['pis_valor_devido']=pv(m.group(3))
            m = re.search(r'^COFINS\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m: item['cofins_aliquota']=pv(m.group(1)); item['cofins_valor_devido']=pv(m.group(3))
            item['total_impostos'] = (item['ii_valor_devido']+item['ipi_valor_devido']
                                      +item['pis_valor_devido']+item['cofins_valor_devido'])
            item['valor_total_com_impostos'] = pv(str(item['valorTotal']))+item['total_impostos']
            return item
        except Exception as e:
            logger.error(f"Erro item {num_str}: {e}"); return None

    def _calculate_totals(self):
        if self.documento['itens']:
            pv = self._parse_valor
            itens = self.documento['itens']
            self.documento['totais'] = {
                'valor_total_fob': sum(pv(str(i.get('valorTotal',0))) for i in itens),
                'peso_liquido_total': sum(pv(str(i.get('pesoLiq',0))) for i in itens),
                'total_valor_aduaneiro': sum(i.get('aduaneiro_reais',0) for i in itens),
                'total_ii': sum(i.get('ii_valor_devido',0) for i in itens),
                'total_ipi': sum(i.get('ipi_valor_devido',0) for i in itens),
                'total_pis': sum(i.get('pis_valor_devido',0) for i in itens),
                'total_cofins': sum(i.get('cofins_valor_devido',0) for i in itens),
                'total_frete': sum(i.get('frete_internacional',0) for i in itens),
                'total_seguro': sum(i.get('seguro_internacional',0) for i in itens),
                'quantidade_adicoes': len(itens),
            }


# ==============================================================================
# PARTE 5 — DUIMP PDF PARSER (INALTERADO)
# ==============================================================================
def montar_descricao_final(desc_complementar, codigo_extra, detalhamento):
    return f"{str(desc_complementar).strip()} - {str(codigo_extra).strip()} - {str(detalhamento).strip()}"


class DuimpPDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.full_text = ""
        self.header = {}
        self.items = []

    def preprocess(self):
        prog_txt = st.empty(); prog_bar = st.progress(0)
        doc = fitz.open(self.pdf_path)
        total = doc.page_count; parts = []
        for start in range(0, total, _PDF_CHUNK_PAGES):
            end = min(start + _PDF_CHUNK_PAGES, total)
            prog_txt.text(f"Pré-processando páginas {start+1}–{end} de {total} (DUIMP)...")
            prog_bar.progress(end / total)
            chunk_lines = []
            for idx in range(start, end):
                page = doc[idx]
                for line in page.get_text("text").split('\n'):
                    ls = line.strip()
                    if "Extrato da DUIMP" in ls: continue
                    if "Data, hora e responsável" in ls: continue
                    if re.match(r'^\d+\s*/\s*\d+$', ls): continue
                    chunk_lines.append(line)
                page = None
            parts.append("\n".join(chunk_lines))
            del chunk_lines; gc.collect()
        doc.close(); prog_txt.empty(); prog_bar.empty()
        self.full_text = "\n".join(parts); del parts; gc.collect()

    def extract_header(self):
        t = self.full_text
        self.header["numeroDUIMP"] = self._r(r"Extrato da Duimp\s+([\w\-\/]+)", t)
        self.header["cnpj"] = self._r(r"CNPJ do importador:\s*([\d\.\/\-]+)", t)
        self.header["nomeImportador"] = self._r(r"Nome do importador:\s*\n?(.+)", t)
        self.header["pesoBruto"] = self._r(r"Peso Bruto \(kg\):\s*([\d\.,]+)", t)
        self.header["pesoLiquido"] = self._r(r"Peso Liquido \(kg\):\s*([\d\.,]+)", t)
        self.header["urf"] = self._r(r"Unidade de despacho:\s*([\d]+)", t)
        self.header["paisProcedencia"] = self._r(r"País de Procedência:\s*\n?(.+)", t)

    def extract_items(self):
        chunks = re.split(r"Item\s+(\d+)", self.full_text)
        if len(chunks) > 1:
            for i in range(1, len(chunks), 2):
                num = chunks[i]; content = chunks[i+1]
                item = {"numeroAdicao": num}
                item["ncm"] = self._r(r"NCM:\s*([\d\.]+)", content)
                item["paisOrigem"] = self._r(r"País de origem:\s*\n?(.+)", content)
                item["quantidade"] = self._r(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content)
                item["quantidade_comercial"] = self._r(r"Quantidade na unidade comercializada:\s*([\d\.,]+)", content)
                item["unidade"] = self._r(r"Unidade estatística:\s*(.+)", content)
                item["pesoLiq"] = self._r(r"Peso líquido \(kg\):\s*([\d\.,]+)", content)
                item["valorUnit"] = self._r(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content)
                item["valorTotal"] = self._r(r"Valor total na condição de venda:\s*([\d\.,]+)", content)
                item["moeda"] = self._r(r"Moeda negociada:\s*(.+)", content)
                m = re.search(r"Código do Exportador Estrangeiro:\s*(.+?)(?=\n\s*(?:Endereço|Dados))", content, re.DOTALL)
                item["fornecedor_raw"] = m.group(1).strip() if m else ""
                m = re.search(r"Endereço:\s*(.+?)(?=\n\s*(?:Dados da Mercadoria|Aplicação))", content, re.DOTALL)
                item["endereco_raw"] = m.group(1).strip() if m else ""
                m = re.search(r"Detalhamento do Produto:\s*(.+?)(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))", content, re.DOTALL)
                item["descricao"] = m.group(1).strip() if m else ""
                m = re.search(r"Descrição complementar da mercadoria:\s*(.+?)(?=\n|$)", content, re.DOTALL)
                item["desc_complementar"] = m.group(1).strip() if m else ""
                self.items.append(item)

    def _r(self, pat, text):
        m = re.search(pat, text)
        return m.group(1).strip() if m else ""


# ==============================================================================
# PARTE 6 — ADICAO_FIELDS_ORDER, FOOTER_TAGS, DataFormatter, XMLBuilder
# ==============================================================================
ADICAO_FIELDS_ORDER = [
    {"tag":"acrescimo","type":"complex","children":[
        {"tag":"codigoAcrescimo","default":"17"},
        {"tag":"denominacao","default":"OUTROS ACRESCIMOS AO VALOR ADUANEIRO"},
        {"tag":"moedaNegociadaCodigo","default":"978"},
        {"tag":"moedaNegociadaNome","default":"EURO/COM.EUROPEIA"},
        {"tag":"valorMoedaNegociada","default":"000000000000000"},
        {"tag":"valorReais","default":"000000000000000"},
    ]},
    {"tag":"cideValorAliquotaEspecifica","default":"00000000000"},
    {"tag":"cideValorDevido","default":"000000000000000"},
    {"tag":"cideValorRecolher","default":"000000000000000"},
    {"tag":"codigoRelacaoCompradorVendedor","default":"3"},
    {"tag":"codigoVinculoCompradorVendedor","default":"1"},
    {"tag":"cofinsAliquotaAdValorem","default":"00965"},
    {"tag":"cofinsAliquotaEspecificaQuantidadeUnidade","default":"000000000"},
    {"tag":"cofinsAliquotaEspecificaValor","default":"0000000000"},
    {"tag":"cofinsAliquotaReduzida","default":"00000"},
    {"tag":"cofinsAliquotaValorDevido","default":"000000000000000"},
    {"tag":"cofinsAliquotaValorRecolher","default":"000000000000000"},
    {"tag":"condicaoVendaIncoterm","default":"FCA"},
    {"tag":"condicaoVendaLocal","default":""},
    {"tag":"condicaoVendaMetodoValoracaoCodigo","default":"01"},
    {"tag":"condicaoVendaMetodoValoracaoNome","default":"METODO 1 - ART. 1 DO ACORDO (DECRETO 92930/86)"},
    {"tag":"condicaoVendaMoedaCodigo","default":"978"},
    {"tag":"condicaoVendaMoedaNome","default":"EURO/COM.EUROPEIA"},
    {"tag":"condicaoVendaValorMoeda","default":"000000000000000"},
    {"tag":"condicaoVendaValorReais","default":"000000000000000"},
    {"tag":"dadosCambiaisCoberturaCambialCodigo","default":"1"},
    {"tag":"dadosCambiaisCoberturaCambialNome","default":"COM COBERTURA CAMBIAL E PAGAMENTO FINAL A PRAZO DE ATE' 180"},
    {"tag":"dadosCambiaisInstituicaoFinanciadoraCodigo","default":"00"},
    {"tag":"dadosCambiaisInstituicaoFinanciadoraNome","default":"N/I"},
    {"tag":"dadosCambiaisMotivoSemCoberturaCodigo","default":"00"},
    {"tag":"dadosCambiaisMotivoSemCoberturaNome","default":"N/I"},
    {"tag":"dadosCambiaisValorRealCambio","default":"000000000000000"},
    {"tag":"dadosCargaPaisProcedenciaCodigo","default":"000"},
    {"tag":"dadosCargaUrfEntradaCodigo","default":"0000000"},
    {"tag":"dadosCargaViaTransporteCodigo","default":"01"},
    {"tag":"dadosCargaViaTransporteNome","default":"MARÍTIMA"},
    {"tag":"dadosMercadoriaAplicacao","default":"REVENDA"},
    {"tag":"dadosMercadoriaCodigoNaladiNCCA","default":"0000000"},
    {"tag":"dadosMercadoriaCodigoNaladiSH","default":"00000000"},
    {"tag":"dadosMercadoriaCodigoNcm","default":"00000000"},
    {"tag":"dadosMercadoriaCondicao","default":"NOVA"},
    {"tag":"dadosMercadoriaDescricaoTipoCertificado","default":"Sem Certificado"},
    {"tag":"dadosMercadoriaIndicadorTipoCertificado","default":"1"},
    {"tag":"dadosMercadoriaMedidaEstatisticaQuantidade","default":"00000000000000"},
    {"tag":"dadosMercadoriaMedidaEstatisticaUnidade","default":"UNIDADE"},
    {"tag":"dadosMercadoriaNomeNcm","default":"DESCRIÇÃO PADRÃO NCM"},
    {"tag":"dadosMercadoriaPesoLiquido","default":"000000000000000"},
    {"tag":"dcrCoeficienteReducao","default":"00000"},
    {"tag":"dcrIdentificacao","default":"00000000"},
    {"tag":"dcrValorDevido","default":"000000000000000"},
    {"tag":"dcrValorDolar","default":"000000000000000"},
    {"tag":"dcrValorReal","default":"000000000000000"},
    {"tag":"dcrValorRecolher","default":"000000000000000"},
    {"tag":"fornecedorCidade","default":""},
    {"tag":"fornecedorLogradouro","default":""},
    {"tag":"fornecedorNome","default":""},
    {"tag":"fornecedorNumero","default":""},
    {"tag":"freteMoedaNegociadaCodigo","default":"978"},
    {"tag":"freteMoedaNegociadaNome","default":"EURO/COM.EUROPEIA"},
    {"tag":"freteValorMoedaNegociada","default":"000000000000000"},
    {"tag":"freteValorReais","default":"000000000000000"},
    {"tag":"iiAcordoTarifarioTipoCodigo","default":"0"},
    {"tag":"iiAliquotaAcordo","default":"00000"},
    {"tag":"iiAliquotaAdValorem","default":"00000"},
    {"tag":"iiAliquotaPercentualReducao","default":"00000"},
    {"tag":"iiAliquotaReduzida","default":"00000"},
    {"tag":"iiAliquotaValorCalculado","default":"000000000000000"},
    {"tag":"iiAliquotaValorDevido","default":"000000000000000"},
    {"tag":"iiAliquotaValorRecolher","default":"000000000000000"},
    {"tag":"iiAliquotaValorReduzido","default":"000000000000000"},
    {"tag":"iiBaseCalculo","default":"000000000000000"},
    {"tag":"iiFundamentoLegalCodigo","default":"00"},
    {"tag":"iiMotivoAdmissaoTemporariaCodigo","default":"00"},
    {"tag":"iiRegimeTributacaoCodigo","default":"1"},
    {"tag":"iiRegimeTributacaoNome","default":"RECOLHIMENTO INTEGRAL"},
    {"tag":"ipiAliquotaAdValorem","default":"00000"},
    {"tag":"ipiAliquotaEspecificaCapacidadeRecipciente","default":"00000"},
    {"tag":"ipiAliquotaEspecificaQuantidadeUnidadeMedida","default":"000000000"},
    {"tag":"ipiAliquotaEspecificaTipoRecipienteCodigo","default":"00"},
    {"tag":"ipiAliquotaEspecificaValorUnidadeMedida","default":"0000000000"},
    {"tag":"ipiAliquotaNotaComplementarTIPI","default":"00"},
    {"tag":"ipiAliquotaReduzida","default":"00000"},
    {"tag":"ipiAliquotaValorDevido","default":"000000000000000"},
    {"tag":"ipiAliquotaValorRecolher","default":"000000000000000"},
    {"tag":"ipiRegimeTributacaoCodigo","default":"4"},
    {"tag":"ipiRegimeTributacaoNome","default":"SEM BENEFICIO"},
    {"tag":"mercadoria","type":"complex","children":[
        {"tag":"descricaoMercadoria","default":""},
        {"tag":"numeroSequencialItem","default":"01"},
        {"tag":"quantidade","default":"00000000000000"},
        {"tag":"unidadeMedida","default":"UNIDADE"},
        {"tag":"valorUnitario","default":"00000000000000000000"},
    ]},
    {"tag":"numeroAdicao","default":"001"},
    {"tag":"numeroDUIMP","default":""},
    {"tag":"numeroLI","default":"0000000000"},
    {"tag":"paisAquisicaoMercadoriaCodigo","default":"000"},
    {"tag":"paisAquisicaoMercadoriaNome","default":""},
    {"tag":"paisOrigemMercadoriaCodigo","default":"000"},
    {"tag":"paisOrigemMercadoriaNome","default":""},
    {"tag":"pisCofinsBaseCalculoAliquotaICMS","default":"00000"},
    {"tag":"pisCofinsBaseCalculoFundamentoLegalCodigo","default":"00"},
    {"tag":"pisCofinsBaseCalculoPercentualReducao","default":"00000"},
    {"tag":"pisCofinsBaseCalculoValor","default":"000000000000000"},
    {"tag":"pisCofinsFundamentoLegalReducaoCodigo","default":"00"},
    {"tag":"pisCofinsRegimeTributacaoCodigo","default":"1"},
    {"tag":"pisCofinsRegimeTributacaoNome","default":"RECOLHIMENTO INTEGRAL"},
    {"tag":"pisPasepAliquotaAdValorem","default":"00000"},
    {"tag":"pisPasepAliquotaEspecificaQuantidadeUnidade","default":"000000000"},
    {"tag":"pisPasepAliquotaEspecificaValor","default":"0000000000"},
    {"tag":"pisPasepAliquotaReduzida","default":"00000"},
    {"tag":"pisPasepAliquotaValorDevido","default":"000000000000000"},
    {"tag":"pisPasepAliquotaValorRecolher","default":"000000000000000"},
    {"tag":"icmsBaseCalculoValor","default":"000000000000000"},
    {"tag":"icmsBaseCalculoAliquota","default":"00000"},
    {"tag":"icmsBaseCalculoValorImposto","default":"00000000000000"},
    {"tag":"icmsBaseCalculoValorDiferido","default":"00000000000000"},
    {"tag":"cbsIbsCst","default":"000"},
    {"tag":"cbsIbsClasstrib","default":"000001"},
    {"tag":"cbsBaseCalculoValor","default":"000000000000000"},
    {"tag":"cbsBaseCalculoAliquota","default":"00000"},
    {"tag":"cbsBaseCalculoAliquotaReducao","default":"00000"},
    {"tag":"cbsBaseCalculoValorImposto","default":"00000000000000"},
    {"tag":"ibsBaseCalculoValor","default":"000000000000000"},
    {"tag":"ibsBaseCalculoAliquota","default":"00000"},
    {"tag":"ibsBaseCalculoAliquotaReducao","default":"00000"},
    {"tag":"ibsBaseCalculoValorImposto","default":"00000000000000"},
    {"tag":"relacaoCompradorVendedor","default":"Fabricante é desconhecido"},
    {"tag":"seguroMoedaNegociadaCodigo","default":"220"},
    {"tag":"seguroMoedaNegociadaNome","default":"DOLAR DOS EUA"},
    {"tag":"seguroValorMoedaNegociada","default":"000000000000000"},
    {"tag":"seguroValorReais","default":"000000000000000"},
    {"tag":"sequencialRetificacao","default":"00"},
    {"tag":"valorMultaARecolher","default":"000000000000000"},
    {"tag":"valorMultaARecolherAjustado","default":"000000000000000"},
    {"tag":"valorReaisFreteInternacional","default":"000000000000000"},
    {"tag":"valorReaisSeguroInternacional","default":"000000000000000"},
    {"tag":"valorTotalCondicaoVenda","default":"00000000000"},
    {"tag":"vinculoCompradorVendedor","default":"Não há vinculação entre comprador e vendedor."},
]

FOOTER_TAGS = {
    "armazem":{"tag":"nomeArmazem","default":"TCP"},
    "armazenamentoRecintoAduaneiroCodigo":"9801303",
    "armazenamentoRecintoAduaneiroNome":"TCP - TERMINAL",
    "armazenamentoSetor":"002",
    "canalSelecaoParametrizada":"001",
    "caracterizacaoOperacaoCodigoTipo":"1",
    "caracterizacaoOperacaoDescricaoTipo":"Importação Própria",
    "cargaDataChegada":"20251120",
    "cargaNumeroAgente":"N/I",
    "cargaPaisProcedenciaCodigo":"386",
    "cargaPaisProcedenciaNome":"",
    "cargaPesoBruto":"000000000000000",
    "cargaPesoLiquido":"000000000000000",
    "cargaUrfEntradaCodigo":"0917800",
    "cargaUrfEntradaNome":"PORTO DE PARANAGUA",
    "conhecimentoCargaEmbarqueData":"20251025",
    "conhecimentoCargaEmbarqueLocal":"EXTERIOR",
    "conhecimentoCargaId":"CE123456",
    "conhecimentoCargaIdMaster":"CE123456",
    "conhecimentoCargaTipoCodigo":"12",
    "conhecimentoCargaTipoNome":"HBL - House Bill of Lading",
    "conhecimentoCargaUtilizacao":"1",
    "conhecimentoCargaUtilizacaoNome":"Total",
    "dataDesembaraco":"20251124",
    "dataRegistro":"20251124",
    "documentoChegadaCargaCodigoTipo":"1",
    "documentoChegadaCargaNome":"Manifesto da Carga",
    "documentoChegadaCargaNumero":"1625502058594",
    "embalagem":[{"tag":"codigoTipoEmbalagem","default":"60"},
                 {"tag":"nomeEmbalagem","default":"PALLETS"},
                 {"tag":"quantidadeVolume","default":"00001"}],
    "freteCollect":"000000000000000",
    "freteEmTerritorioNacional":"000000000000000",
    "freteMoedaNegociadaCodigo":"978",
    "freteMoedaNegociadaNome":"EURO/COM.EUROPEIA",
    "fretePrepaid":"000000000000000",
    "freteTotalDolares":"000000000000000",
    "freteTotalMoeda":"000000000000000",
    "freteTotalReais":"000000000000000",
    "icms":[{"tag":"agenciaIcms","default":"00000"},
            {"tag":"codigoTipoRecolhimentoIcms","default":"3"},
            {"tag":"nomeTipoRecolhimentoIcms","default":"Exoneração do ICMS"},
            {"tag":"numeroSequencialIcms","default":"001"},
            {"tag":"ufIcms","default":"PR"},
            {"tag":"valorTotalIcms","default":"000000000000000"}],
    "importadorCodigoTipo":"1",
    "importadorCpfRepresentanteLegal":"00000000000",
    "importadorEnderecoBairro":"CENTRO",
    "importadorEnderecoCep":"00000000",
    "importadorEnderecoComplemento":"",
    "importadorEnderecoLogradouro":"RUA PRINCIPAL",
    "importadorEnderecoMunicipio":"CIDADE",
    "importadorEnderecoNumero":"00",
    "importadorEnderecoUf":"PR",
    "importadorNome":"",
    "importadorNomeRepresentanteLegal":"REPRESENTANTE",
    "importadorNumero":"",
    "importadorNumeroTelefone":"0000000000",
    "informacaoComplementar":"Informações extraídas do Sistema Integrado DUIMP 2026.",
    "localDescargaTotalDolares":"000000000000000",
    "localDescargaTotalReais":"000000000000000",
    "localEmbarqueTotalDolares":"000000000000000",
    "localEmbarqueTotalReais":"000000000000000",
    "modalidadeDespachoCodigo":"1",
    "modalidadeDespachoNome":"Normal",
    "numeroDUIMP":"",
    "operacaoFundap":"N",
    "pagamento":[],
    "seguroMoedaNegociadaCodigo":"220",
    "seguroMoedaNegociadaNome":"DOLAR DOS EUA",
    "seguroTotalDolares":"000000000000000",
    "seguroTotalMoedaNegociada":"000000000000000",
    "seguroTotalReais":"000000000000000",
    "sequencialRetificacao":"00",
    "situacaoEntregaCarga":"ENTREGA CONDICIONADA",
    "tipoDeclaracaoCodigo":"01",
    "tipoDeclaracaoNome":"CONSUMO",
    "totalAdicoes":"000",
    "urfDespachoCodigo":"0917800",
    "urfDespachoNome":"PORTO DE PARANAGUA",
    "valorTotalMultaARecolherAjustado":"000000000000000",
    "viaTransporteCodigo":"01",
    "viaTransporteMultimodal":"N",
    "viaTransporteNome":"MARÍTIMA",
    "viaTransporteNomeTransportador":"MAERSK A/S",
    "viaTransporteNomeVeiculo":"MAERSK",
    "viaTransportePaisTransportadorCodigo":"741",
    "viaTransportePaisTransportadorNome":"CINGAPURA",
}


class DataFormatter:
    @staticmethod
    def clean_text(text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text.replace('\n',' ').replace('\r','')).strip()

    @staticmethod
    def format_number(value, length=15):
        if not value: return "0"*length
        clean = re.sub(r'\D','',str(value))
        return clean.zfill(length) if clean else "0"*length

    @staticmethod
    def format_ncm(value):
        if not value: return "00000000"
        return re.sub(r'\D','',value)[:8]

    @staticmethod
    def format_input_fiscal(value, length=15, is_percent=False):
        try:
            if isinstance(value, str): value = value.replace('.','').replace(',','.')
            return str(int(round(float(value)*100))).zfill(length)
        except: return "0"*length

    @staticmethod
    def format_high_precision(value, length=15):
        try:
            if isinstance(value, str): value = value.replace('.','').replace(',','.')
            return str(int(round(float(value)*10000000))).zfill(length)
        except: return "0"*length

    @staticmethod
    def format_quantity(value, length=14):
        try:
            if isinstance(value, str): value = value.replace('.','').replace(',','.')
            return str(int(round(float(value)*100000))).zfill(length)
        except: return "0"*length

    @staticmethod
    def calculate_cbs_ibs(base_xml_string):
        try:
            bf = int(base_xml_string)/100.0
            cbs = str(int(round(bf*0.009*100))).zfill(14)
            ibs = str(int(round(bf*0.001*100))).zfill(14)
            return cbs, ibs
        except: return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def parse_supplier_info(raw_name, raw_addr):
        data = {"fornecedorNome":"","fornecedorLogradouro":"","fornecedorNumero":"S/N","fornecedorCidade":""}
        if raw_name:
            parts = raw_name.split('-',1)
            data["fornecedorNome"] = parts[-1].strip() if len(parts)>1 else raw_name.strip()
        if raw_addr:
            ca = DataFormatter.clean_text(raw_addr)
            pd_ = ca.rsplit('-',1)
            if len(pd_)>1:
                data["fornecedorCidade"] = pd_[1].strip()
                street = pd_[0].strip()
            else:
                data["fornecedorCidade"] = "EXTERIOR"; street = ca
            cs = street.rsplit(',',1)
            if len(cs)>1:
                data["fornecedorLogradouro"] = cs[0].strip()
                m = re.search(r'\d+', cs[1])
                if m: data["fornecedorNumero"] = m.group(0)
            else:
                data["fornecedorLogradouro"] = street
        return data


class XMLBuilder:
    def __init__(self, parser, edited_items=None):
        self.p = parser
        self.items_to_use = edited_items if edited_items else self.p.items
        self.root = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self, user_inputs=None):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP","").split("/")[0].replace("-","").replace(".","")
        totals = {"frete":0.0,"seguro":0.0,"ii":0.0,"ipi":0.0,"pis":0.0,"cofins":0.0}

        def gf(val):
            try:
                if isinstance(val,str): val=val.replace('.','').replace(',','.')
                return float(val)
            except: return 0.0

        for it in self.items_to_use:
            totals["frete"] += gf(it.get("Frete (R$)"))
            totals["seguro"] += gf(it.get("Seguro (R$)"))
            totals["ii"] += gf(it.get("II (R$)"))
            totals["ipi"] += gf(it.get("IPI (R$)"))
            totals["pis"] += gf(it.get("PIS (R$)"))
            totals["cofins"] += gf(it.get("COFINS (R$)"))

        for it in self.items_to_use:
            adicao = etree.SubElement(self.duimp, "adicao")
            input_number = str(it.get("NUMBER","")).strip()
            original_desc = DataFormatter.clean_text(it.get("descricao",""))
            desc_compl = DataFormatter.clean_text(it.get("desc_complementar",""))
            final_desc = montar_descricao_final(desc_compl, input_number, original_desc)
            vtvf = DataFormatter.format_high_precision(it.get("valorTotal","0"), 11)
            vuf = DataFormatter.format_high_precision(it.get("valorUnit","0"), 20)
            qcr = it.get("quantidade_comercial") or it.get("quantidade")
            qcf = DataFormatter.format_quantity(qcr, 14)
            qef = DataFormatter.format_quantity(it.get("quantidade"), 14)
            plf = DataFormatter.format_quantity(it.get("pesoLiq"), 15)
            btrf = DataFormatter.format_input_fiscal(it.get("valorTotal","0"), 15)
            rf = gf(it.get("Frete (R$)",0))
            rs = gf(it.get("Seguro (R$)",0))
            ra = gf(it.get("Aduaneiro (R$)",0))
            ff = DataFormatter.format_input_fiscal(rf)
            sf = DataFormatter.format_input_fiscal(rs)
            af = DataFormatter.format_input_fiscal(ra)
            iibf = DataFormatter.format_input_fiscal(it.get("II Base (R$)",0))
            iiaf = DataFormatter.format_input_fiscal(it.get("II Alíq. (%)",0),5,True)
            iivf = DataFormatter.format_input_fiscal(gf(it.get("II (R$)",0)))
            ipiaf = DataFormatter.format_input_fiscal(it.get("IPI Alíq. (%)",0),5,True)
            ipivf = DataFormatter.format_input_fiscal(gf(it.get("IPI (R$)",0)))
            pisbf = DataFormatter.format_input_fiscal(it.get("PIS Base (R$)",0))
            pisaf = DataFormatter.format_input_fiscal(it.get("PIS Alíq. (%)",0),5,True)
            pisvf = DataFormatter.format_input_fiscal(gf(it.get("PIS (R$)",0)))
            cofaf = DataFormatter.format_input_fiscal(it.get("COFINS Alíq. (%)",0),5,True)
            cofvf = DataFormatter.format_input_fiscal(gf(it.get("COFINS (R$)",0)))
            icms_base = iibf if int(iibf)>0 else btrf
            cbs_imp, ibs_imp = DataFormatter.calculate_cbs_ibs(icms_base)
            sup = DataFormatter.parse_supplier_info(it.get("fornecedor_raw"), it.get("endereco_raw"))
            emap = {
                "numeroAdicao":str(it["numeroAdicao"])[-3:],
                "numeroDUIMP":duimp_fmt,
                "dadosMercadoriaCodigoNcm":DataFormatter.format_ncm(it.get("ncm")),
                "dadosMercadoriaMedidaEstatisticaQuantidade":qef,
                "dadosMercadoriaMedidaEstatisticaUnidade":it.get("unidade","").upper(),
                "dadosMercadoriaPesoLiquido":plf,
                "condicaoVendaMoedaNome":it.get("moeda","").upper(),
                "valorTotalCondicaoVenda":vtvf,
                "valorUnitario":vuf,
                "condicaoVendaValorMoeda":btrf,
                "condicaoVendaValorReais":af if int(af)>0 else btrf,
                "paisOrigemMercadoriaNome":it.get("paisOrigem","").upper(),
                "paisAquisicaoMercadoriaNome":it.get("paisOrigem","").upper(),
                "descricaoMercadoria":final_desc,
                "quantidade":qcf,
                "unidadeMedida":it.get("unidade","").upper(),
                "dadosCargaUrfEntradaCodigo":h.get("urf","0917800"),
                "fornecedorNome":sup["fornecedorNome"][:60],
                "fornecedorLogradouro":sup["fornecedorLogradouro"][:60],
                "fornecedorNumero":sup["fornecedorNumero"][:10],
                "fornecedorCidade":sup["fornecedorCidade"][:30],
                "freteValorReais":ff,"seguroValorReais":sf,
                "iiBaseCalculo":iibf,"iiAliquotaAdValorem":iiaf,
                "iiAliquotaValorCalculado":iivf,"iiAliquotaValorDevido":iivf,"iiAliquotaValorRecolher":iivf,
                "ipiAliquotaAdValorem":ipiaf,"ipiAliquotaValorDevido":ipivf,"ipiAliquotaValorRecolher":ipivf,
                "pisCofinsBaseCalculoValor":pisbf,"pisPasepAliquotaAdValorem":pisaf,
                "pisPasepAliquotaValorDevido":pisvf,"pisPasepAliquotaValorRecolher":pisvf,
                "cofinsAliquotaAdValorem":cofaf,"cofinsAliquotaValorDevido":cofvf,"cofinsAliquotaValorRecolher":cofvf,
                "icmsBaseCalculoValor":icms_base,"icmsBaseCalculoAliquota":"01800",
                "cbsIbsClasstrib":"000001","cbsBaseCalculoValor":icms_base,
                "cbsBaseCalculoAliquota":"00090","cbsBaseCalculoValorImposto":cbs_imp,
                "ibsBaseCalculoValor":icms_base,"ibsBaseCalculoAliquota":"00010","ibsBaseCalculoValorImposto":ibs_imp,
            }
            for field in ADICAO_FIELDS_ORDER:
                tag = field["tag"]
                if field.get("type") == "complex":
                    parent = etree.SubElement(adicao, tag)
                    for child in field["children"]:
                        etree.SubElement(parent, child["tag"]).text = emap.get(child["tag"], child["default"])
                else:
                    etree.SubElement(adicao, tag).text = emap.get(tag, field["default"])

        pbf = DataFormatter.format_quantity(h.get("pesoBruto"), 15)
        plf2 = DataFormatter.format_quantity(h.get("pesoLiquido"), 15)
        fmap = {
            "numeroDUIMP":duimp_fmt,
            "importadorNome":h.get("nomeImportador",""),
            "importadorNumero":DataFormatter.format_number(h.get("cnpj"),14),
            "cargaPesoBruto":pbf,"cargaPesoLiquido":plf2,
            "cargaPaisProcedenciaNome":h.get("paisProcedencia","").upper(),
            "totalAdicoes":str(len(self.items_to_use)).zfill(3),
            "freteTotalReais":DataFormatter.format_input_fiscal(totals["frete"]),
            "seguroTotalReais":DataFormatter.format_input_fiscal(totals["seguro"]),
        }
        if user_inputs:
            for k in ["cargaDataChegada","dataDesembaraco","dataRegistro","conhecimentoCargaEmbarqueData",
                      "cargaPesoBruto","cargaPesoLiquido","localDescargaTotalDolares","localDescargaTotalReais",
                      "localEmbarqueTotalDolares","localEmbarqueTotalReais"]:
                if k in user_inputs: fmap[k] = user_inputs[k]

        receitas = [
            {"code":"0086","val":totals["ii"]},{"code":"1038","val":totals["ipi"]},
            {"code":"5602","val":totals["pis"]},{"code":"5629","val":totals["cofins"]},
        ]
        if user_inputs and user_inputs.get("valorReceita7811","0") not in ("0","000000000000000"):
            receitas.append({"code":"7811","val":float(user_inputs["valorReceita7811"])})

        for tag, dval in FOOTER_TAGS.items():
            if tag == "embalagem" and user_inputs:
                parent = etree.SubElement(self.duimp, tag)
                for sf in dval:
                    v = user_inputs.get("quantidadeVolume", sf["default"]) if sf["tag"]=="quantidadeVolume" else sf["default"]
                    etree.SubElement(parent, sf["tag"]).text = v
                continue
            if tag == "pagamento":
                agencia = user_inputs.get("agenciaPagamento","3715") if user_inputs else "3715"
                banco = user_inputs.get("bancoPagamento","341") if user_inputs else "341"
                for rec in receitas:
                    if rec["val"] > 0:
                        pag = etree.SubElement(self.duimp, "pagamento")
                        etree.SubElement(pag, "agenciaPagamento").text = agencia
                        etree.SubElement(pag, "bancoPagamento").text = banco
                        etree.SubElement(pag, "codigoReceita").text = rec["code"]
                        if rec["code"]=="7811" and user_inputs:
                            etree.SubElement(pag, "valorReceita").text = user_inputs["valorReceita7811"].zfill(15)
                        else:
                            etree.SubElement(pag, "valorReceita").text = DataFormatter.format_input_fiscal(rec["val"])
                continue
            if tag in fmap:
                etree.SubElement(self.duimp, tag).text = fmap[tag]; continue
            if user_inputs and tag in user_inputs:
                etree.SubElement(self.duimp, tag).text = user_inputs[tag]; continue
            if isinstance(dval, list):
                parent = etree.SubElement(self.duimp, tag)
                for sf in dval: etree.SubElement(parent, sf["tag"]).text = sf["default"]
            elif isinstance(dval, dict):
                parent = etree.SubElement(self.duimp, tag)
                etree.SubElement(parent, dval["tag"]).text = dval["default"]
            else:
                etree.SubElement(self.duimp, tag).text = fmap.get(tag, dval)

        xml_bytes = etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
        return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_bytes


# ==============================================================================
# PARTE 7 — MERGE + SISTEMA INTEGRADO DUIMP (INALTERADO)
# ==============================================================================
def _merge_app2_items(df_dest: pd.DataFrame, itens: list) -> tuple:
    src_map = {}
    for item in itens:
        try: src_map[int(item['numero_item'])] = item
        except: pass
    count, not_found = 0, []
    for idx, row in df_dest.iterrows():
        try:
            num = int(str(row['numeroAdicao']).strip())
            if num not in src_map: not_found.append(num); continue
            src = src_map[num]
            df_dest.at[idx,'NUMBER'] = src.get('codigo_interno','')
            df_dest.at[idx,'Frete (R$)'] = src.get('frete_internacional',0.0)
            df_dest.at[idx,'Seguro (R$)'] = src.get('seguro_internacional',0.0)
            df_dest.at[idx,'Aduaneiro (R$)'] = src.get('aduaneiro_reais',src.get('valorAduaneiroReal',src.get('local_aduaneiro',0.0)))
            df_dest.at[idx,'II (R$)'] = src.get('ii_valor_devido',0.0)
            df_dest.at[idx,'II Base (R$)'] = src.get('ii_base_calculo',src.get('aduaneiro_reais',src.get('valorAduaneiroReal',0.0)))
            df_dest.at[idx,'II Alíq. (%)'] = src.get('ii_aliquota',0.0)
            df_dest.at[idx,'IPI (R$)'] = src.get('ipi_valor_devido',0.0)
            df_dest.at[idx,'IPI Base (R$)'] = src.get('ipi_base_calculo',0.0)
            df_dest.at[idx,'IPI Alíq. (%)'] = src.get('ipi_aliquota',0.0)
            df_dest.at[idx,'PIS (R$)'] = src.get('pis_valor_devido',0.0)
            df_dest.at[idx,'PIS Base (R$)'] = src.get('pis_base_calculo',0.0)
            df_dest.at[idx,'PIS Alíq. (%)'] = src.get('pis_aliquota',0.0)
            df_dest.at[idx,'COFINS (R$)'] = src.get('cofins_valor_devido',0.0)
            df_dest.at[idx,'COFINS Base (R$)'] = src.get('cofins_base_calculo',0.0)
            df_dest.at[idx,'COFINS Alíq. (%)'] = src.get('cofins_aliquota',0.0)
            count += 1
        except: continue
    return df_dest, count, not_found


def _render_totais_grade(df: pd.DataFrame):
    def _s(col): return pd.to_numeric(df[col], errors='coerce').sum() if col in df.columns else 0
    t1,t2,t3,t4,t5,t6 = st.columns(6)
    t1.metric("II Total", f"R$ {_s('II (R$)'):,.2f}")
    t2.metric("IPI Total", f"R$ {_s('IPI (R$)'):,.2f}")
    t3.metric("PIS Total", f"R$ {_s('PIS (R$)'):,.2f}")
    t4.metric("COFINS Total", f"R$ {_s('COFINS (R$)'):,.2f}")
    t5.metric("Frete Total", f"R$ {_s('Frete (R$)'):,.2f}")
    t6.metric("Seguro Total", f"R$ {_s('Seguro (R$)'):,.2f}")


def sistema_integrado_duimp():
    page_header("📊", "Sistema Integrado DUIMP 2026",
                "Upload · Vinculação · Conferência · Geração de XML 8686")

    tab_up, tab_conf, tab_xml = st.tabs(["📂  Upload & Vinculação", "📋  Conferência", "💾  Exportar XML"])

    with tab_up:
        section_title("⚙️ Formato do Arquivo de Tributos (APP2)")
        col_radio, col_badge = st.columns([3, 1], gap="large")
        with col_radio:
            layout_choice = st.radio("Selecione o layout do APP2",
                options=["🔵  Sigraweb — Conferência do Processo Detalhado (layout novo)",
                         "🟠  Extrato DUIMP — Itens da DUIMP (layout antigo)"],
                index=0 if st.session_state["layout_app2"] == "sigraweb" else 1, key="layout_radio", horizontal=False)
            novo = "sigraweb" if layout_choice.startswith("🔵") else "extrato_duimp"
            if novo != st.session_state["layout_app2"]:
                st.session_state["layout_app2"] = novo
                st.session_state["parsed_sigraweb"] = None
                st.session_state["merged_df"] = None
                st.rerun()
        with col_badge:
            is_sgw = st.session_state["layout_app2"] == "sigraweb"
            bc = "lbadge" if is_sgw else "lbadge amber"
            btx = "🔵 Sigraweb (ativo)" if is_sgw else "🟠 Extrato DUIMP (ativo)"
            ph(f'<div class="{bc}">{btx}</div>')

        st.divider()
        section_title("📂 Carregar Arquivos")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            ph("""<div class="uzone"><div class="uzone-icon">📄</div><div class="uzone-title">Passo 1 — Extrato DUIMP</div><div class="uzone-sub">Siscomex · PDF</div></div>""")
            file_duimp = st.file_uploader("Arquivo DUIMP (PDF)", type="pdf", key="u1")
        with c2:
            lbl2 = "Sigraweb · Conferência Detalhada" if is_sgw else "Extrato DUIMP · Itens"
            ph(f"""<div class="uzone"><div class="uzone-icon">📑</div><div class="uzone-title">Passo 2 — {lbl2}</div><div class="uzone-sub">PDF</div></div>""")
            file_app2 = st.file_uploader("Arquivo APP2 (PDF)" if is_sgw else "Arquivo Extrato DUIMP (PDF)", type="pdf", key="u2")

        if file_duimp and (st.session_state["parsed_duimp"] is None or file_duimp.name != getattr(st.session_state.get("last_duimp"),"name","")):
            _td_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as _td:
                    _td.write(file_duimp.read()); _td_path = _td.name
                p = DuimpPDFParser(_td_path)
                p.preprocess(); p.extract_header(); p.extract_items()
                st.session_state["parsed_duimp"] = p
                st.session_state["last_duimp"] = file_duimp
                df = pd.DataFrame(p.items)
                for col in ["NUMBER","Frete (R$)","Seguro (R$)","II (R$)","II Base (R$)","II Alíq. (%)",
                            "IPI (R$)","IPI Base (R$)","IPI Alíq. (%)","PIS (R$)","PIS Base (R$)","PIS Alíq. (%)",
                            "COFINS (R$)","COFINS Base (R$)","COFINS Alíq. (%)","Aduaneiro (R$)"]:
                    df[col] = 0.00 if col != "NUMBER" else ""
                st.session_state["merged_df"] = df
                status_ok(f"DUIMP lida — {len(p.items)} adições encontradas.")
            except Exception as e:
                st.error(f"Erro ao ler DUIMP: {e}")
            finally:
                if _td_path and os.path.exists(_td_path):
                    try: os.unlink(_td_path)
                    except: pass

        if file_app2 and st.session_state["parsed_sigraweb"] is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_app2.getvalue()); tmp_path = tmp.name
            try:
                parser_a2 = SigrawebPDFParser() if is_sgw else HafelePDFParser()
                doc_a2 = parser_a2.parse_pdf(tmp_path)
                st.session_state["parsed_sigraweb"] = doc_a2
                n = len(doc_a2['itens'])
                if n > 0:
                    lname = "Sigraweb" if is_sgw else "Extrato DUIMP"
                    status_ok(f"{lname} lido — {n} itens encontrados.")
                else:
                    st.warning("Nenhum item detectado.")
            except Exception as e:
                st.error(f"Erro ao ler APP2: {e}")
            finally:
                if os.path.exists(tmp_path):
                    try: os.unlink(tmp_path)
                    except: pass

        st.divider()
        section_title("🔗 Ações")
        col_btn, col_reset = st.columns([2, 1], gap="large")
        with col_btn:
            if st.button("🔗 VINCULAR DADOS", type="primary", use_container_width=True):
                if st.session_state["merged_df"] is not None and st.session_state["parsed_sigraweb"] is not None:
                    doc_a2 = st.session_state["parsed_sigraweb"]
                    df_dest = st.session_state["merged_df"].copy()
                    df_dest, count, nf = _merge_app2_items(df_dest, doc_a2['itens'])
                    st.session_state["merged_df"] = df_dest
                    st.success(f"✅ {count} adições vinculadas.")
                    if nf: st.warning(f"⚠️ {len(nf)} não encontradas: {nf}")
                else:
                    st.warning("Carregue os dois arquivos antes de vincular.")
        with col_reset:
            if st.button("🗑️ Limpar Tudo", type="secondary", use_container_width=True):
                for k in ["parsed_duimp","parsed_sigraweb","merged_df","last_duimp"]:
                    st.session_state[k] = None
                st.rerun()

    with tab_conf:
        section_title("📋 Conferência e Edição")
        if st.session_state["merged_df"] is not None:
            edf = st.data_editor(st.session_state["merged_df"], hide_index=True, use_container_width=True, height=540)
            for tax in ['II','IPI','PIS','COFINS']:
                bc_ = f"{tax} Base (R$)"; ac_ = f"{tax} Alíq. (%)"; vc_ = f"{tax} (R$)"
                if bc_ in edf.columns and ac_ in edf.columns:
                    edf[bc_] = pd.to_numeric(edf[bc_], errors='coerce').fillna(0.0)
                    edf[ac_] = pd.to_numeric(edf[ac_], errors='coerce').fillna(0.0)
                    edf[vc_] = edf[bc_] * (edf[ac_] / 100.0)
            st.session_state["merged_df"] = edf
            section_title("📊 Totais da Grade")
            _render_totais_grade(edf)
        else:
            empty_state("📋", "Nenhum dado vinculado ainda", "Carregue os arquivos e execute a vinculação")

    with tab_xml:
        section_title("💾 Exportar XML")
        if st.session_state["merged_df"] is not None:
            if st.button("⚙️ Gerar XML (Layout 8686)", type="primary", use_container_width=True):
                try:
                    p = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    for i, item in enumerate(p.items):
                        if i < len(records): item.update(records[i])
                    builder = XMLBuilder(p)
                    xml_bytes = builder.build()
                    duimp_num = p.header.get("numeroDUIMP","0000").replace("/","-")
                    st.download_button("⬇️ Baixar XML", data=xml_bytes,
                                       file_name=f"DUIMP_{duimp_num}_INTEGRADO.xml",
                                       mime="text/xml", use_container_width=True)
                    st.success("✅ XML gerado com sucesso!")
                    with st.expander("👁️ Preview XML"):
                        st.code(xml_bytes.decode('utf-8', errors='ignore')[:3000], language='xml')
                except Exception as e:
                    st.error(f"Erro: {e}")
        else:
            empty_state("💾", "Nenhum dado disponível", "Realize o upload e vinculação antes de gerar o XML")


# ==============================================================================
# APLICAÇÃO PRINCIPAL
# ==============================================================================
def main():
    load_css()

    ph("""
    <div class="hero">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png"
             class="hero-logo" alt="Häfele">
        <h1 class="hero-title">Sistema de Processamento Unificado 2026</h1>
        <p class="hero-sub">TXT · Captura em Massa MasterSAF · DUIMP — Análise e geração de XML fiscal</p>
        <div class="hero-chips">
            <span class="chip">📄 TXT</span>
            <span class="chip">⚡ MasterSAF</span>
            <span class="chip">📊 DUIMP</span>
            <span class="chip">🔵 Sigraweb</span>
            <span class="chip">🟠 Extrato DUIMP</span>
            <span class="chip">⚙️ XML 8686</span>
        </div>
    </div>""")

    tab1, tab2, tab3 = st.tabs([
        "📄  Processador TXT",
        "⚡  Captura em Massa MasterSAF",
        "📊  Sistema Integrado DUIMP",
    ])
    with tab1: processador_txt()
    with tab2: processador_mastersaf()
    with tab3: sistema_integrado_duimp()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        st.code(traceback.format_exc())