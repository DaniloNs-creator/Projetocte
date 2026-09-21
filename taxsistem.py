# -*- coding: utf-8 -*-
"""
==================================================================================
HÄFELE TAX SYSTEM — Sistema Integrado de Processamento Fiscal
Versão: 6.0 - COMPLETA com correção do erro startswith
==================================================================================

Sistema unificado com os módulos:
  1. Processador de Arquivos TXT
  2. MasterSAF Automação — Download e processamento de CT-es
  3. Catálogo Siscomex — Conversor JSON <-> Excel
==================================================================================
"""

from __future__ import annotations

import io
import json
import re
import zipfile
import os
import tempfile
import shutil
import time
import traceback
import chardet
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import plotly.express as px
import xml.etree.ElementTree as ET

try:
    import openpyxl
except ImportError:
    pass

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    import subprocess
except ImportError:
    webdriver = None

# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================

st.set_page_config(
    page_title="HÄFELE TAX SYSTEM",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Configuração do servidor para uploads grandes
try:
    os.makedirs(".streamlit", exist_ok=True)
    config_path = os.path.join(".streamlit", "config.toml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("[server]\nmaxUploadSize = 2000\nmaxMessageSize = 2000\n")
except Exception:
    pass

# ==============================================================================
# CONSTANTES GERAIS
# ==============================================================================

APP_TITLE = "HÄFELE TAX SYSTEM"
APP_ICON = "🏛️"

# Constantes MasterSAF / CT-e
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

# ==============================================================================
# HELPERS COMPATIBILIDADE
# ==============================================================================

def _w(stretch: bool = True):
    try:
        import inspect
        sig = inspect.signature(st.dataframe)
        if "width" in sig.parameters and "use_container_width" not in sig.parameters:
            return {"width": "stretch" if stretch else "content"}
        else:
            return {"use_container_width": stretch}
    except Exception:
        return {"use_container_width": stretch}

_WS = _w(True)
_WC = _w(False)

# ==============================================================================
# SESSION STATE
# ==============================================================================

_defaults = {
    # MasterSAF
    'ms_logs': [],
    'ms_download_path': None,
    'ms_processed_data': [],
    'ms_zip_bytes': None,
}

for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================================
# HELPERS UI
# ==============================================================================

def ph(html: str):
    st.markdown(html, unsafe_allow_html=True)

def section_title(text: str):
    ph(f'<div class="stitle">{text}</div>')

def empty_state(icon: str, title: str, sub: str = ""):
    ph(f"""
    <div class="empty">
        <div class="empty-icon">{icon}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-sub">{sub}</div>
    </div>""")


def show_loading_animation(message="Processando..."):
    with st.spinner(message):
        pb = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            pb.progress(i + 1)
        pb.empty()

def show_success_animation(message="Concluído!"):
    ph_container = st.empty()
    with ph_container.container():
        st.success(f"✅ {message}")
        time.sleep(1.2)
    ph_container.empty()

def botao_voltar():
    """Botão para voltar à tela inicial"""
    if st.button("🏠 Voltar ao Início", key="btn_voltar"):
        st.query_params.clear()
        st.rerun()

# ==============================================================================
# CSS GLOBAL - DARK MODE
# ==============================================================================

def load_css():
    ph("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root{
        --bg-primary: #0A0E17;
        --bg-secondary: #141B2D;
        --bg-card: #141B2D;
        --bg-card-hover: #1A2340;
        --text-primary: #E2E8F0;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        --border-color: #1E293B;
        --border-hover: #334155;
        --blue: #3B82F6;
        --blue-dark: #1E3A8A;
        --blue-light: #60A5FA;
        --green: #10B981;
        --green-dark: #059669;
        --amber: #F59E0B;
        --red: #EF4444;
        --cor-primaria: #0B3D2E;
        --cor-secundaria: #134E36;
        --cor-grad-1: #0B3D2E;
        --cor-grad-2: #1E7A4C;
        --cor-grad-3: #C9A24B;
        --cor-destaque: #C9A24B;
        --cor-card: #141B2D;
        --cor-erro: #EF4444;
        --cor-alerta: #F59E0B;
        --cor-ok: #10B981;
        --r:10px;
        --r-lg:16px;
        --r-xl:24px;
        --r-2xl:32px;
        --sh0:0 1px 3px rgba(0,0,0,.4);
        --sh1:0 2px 8px rgba(0,0,0,.5),0 1px 3px rgba(0,0,0,.3);
        --sh2:0 8px 24px rgba(0,0,0,.6),0 2px 8px rgba(0,0,0,.4);
        --sh3:0 20px 60px rgba(0,0,0,.7),0 4px 16px rgba(0,0,0,.5);
        --tr:all .2s cubic-bezier(.4,0,.2,1);
        --sombra-suave: 0 2px 10px rgba(0,0,0,.4);
        --sombra-hover: 0 10px 24px rgba(0,0,0,.5);
        --raio: 12px;
        --transicao: all .28s cubic-bezier(.4,0,.2,1);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: var(--border-hover); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }

    @keyframes fadeInUp {
        0% { opacity: 0; transform: translateY(14px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeInLeft {
        0% { opacity: 0; transform: translateX(-14px); }
        100% { opacity: 1; transform: translateX(0); }
    }
    @keyframes gradientFlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
        70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
        100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
    }

    .hero-home {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 70vh;
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #050D1F 0%, #0A1628 40%, #0F2040 70%, #1A2D5A 100%);
        border-radius: var(--r-2xl);
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(59, 130, 246, 0.1);
    }
    .hero-home::before {
        content: '';
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(rgba(59,130,246,.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,.05) 1px, transparent 1px);
        background-size: 48px 48px;
        pointer-events: none;
    }
    .hero-home .logo {
        max-width: 280px;
        margin-bottom: 2rem;
        filter: drop-shadow(0 8px 32px rgba(0,0,0,.6));
        position: relative;
        z-index: 1;
        transition: var(--tr);
    }
    .hero-home .logo:hover { transform: scale(1.03); }
    .hero-home h1 {
        font-size: 3.5rem;
        font-weight: 900;
        color: #fff;
        margin: 0 0 .5rem;
        letter-spacing: -1px;
        position: relative;
        z-index: 1;
        text-shadow: 0 4px 20px rgba(0,0,0,.3);
    }
    .hero-home .sub {
        font-size: 1.1rem;
        color: rgba(255,255,255,.6);
        margin-bottom: 2.5rem;
        position: relative;
        z-index: 1;
        max-width: 600px;
    }
    .hero-home .sub strong { color: rgba(255,255,255,.9); }

    .home-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.5rem;
        width: 100%;
        max-width: 900px;
        position: relative;
        z-index: 1;
    }
    .home-card {
        background: rgba(255,255,255,.06);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: var(--r-lg);
        padding: 1.8rem 1.5rem;
        text-align: center;
        cursor: pointer;
        transition: var(--tr);
        color: #fff;
        text-decoration: none;
        display: block;
    }
    .home-card:hover {
        background: rgba(255,255,255,.12);
        transform: translateY(-6px);
        box-shadow: 0 12px 40px rgba(0,0,0,.4);
        border-color: rgba(59,130,246,.3);
    }
    .home-card .icon { font-size: 2.8rem; margin-bottom: .8rem; display: block; }
    .home-card .name { font-weight: 700; font-size: 1.1rem; margin-bottom: .3rem; }
    .home-card .desc { font-size: .78rem; color: rgba(255,255,255,.5); line-height: 1.4; }

    .ph-hdr {
        display: flex;
        align-items: center;
        gap: 1rem;
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--blue);
        border-radius: var(--r);
        padding: .9rem 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: var(--sh0);
        transition: var(--tr);
    }
    .ph-hdr:hover {
        box-shadow: var(--sh1);
        border-left-color: var(--blue-light);
        border-color: var(--border-hover);
    }
    .ph-icon { font-size: 2rem; flex-shrink: 0; line-height: 1; }
    .ph-title { font-size: 1.3rem; font-weight: 800; color: var(--blue-light); line-height: 1.2; }
    .ph-sub { font-size: .8rem; color: var(--text-secondary); margin-top: .15rem; }

    .stitle {
        display: flex;
        align-items: center;
        font-size: .88rem;
        font-weight: 700;
        color: var(--blue-light);
        padding: .5rem 0 .5rem .85rem;
        border-left: 3px solid var(--blue);
        margin: 1.1rem 0 .7rem;
        background: linear-gradient(90deg, rgba(59,130,246,.08), transparent 80%);
        border-radius: 0 var(--r) var(--r) 0;
        letter-spacing: .2px;
    }

    .card {
        background: var(--bg-card);
        border-radius: var(--r-lg);
        border: 1px solid var(--border-color);
        box-shadow: var(--sh1);
        padding: 1.3rem 1.5rem;
        margin-bottom: 1rem;
        transition: var(--tr);
    }
    .card:hover {
        box-shadow: var(--sh2);
        border-color: var(--border-hover);
    }
    .card-accent { border-top: 3px solid var(--blue); }

    .empty {
        text-align: center;
        padding: 3.5rem 1.5rem;
        color: var(--text-secondary);
        border: 2px dashed var(--border-color);
        border-radius: var(--r-xl);
        background: var(--bg-secondary);
    }
    .empty-icon { font-size: 3rem; margin-bottom: .6rem; opacity: .5; }
    .empty-title { font-size: 1rem; font-weight: 700; color: var(--text-muted); margin-bottom: .3rem; }
    .empty-sub { font-size: .82rem; color: var(--text-muted); }

    .ms-stat-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin: 1rem 0;
    }
    .ms-stat-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--r-lg);
        padding: 1.2rem 1.4rem;
        position: relative;
        overflow: hidden;
        transition: var(--tr);
        box-shadow: var(--sh0);
    }
    .ms-stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--blue), var(--green));
    }
    .ms-stat-card:hover {
        box-shadow: var(--sh2);
        transform: translateY(-2px);
        border-color: var(--border-hover);
    }
    .ms-stat-label {
        font-size: .68rem;
        font-weight: 700;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: .12em;
        margin-bottom: .55rem;
    }
    .ms-stat-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.6rem;
        font-weight: 600;
        color: var(--green);
        line-height: 1;
    }
    .ms-stat-sub { font-size: .72rem; color: var(--text-muted); margin-top: .35rem; }

    .ms-log-area {
        background: #080D18;
        border: 1px solid rgba(59,130,246,.15);
        border-radius: var(--r-lg);
        padding: 1.1rem 1.2rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: .75rem;
        color: #CBD5E1;
        max-height: 420px;
        overflow-y: auto;
        white-space: pre-wrap;
        line-height: 1.6;
        box-shadow: inset 0 2px 8px rgba(0,0,0,.3);
    }
    .ms-log-area .log-ts { color: #334155; }
    .ms-log-area .log-ok { color: #22D3EE; }
    .ms-log-area .log-warn { color: #F59E0B; }
    .ms-log-area .log-err { color: #F87171; }
    .ms-log-area .log-info { color: #60A5FA; }

    .flabel {
        font-size: .76rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: .6px;
        margin-bottom: .3rem;
    }
    .lbadge {
        display: inline-flex;
        align-items: center;
        gap: .35rem;
        background: var(--blue);
        color: #fff;
        border-radius: var(--r);
        padding: .3rem .85rem;
        font-size: .78rem;
        font-weight: 700;
        margin-top: .5rem;
        box-shadow: 0 4px 16px rgba(59,130,246,.3);
        letter-spacing: .2px;
    }
    .lbadge.amber { background: var(--amber); }
    .lbadge.green { background: var(--green); }

    .ipill {
        display: inline-flex;
        align-items: center;
        gap: .35rem;
        background: rgba(59,130,246,.15);
        border: 1px solid rgba(59,130,246,.2);
        color: var(--blue-light);
        border-radius: 20px;
        padding: .22rem .8rem;
        font-size: .78rem;
        font-weight: 600;
        margin-bottom: .5rem;
    }

    .uzone {
        background: rgba(59,130,246,.08);
        border: 2px dashed rgba(59,130,246,.2);
        border-radius: var(--r-lg);
        padding: 1.1rem 1rem;
        text-align: center;
        margin-bottom: .5rem;
        transition: var(--tr);
        cursor: pointer;
    }
    .uzone:hover {
        border-color: var(--blue);
        background: rgba(59,130,246,.12);
    }
    .uzone-icon { font-size: 1.7rem; line-height: 1; margin-bottom: .3rem; }
    .uzone-title { font-weight: 700; color: var(--blue-light); font-size: .9rem; margin-top: .2rem; }
    .uzone-sub { font-size: .75rem; color: var(--text-secondary); margin-top: .15rem; }

    .btn-voltar {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(59,130,246,.1);
        border: 1px solid rgba(59,130,246,.2);
        border-radius: var(--r);
        padding: 0.4rem 1rem;
        color: var(--blue-light);
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: var(--tr);
        text-decoration: none;
        margin-bottom: 1rem;
    }
    .btn-voltar:hover {
        background: rgba(59,130,246,.2);
        border-color: var(--blue);
    }

    [data-testid="metric-container"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--r-lg);
        padding: .8rem 1rem;
        box-shadow: var(--sh0);
        transition: var(--tr);
    }
    [data-testid="metric-container"]:hover {
        box-shadow: var(--sh1);
        border-color: var(--border-hover);
    }
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
    }

    .stButton > button {
        border-radius: var(--r) !important;
        font-weight: 600 !important;
        font-size: .86rem !important;
        letter-spacing: .1px;
        transition: var(--tr) !important;
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: var(--sh2) !important;
        border-color: var(--border-hover) !important;
        background: var(--bg-card-hover) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--blue), var(--blue-dark)) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 16px rgba(59,130,246,.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #3B82F6, #1E3A8A) !important;
        box-shadow: 0 6px 24px rgba(59,130,246,.4) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 3px;
        background: var(--bg-secondary);
        border-radius: var(--r-lg);
        padding: 5px;
        border: 1px solid var(--border-color);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
        font-size: .85rem;
        padding: .42rem 1rem;
        transition: var(--tr);
        color: var(--text-secondary);
        border: none;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--blue-light);
        background: rgba(59,130,246,.1);
    }
    .stTabs [aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--blue-light) !important;
        box-shadow: var(--sh1) !important;
    }

    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        border-radius: var(--r) !important;
        border: 1.5px solid var(--border-color) !important;
        font-size: .86rem !important;
        transition: var(--tr);
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: var(--blue) !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,.2) !important;
    }

    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border-radius: var(--r-lg) !important;
        border: 1px solid var(--border-color) !important;
        overflow: hidden;
        box-shadow: var(--sh1) !important;
        background: var(--bg-secondary) !important;
    }

    .stSelectbox > div > div {
        background: var(--bg-secondary) !important;
        border-color: var(--border-color) !important;
        color: var(--text-primary) !important;
    }

    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: .88rem;
        color: var(--blue-light);
        background: var(--bg-secondary);
        border-radius: 8px;
        padding: .48rem .8rem !important;
    }
    [data-testid="stExpander"] {
        border: 1px solid var(--border-color) !important;
        border-radius: var(--r) !important;
    }

    hr { border: none; border-top: 1px solid var(--border-color); margin: 1rem 0; }

    [data-testid="stFileUploader"] {
        background: var(--bg-secondary);
        border: 2px dashed var(--border-color);
        border-radius: var(--r-lg);
        padding: 1rem;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: var(--blue);
    }

    .stCheckbox label, .stRadio label {
        color: var(--text-primary) !important;
    }

    @media(max-width:1024px) {
        .ms-stat-grid { grid-template-columns: repeat(2, 1fr); }
        .hero-home h1 { font-size: 2.5rem; }
        .home-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media(max-width:768px) {
        .hero-home { min-height: auto; padding: 2.5rem 1.5rem; }
        .hero-home h1 { font-size: 1.8rem; }
        .hero-home .logo { max-width: 180px; }
        .home-grid { grid-template-columns: 1fr 1fr; gap: 1rem; }
        .home-card { padding: 1.2rem 1rem; }
        .home-card .icon { font-size: 2rem; }
        .ms-stat-grid { grid-template-columns: 1fr 1fr; }
    }
    @media(max-width:480px) {
        .hero-home h1 { font-size: 1.4rem; }
        .home-grid { grid-template-columns: 1fr; }
        .hero-home .sub { font-size: .9rem; }
        .ms-stat-grid { grid-template-columns: 1fr; }
        .ph-hdr { flex-wrap: wrap; }
    }
    </style>""")


# ==============================================================================
# FUNÇÃO PARA PÁGINA INICIAL (HOME)
# ==============================================================================

def pagina_home():
    """Página inicial com logo Häfele e botões para cada módulo"""

    ph("""
    <div class="hero-home">
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png"
             class="logo" alt="Häfele Brasil">
        <h1>HÄFELE TAX SYSTEM</h1>
        <p class="sub">
            <strong>Sistema Integrado de Processamento Fiscal</strong><br>
            TXT · MasterSAF · Siscomex — Tudo em um só lugar
        </p>
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
                <div class="desc">Conversor JSON ⇄ Excel do Catálogo de Itens</div>
            </a>
        </div>
    </div>
    """)


# ==============================================================================
# MÓDULO 2: PROCESSADOR TXT
# ==============================================================================

def modulo_processador_txt():
    botao_voltar()
    
    ph("""
    <div class="ph-hdr">
        <span class="ph-icon">📄</span>
        <div>
            <div class="ph-title">Processador de Arquivos TXT</div>
            <div class="ph-sub">Remova linhas indesejadas e substitua padrões em arquivos TXT</div>
        </div>
    </div>
    """)

    def detectar_encoding(conteudo):
        return chardet.detect(conteudo)['encoding']

    def processar_arquivo(conteudo, padroes):
        try:
            substituicoes = {
                "IMPOSTO IMPORTACAO": "IMP IMPORT",
                "TAXA SICOMEX": "TX SISCOMEX",
                "FRETE INTERNACIONAL": "FRET INTER",
                "SEGURO INTERNACIONAL": "SEG INTER",
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
        st.markdown("#### 📁 Selecione o arquivo TXT")
        arquivo = st.file_uploader("Selecione o arquivo TXT", type=['txt'])

    with col_cfg:
        with st.expander("⚙️ Padrões adicionais de remoção"):
            padroes_add = st.text_input("Padrões (vírgula)", placeholder="Ex: TOTAL, SOMA")
            padroes = padroes_default + [
                p.strip() for p in padroes_add.split(",") if p.strip()
            ] if padroes_add else padroes_default
        st.markdown(f'<div class="ipill">🔍 {len(padroes)} padrões ativos</div>', unsafe_allow_html=True)

    if arquivo is not None:
        if st.button("🔄 Processar Arquivo TXT", type="primary", **_WS):
            try:
                show_loading_animation("Analisando arquivo...")
                conteudo = arquivo.read()
                resultado, total = processar_arquivo(conteudo, padroes)
                if resultado is not None:
                    show_success_animation("Processamento concluído!")
                    mantidas = len(resultado.splitlines())
                    removidas = total - mantidas
                    k1, k2, k3 = st.columns(3)
                    k1.metric("📋 Originais", total)
                    k2.metric("✅ Mantidas", mantidas)
                    k3.metric("🗑️ Removidas", removidas, delta=f"-{removidas}", delta_color="inverse")
                    
                    st.markdown("#### 👁️ Prévia")
                    st.text_area("Conteúdo processado", resultado, height=260)
                    buf = io.BytesIO()
                    buf.write(resultado.encode('utf-8'))
                    buf.seek(0)
                    st.download_button(
                        "⬇️ Baixar arquivo processado", data=buf,
                        file_name=f"processado_{arquivo.name}",
                        mime="text/plain", **_WS,
                    )
            except Exception as e:
                st.error(f"Erro: {str(e)}")
    else:
        empty_state("📂", "Nenhum arquivo carregado", "Selecione um arquivo .TXT acima para começar")


# ==============================================================================
# MÓDULO 3: MasterSAF AUTOMAÇÃO (COMPLETO)
# ==============================================================================

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
            for infQ in root.findall('.//infQ'):
                tpMed = infQ.find('tpMed')
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


def add_ms_log(msg, level='info'):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.ms_logs.append({'ts': ts, 'msg': msg, 'level': level})


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
            <div class="ph-sub">Download e processamento em massa de CT-es direto do portal</div>
        </div>
    </div>
    """)

    tab_exec, tab_resultados, tab_export = st.tabs([
        "🚀 Executar Automação",
        "📊 Resultados & Análise",
        "📥 Exportar Dados",
    ])

    with tab_exec:
        section_title("⚙️ Configuração da Automação")
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            with st.container():
                st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
                st.markdown("#### 🔑 Credenciais de Acesso")
                usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="ms_usuario")
                senha = st.text_input("Senha", type="password", placeholder="••••••••", key="ms_senha")
                st.markdown('</div>', unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("#### 📅 Período de Busca")
                p1, p2 = st.columns(2)
                with p1:
                    data_ini = st.text_input("Data Inicial", value="08/05/2026", key="ms_dt_ini")
                with p2:
                    data_fin = st.text_input("Data Final", value="08/05/2026", key="ms_dt_fin")
                st.markdown('</div>', unsafe_allow_html=True)

        with col_b:
            with st.container():
                st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
                st.markdown("#### ⚙️ Parâmetros de Execução")
                qtd_loops = st.number_input(
                    "Quantidade de Páginas (Loops)",
                    min_value=1, max_value=1000, value=5,
                    help="Cada loop processa uma página de até 200 CT-es.",
                    key="ms_qtd_loops",
                )
                gerar_excel = st.checkbox("Gerar Excel consolidado dos CT-es", value=True, key="ms_gerar_excel")
                gerar_zip = st.checkbox("Disponibilizar ZIP com XMLs brutos", value=True, key="ms_gerar_zip")
                st.markdown('</div>', unsafe_allow_html=True)

            with st.container():
                st.markdown("""
                <div class="card">
                    <div class="flabel">🚀 Executar</div>
                    <p style="font-size:0.82rem;color:var(--text-secondary);margin-bottom:1rem;line-height:1.6;">
                        O navegador será executado em <strong style="color:var(--blue-light)">modo headless</strong>.
                        Acompanhe o progresso em tempo real abaixo.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                iniciar = st.button("⚡ Iniciar Automação", key="ms_btn_iniciar",
                                    type="primary", **_WS)

        if iniciar:
            if not usuario or not senha:
                st.error("⚠️ Preencha o usuário e a senha para continuar.")
            else:
                st.session_state.ms_logs = []
                st.session_state.ms_processed_data = []

                dl_path = tempfile.mkdtemp(prefix="mastersaf_web_")
                st.session_state.ms_download_path = dl_path

                st.divider()
                section_title("📋 Log de Execução")
                status_box = st.info("⏳ Inicializando ambiente e navegador...")
                progress_bar = st.progress(0)

                driver = None
                processor = CTeProcessor()

                try:
                    chrome_version = get_chrome_version()
                    if chrome_version:
                        add_ms_log(f"📊 Versão do navegador: {chrome_version}", 'info')

                    add_ms_log("🌐 Iniciando Chrome em modo headless...", 'info')
                    driver = get_driver(dl_path)

                    status_box.info("🔑 Autenticando no MasterSAF...")
                    add_ms_log("🔗 Acessando https://prod01.dfe.thomsonreuters.com/portal/mvc/login", 'info')
                    driver.get("https://prod01.dfe.thomsonreuters.com/portal/mvc/login")
                    time.sleep(3)

                    driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
                    driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="enter"]'))
                    time.sleep(5)
                    add_ms_log("✅ Login realizado com sucesso", 'ok')
                    progress_bar.progress(0.05)

                    status_box.info("📋 Navegando até Listagem de CT-es...")
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
                    time.sleep(5)
                    add_ms_log("📋 Módulo Listagem Receptor CT-es acessado", 'info')
                    progress_bar.progress(0.08)

                    add_ms_log(f"📅 Definindo período: {data_ini} → {data_fin}", 'info')
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

                    status_box.info("🔄 Atualizando listagem...")
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
                    time.sleep(5)
                    progress_bar.progress(0.12)

                    add_ms_log("⚙️ Configurando 200 itens por página...", 'info')
                    sel = driver.find_element(
                        By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
                    sel.click()
                    time.sleep(1)
                    sel.find_element(By.XPATH, './/option[@value="200"]').click()
                    time.sleep(3)
                    progress_bar.progress(0.15)

                    add_ms_log(f"📥 Loop de download iniciado — {int(qtd_loops)} página(s)", 'info')

                    for i in range(int(qtd_loops)):
                        add_ms_log(f"━━ Página {i + 1} / {int(qtd_loops)}", 'info')

                        try:
                            cb = driver.find_element(
                                By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                            if not cb.is_selected():
                                cb.click()
                            time.sleep(2)
                        except Exception:
                            add_ms_log("   ⚠ Não foi possível marcar checkboxes", 'warn')

                        try:
                            driver.execute_script("arguments[0].click();",
                                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                            time.sleep(2)
                            driver.execute_script("arguments[0].click();",
                                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                        except Exception:
                            add_ms_log("   ⚠ Botão de download em massa não encontrado", 'warn')

                        add_ms_log("   ⏳ Aguardando download finalizar...", 'info')
                        esperar_downloads(dl_path, timeout=120)
                        time.sleep(2)

                        try:
                            cb = driver.find_element(
                                By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                            if cb.is_selected():
                                cb.click()
                            time.sleep(1)
                        except Exception:
                            pass

                        if i < int(qtd_loops) - 1:
                            try:
                                driver.find_element(
                                    By.XPATH, '//*[@id="next_plistagem"]/span').click()
                                time.sleep(5)
                            except Exception:
                                add_ms_log("   ⚠ Fim das páginas disponíveis", 'warn')
                                break

                        pct = 0.15 + ((i + 1) / int(qtd_loops)) * 0.60
                        progress_bar.progress(pct)
                        status_box.info(
                            f"⏳ Baixando XMLs — {i + 1} de {int(qtd_loops)} páginas concluídas...")

                    add_ms_log("✅ Todos os downloads concluídos", 'ok')
                    driver.quit()
                    driver = None
                    progress_bar.progress(0.78)

                    zip_found = list(Path(dl_path).glob('*.zip'))
                    add_ms_log(f"🔍 {len(zip_found)} arquivo(s) ZIP localizado(s)", 'info')

                    if gerar_excel and zip_found:
                        status_box.info("📊 Processando XMLs e montando Excel...")
                        processor.process_directory(dl_path, add_ms_log)
                        add_ms_log(f"📊 CT-es identificados: {len(processor.processed_data)}", 'ok')
                    progress_bar.progress(0.92)

                    st.session_state.ms_processed_data = processor.processed_data.copy()

                    if gerar_zip:
                        add_ms_log("📦 Empacotando XMLs brutos...", 'info')
                        buf_io = io.BytesIO()
                        with zipfile.ZipFile(buf_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root_dir, _, files in os.walk(dl_path):
                                for file in files:
                                    zipf.write(os.path.join(root_dir, file), file)
                        buf_io.seek(0)
                        st.session_state.ms_zip_bytes = buf_io.getvalue()

                    progress_bar.progress(1.0)
                    status_box.success("✅ Automação concluída com sucesso!")
                    add_ms_log("🏁 Pipeline completo.", 'ok')

                    shutil.rmtree(dl_path, ignore_errors=True)

                    if processor.processed_data:
                        summ = processor.summary()
                        st.markdown("---")
                        section_title("📊 Resumo da Extração")
                        ph(f"""
                        <div class="ms-stat-grid">
                            <div class="ms-stat-card">
                                <div class="ms-stat-label">CT-es Processados</div>
                                <div class="ms-stat-value">{summ['total']:,}</div>
                                <div class="ms-stat-sub">documentos fiscais</div>
                            </div>
                            <div class="ms-stat-card">
                                <div class="ms-stat-label">Peso Bruto Total</div>
                                <div class="ms-stat-value">{summ['peso_total']:,.0f}</div>
                                <div class="ms-stat-sub">quilogramas</div>
                            </div>
                            <div class="ms-stat-card">
                                <div class="ms-stat-label">Valor Total</div>
                                <div class="ms-stat-value">R$ {summ['valor_total']:,.2f}</div>
                                <div class="ms-stat-sub">prestação de serviço</div>
                            </div>
                            <div class="ms-stat-card">
                                <div class="ms-stat-label">Emitentes Únicos</div>
                                <div class="ms-stat-value">{summ['emitentes']}</div>
                                <div class="ms-stat-sub">transportadoras</div>
                            </div>
                        </div>
                        """)

                except Exception as e:
                    st.error(f"❌ Erro técnico: {str(e)[:300]}")
                    add_ms_log(f"❌ EXCEÇÃO: {str(e)[:300]}", 'err')
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

            section_title("🔎 Filtros")
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                uf_f = st.multiselect("UF Início", options=df['UF Inicio'].unique(), key="ms_uf_ini")
            with fc2:
                uf_d = st.multiselect("UF Destino", options=df['UF Destino'].unique(), key="ms_uf_dest")
            with fc3:
                emit_f = st.multiselect("Emitente", options=df['Emitente'].unique(), key="ms_emit")

            pmin = float(df['Peso Bruto (kg)'].min())
            pmax = float(df['Peso Bruto (kg)'].max())
            pf = st.slider("Faixa de Peso (kg)", pmin, pmax, (pmin, pmax),
                          format="%.1f kg", key="ms_peso_range") if pmin < pmax else (pmin, pmax)

            fdf = df.copy()
            if uf_f: fdf = fdf[fdf['UF Inicio'].isin(uf_f)]
            if uf_d: fdf = fdf[fdf['UF Destino'].isin(uf_d)]
            if emit_f: fdf = fdf[fdf['Emitente'].isin(emit_f)]
            fdf = fdf[(fdf['Peso Bruto (kg)'] >= pf[0]) & (fdf['Peso Bruto (kg)'] <= pf[1])]

            section_title("📊 Métricas")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Valor Total", f"R$ {fdf['Valor Prestacao'].sum():,.2f}")
            m2.metric("⚖️ Peso Total", f"{fdf['Peso Bruto (kg)'].sum():,.2f} kg")
            m3.metric("📈 Peso Médio", f"{fdf['Peso Bruto (kg)'].mean():,.2f} kg")
            m4.metric("📋 CT-es", len(fdf))

            section_title("📋 Dados")
            cols = ['Arquivo','nCT','Data Emissao','Emitente','Remetente',
                    'Destinatario','UF Inicio','UF Destino','Peso Bruto (kg)',
                    'Valor Prestacao']
            st.dataframe(fdf[cols], **_WS, height=300)

            with st.expander("📋 Todos os campos"):
                st.dataframe(fdf, **_WS)

            section_title("📈 Análise Visual")
            g1, g2 = st.columns(2)
            with g1:
                if not fdf.empty:
                    fig = px.histogram(fdf, x='Peso Bruto (kg)', nbins=30,
                                       title="Distribuição de Peso Bruto",
                                       color_discrete_sequence=['#3B82F6'])
                    fig.update_layout(margin=dict(t=38,b=8,l=8,r=8),
                                      paper_bgcolor='rgba(0,0,0,0)',
                                      plot_bgcolor='rgba(0,0,0,0)',
                                      font=dict(color='#E2E8F0'))
                    st.plotly_chart(fig, **_WS)
            with g2:
                if not fdf.empty:
                    fig2 = px.scatter(fdf, x='Peso Bruto (kg)', y='Valor Prestacao',
                                      color='UF Destino',
                                      title="Peso vs Valor Prestação",
                                      color_discrete_sequence=px.colors.qualitative.Set2)
                    fig2.update_layout(margin=dict(t=38,b=8,l=8,r=8),
                                       legend=dict(orientation="h", y=-0.22),
                                       paper_bgcolor='rgba(0,0,0,0)',
                                       plot_bgcolor='rgba(0,0,0,0)',
                                       font=dict(color='#E2E8F0'))
                    st.plotly_chart(fig2, **_WS)
        else:
            empty_state("📊", "Nenhum CT-e processado ainda",
                        "Execute a automação na aba 'Executar Automação' para ver os resultados")

    with tab_export:
        if st.session_state.ms_processed_data:
            df = pd.DataFrame(st.session_state.ms_processed_data)

            section_title("💾 Exportar Dados")
            cf, cc = st.columns([1, 2], gap="large")
            with cf:
                st.metric("📋 Registros", len(df))
                fmt = st.radio("Formato", ["📊 Excel (.xlsx)", "📄 CSV (.csv)"], key="ms_exp_fmt")
            with cc:
                cols = st.multiselect("Colunas", options=df.columns.tolist(),
                                      default=df.columns.tolist(), key="ms_exp_cols")
            df_exp = df[cols] if cols else df
            st.divider()
            if "Excel" in fmt:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as w:
                    df_exp.to_excel(w, sheet_name='Dados_CTe', index=False)
                out.seek(0)
                st.download_button(
                    "📥 Baixar Excel", data=out,
                    file_name="dados_cte_mastersaf.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    **_WS,
                )
            else:
                csv = df_exp.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Baixar CSV", data=csv,
                    file_name="dados_cte_mastersaf.csv", mime="text/csv",
                    **_WS,
                )

            if st.session_state.get('ms_zip_bytes'):
                st.divider()
                st.download_button(
                    "📥 Download ZIP — XMLs brutos",
                    data=st.session_state.ms_zip_bytes,
                    file_name="XMLs_MasterSaf.zip",
                    mime="application/zip",
                    **_WS,
                )

            with st.expander("👁️ Prévia"):
                st.dataframe(df_exp.head(10), **_WS)
        else:
            empty_state("📥", "Nenhum dado disponível",
                        "Execute a automação na aba 'Executar Automação' primeiro")


# ==============================================================================
# MÓDULO SISCOMEX: CATÁLOGO DE ITENS — CONVERSOR JSON/EXCEL
# ==============================================================================

# Colunas "simples" (escalares) do item do catálogo, na ordem oficial.
COLUNAS_SIMPLES = [
    "seq",
    "codigo",
    "descricao",
    "denominacao",
    "cpfCnpjRaiz",
    "situacao",
    "modalidade",
    "ncm",
    "versao",
    "inicioVigencia",
    "dataReferencia",
]

# Campos que são listas no JSON do Siscomex. codigosInterno é lista de
# strings simples (vira coluna ";"-separada); os "atributos*" são listas
# de objetos/estruturas mais ricas (viram colunas JSON cru, para não
# perder informação e permitir round-trip exato).
COLUNA_LISTA_SIMPLES = "codigosInterno"
COLUNAS_LISTA_JSON = [
    "atributos",
    "atributosMultivalorados",
    "atributosCompostos",
    "atributosCompostosMultivalorados",
]

TODAS_COLUNAS = COLUNAS_SIMPLES + [COLUNA_LISTA_SIMPLES] + COLUNAS_LISTA_JSON

# Campos escalares que o próprio Siscomex às vezes OMITE do item (chave
# ausente, não string vazia) — ex.: itens antigos do catálogo real não
# têm "descricao", só "denominacao". Para esses campos, se a célula
# voltar vazia do Excel, a chave é omitida do JSON reconstruído em vez
# de virar "", preservando o formato original. Ajuste esta lista se
# notar outros campos com o mesmo comportamento no seu catálogo.
CAMPOS_OMITIVEIS_SE_VAZIOS = {"descricao", "dataReferencia"}

SEPARADOR_CODIGOS = ";"


# ---------------------------------------------------------------------------
# Núcleo de conversão (independente do Streamlit, testável isoladamente)
# ---------------------------------------------------------------------------

@dataclass
class ResultadoConversao:
    dataframe: pd.DataFrame | None = None
    total_itens: int = 0
    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)


def _valor_ou_vazio(item: dict, chave: str) -> Any:
    return item.get(chave, "")


def json_para_dataframe(itens: list[dict], progress_cb=None) -> ResultadoConversao:
    """Achata a lista de itens do catálogo Siscomex em um DataFrame.

    Campos escalares viram colunas normais. `codigosInterno` vira uma
    string separada por ';'. Os quatro campos de atributos viram colunas
    contendo o JSON bruto daquele campo (string), preservando 100% da
    estrutura original para permitir reconstrução exata no sentido
    inverso (Excel -> JSON).
    """
    resultado = ResultadoConversao()
    linhas = []
    total = len(itens)

    for i, item in enumerate(itens):
        if not isinstance(item, dict):
            resultado.avisos.append(f"Item na posição {i} ignorado: não é um objeto JSON válido.")
            continue

        linha = {c: _valor_ou_vazio(item, c) for c in COLUNAS_SIMPLES}

        codigos = item.get(COLUNA_LISTA_SIMPLES, [])
        if isinstance(codigos, list):
            linha[COLUNA_LISTA_SIMPLES] = SEPARADOR_CODIGOS.join(str(c) for c in codigos)
        else:
            linha[COLUNA_LISTA_SIMPLES] = str(codigos) if codigos else ""

        for campo in COLUNAS_LISTA_JSON:
            valor = item.get(campo, [])
            # Só grava JSON se houver conteúdo; lista vazia fica em branco
            # (mais legível na planilha, tratado como [] na volta).
            linha[campo] = json.dumps(valor, ensure_ascii=False) if valor else ""

        linhas.append(linha)

        if progress_cb and total:
            progress_cb((i + 1) / total)

    resultado.dataframe = pd.DataFrame(linhas, columns=TODAS_COLUNAS)
    resultado.total_itens = len(linhas)
    return resultado


def dataframe_para_json(df: pd.DataFrame, progress_cb=None) -> tuple[list[dict], list[str], list[str]]:
    """Reconstrói a lista de itens no formato do catálogo Siscomex a
    partir do DataFrame (tipicamente vindo de um Excel editado)."""
    avisos: list[str] = []
    erros: list[str] = []
    itens: list[dict] = []
    total = len(df)

    colunas_presentes = [c for c in TODAS_COLUNAS if c in df.columns]
    faltando = [c for c in TODAS_COLUNAS if c not in df.columns]
    if faltando:
        avisos.append(
            "Colunas ausentes na planilha (serão omitidas/consideradas vazias): "
            + ", ".join(faltando)
        )

    for i, row in enumerate(df.itertuples(index=False), start=0):
        row_dict = dict(zip(df.columns, row))
        item: dict[str, Any] = {}

        for campo in COLUNAS_SIMPLES:
            valor = row_dict.get(campo, "")
            if pd.isna(valor):
                valor = "" if campo != "seq" else None
            if campo in ("seq",):
                # seq e codigo devem ser inteiros quando possível
                try:
                    valor = int(valor) if valor not in ("", None) else None
                except (ValueError, TypeError):
                    erros.append(f"Linha {i + 2}: valor inválido em 'seq' -> {valor!r}")
            if campo == "codigo":
                try:
                    valor = int(valor) if valor not in ("", None) else valor
                except (ValueError, TypeError):
                    pass  # mantém como veio; alguns catálogos usam código alfanumérico
            if campo in CAMPOS_OMITIVEIS_SE_VAZIOS and valor in ("", None):
                continue  # omite a chave, em vez de gravar "" (fiel ao catálogo original)
            item[campo] = valor

        codigos_raw = row_dict.get(COLUNA_LISTA_SIMPLES, "")
        if pd.isna(codigos_raw) or codigos_raw == "":
            item[COLUNA_LISTA_SIMPLES] = []
        else:
            item[COLUNA_LISTA_SIMPLES] = [
                c.strip() for c in str(codigos_raw).split(SEPARADOR_CODIGOS) if c.strip()
            ]

        for campo in COLUNAS_LISTA_JSON:
            bruto = row_dict.get(campo, "")
            if pd.isna(bruto) or bruto == "":
                item[campo] = []
            else:
                try:
                    item[campo] = json.loads(bruto)
                except (json.JSONDecodeError, TypeError) as e:
                    erros.append(f"Linha {i + 2}: JSON inválido na coluna '{campo}' -> {e}")
                    item[campo] = []

        itens.append(item)

        if progress_cb and total:
            progress_cb((i + 1) / total)

    return itens, avisos, erros


# ---------------------------------------------------------------------------
# Validação e preparação de lotes para a API de envio/retificação do
# Siscomex (schema de escrita — diferente do schema de leitura acima).
# Regras conforme documentação oficial do endpoint de importação de
# produtos do Catálogo de Produtos.
# ---------------------------------------------------------------------------

MAX_ITENS_POR_LOTE = 100  # "A lista enviada deve conter, no máximo, 100 elementos."

SITUACOES_VALIDAS = {"ATIVADO", "DESATIVADO", "RASCUNHO"}
MODALIDADES_VALIDAS = {"IMPORTACAO", "EXPORTACAO"}

LIMITES_TAMANHO = {
    "seq": 3,            # dígitos, valor até 999
    "codigo": 10,         # dígitos
    "descricao": 3700,    # caracteres
    "denominacao_min": 1,
    "denominacao_max": 120,
    "versao": 8,
    "atributo_codigo": 25,
    "atributo_valor": 100,
    "codigo_interno": 60,
    "atributos_compostos_max": 5,
}

_RE_SOMENTE_DIGITOS = re.compile(r"^\d+$")


@dataclass
class ItemEnvio:
    numero_linha: int
    seq_original: Any
    item_pronto: dict | None
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _valida_atributos_simples(lista: list, numero_linha: int, campo: str) -> list[str]:
    erros = []
    for j, entrada in enumerate(lista):
        if not isinstance(entrada, dict) or "atributo" not in entrada or "valor" not in entrada:
            erros.append(f"Linha {numero_linha}: '{campo}[{j}]' deve ter 'atributo' e 'valor'.")
            continue
        if not (1 <= len(str(entrada["atributo"])) <= LIMITES_TAMANHO["atributo_codigo"]):
            erros.append(f"Linha {numero_linha}: '{campo}[{j}].atributo' fora do tamanho 1-25.")
        if not (1 <= len(str(entrada["valor"])) <= LIMITES_TAMANHO["atributo_valor"]):
            erros.append(f"Linha {numero_linha}: '{campo}[{j}].valor' fora do tamanho 1-100.")
    return erros


def _valida_atributos_multivalorados(lista: list, numero_linha: int) -> list[str]:
    erros = []
    for j, entrada in enumerate(lista):
        if not isinstance(entrada, dict) or "atributo" not in entrada or "valores" not in entrada:
            erros.append(f"Linha {numero_linha}: 'atributosMultivalorados[{j}]' deve ter 'atributo' e 'valores'.")
            continue
        if not (1 <= len(str(entrada["atributo"])) <= LIMITES_TAMANHO["atributo_codigo"]):
            erros.append(f"Linha {numero_linha}: 'atributosMultivalorados[{j}].atributo' fora do tamanho 1-25.")
        if not isinstance(entrada["valores"], list) or not entrada["valores"]:
            erros.append(f"Linha {numero_linha}: 'atributosMultivalorados[{j}].valores' deve ser uma lista não-vazia.")
    return erros


def _valida_atributos_compostos(lista: list, numero_linha: int, campo: str, dupla_lista: bool) -> list[str]:
    erros = []
    max_n = LIMITES_TAMANHO["atributos_compostos_max"]
    for j, entrada in enumerate(lista):
        if not isinstance(entrada, dict) or "atributo" not in entrada or "valores" not in entrada:
            erros.append(f"Linha {numero_linha}: '{campo}[{j}]' deve ter 'atributo' e 'valores'.")
            continue
        if not (1 <= len(str(entrada["atributo"])) <= LIMITES_TAMANHO["atributo_codigo"]):
            erros.append(f"Linha {numero_linha}: '{campo}[{j}].atributo' fora do tamanho 1-25.")
        valores = entrada["valores"]
        if not isinstance(valores, list) or len(valores) > max_n:
            erros.append(f"Linha {numero_linha}: '{campo}[{j}].valores' deve ser lista com no máximo {max_n} elementos.")
            continue
        grupos = valores if dupla_lista else [valores]
        for grupo in grupos:
            alvo = grupo if dupla_lista else valores
            if dupla_lista and (not isinstance(grupo, list) or len(grupo) > max_n):
                erros.append(f"Linha {numero_linha}: '{campo}[{j}].valores' contém subgrupo inválido (máx {max_n}).")
                continue
            for sub in alvo:
                if not isinstance(sub, dict) or "atributo" not in sub or "valor" not in sub:
                    erros.append(f"Linha {numero_linha}: '{campo}[{j}]' tem par atributo/valor malformado.")
                    continue
                if not (1 <= len(str(sub["atributo"])) <= LIMITES_TAMANHO["atributo_codigo"]):
                    erros.append(f"Linha {numero_linha}: '{campo}[{j}]' atributo interno fora do tamanho 1-25.")
                if not (1 <= len(str(sub["valor"])) <= LIMITES_TAMANHO["atributo_valor"]):
                    erros.append(f"Linha {numero_linha}: '{campo}[{j}]' valor interno fora do tamanho 1-100.")
            if not dupla_lista:
                break
    return erros


def validar_e_preparar_item_envio(item: dict, numero_linha: int) -> ItemEnvio:
    """Valida um item (já no formato de leitura) contra as regras da API
    de envio/retificação e monta o dicionário no formato de escrita
    (chaves e ordem do schema oficial). `seq` é deixado como placeholder
    (renumerado depois, por lote)."""
    resultado = ItemEnvio(numero_linha=numero_linha, seq_original=item.get("seq"), item_pronto=None)
    erros = resultado.erros
    avisos = resultado.avisos
    pronto: dict[str, Any] = {}

    if item.get("seq") in (None, ""):
        erros.append(f"Linha {numero_linha}: 'seq' ausente.")

    codigo = item.get("codigo")
    if codigo not in (None, ""):
        try:
            codigo_int = int(codigo)
            if not (0 <= codigo_int < 10 ** LIMITES_TAMANHO["codigo"]):
                erros.append(f"Linha {numero_linha}: 'codigo' excede {LIMITES_TAMANHO['codigo']} dígitos.")
            else:
                pronto["codigo"] = codigo_int
        except (ValueError, TypeError):
            erros.append(f"Linha {numero_linha}: 'codigo' não é numérico -> {codigo!r}.")

    descricao = item.get("descricao", "")
    if descricao:
        if len(str(descricao)) > LIMITES_TAMANHO["descricao"]:
            erros.append(f"Linha {numero_linha}: 'descricao' excede {LIMITES_TAMANHO['descricao']} caracteres.")
        else:
            pronto["descricao"] = descricao

    denominacao = str(item.get("denominacao", ""))
    if not (LIMITES_TAMANHO["denominacao_min"] <= len(denominacao) <= LIMITES_TAMANHO["denominacao_max"]):
        erros.append(
            f"Linha {numero_linha}: 'denominacao' deve ter entre "
            f"{LIMITES_TAMANHO['denominacao_min']} e {LIMITES_TAMANHO['denominacao_max']} caracteres "
            f"(tem {len(denominacao)})."
        )
    pronto["denominacao"] = denominacao

    cpf_cnpj = re.sub(r"\D", "", str(item.get("cpfCnpjRaiz", "")))
    if len(cpf_cnpj) not in (8, 11) and cpf_cnpj:
        if len(cpf_cnpj) < 8:
            avisos.append(
                f"Linha {numero_linha}: 'cpfCnpjRaiz' tinha {len(cpf_cnpj)} dígito(s) "
                f"(provável perda de zero à esquerda) — completado para 8 dígitos."
            )
            cpf_cnpj = cpf_cnpj.zfill(8)
        else:
            erros.append(f"Linha {numero_linha}: 'cpfCnpjRaiz' deve ter 8 ou 11 dígitos (tem {len(cpf_cnpj)}).")
    if not cpf_cnpj:
        erros.append(f"Linha {numero_linha}: 'cpfCnpjRaiz' ausente.")
    else:
        pronto["cpfCnpjRaiz"] = cpf_cnpj

    situacao = str(item.get("situacao", "")).strip().upper()
    if situacao != str(item.get("situacao", "")).strip():
        avisos.append(f"Linha {numero_linha}: 'situacao' normalizada para maiúsculas ('{situacao}').")
    if situacao not in SITUACOES_VALIDAS:
        erros.append(f"Linha {numero_linha}: 'situacao' deve ser um de {sorted(SITUACOES_VALIDAS)} (veio {item.get('situacao')!r}).")
    pronto["situacao"] = situacao

    modalidade = str(item.get("modalidade", "")).strip().upper()
    if modalidade != str(item.get("modalidade", "")).strip():
        avisos.append(f"Linha {numero_linha}: 'modalidade' normalizada para maiúsculas ('{modalidade}').")
    if modalidade not in MODALIDADES_VALIDAS:
        erros.append(f"Linha {numero_linha}: 'modalidade' deve ser um de {sorted(MODALIDADES_VALIDAS)} (veio {item.get('modalidade')!r}).")
    pronto["modalidade"] = modalidade

    ncm = re.sub(r"\D", "", str(item.get("ncm", "")))
    if ncm and len(ncm) < 8:
        avisos.append(f"Linha {numero_linha}: 'ncm' tinha {len(ncm)} dígito(s) — completado para 8 dígitos.")
        ncm = ncm.zfill(8)
    if len(ncm) != 8:
        erros.append(f"Linha {numero_linha}: 'ncm' deve ter exatamente 8 dígitos (veio {item.get('ncm')!r}).")
    pronto["ncm"] = ncm

    versao = item.get("versao", "")
    if versao:
        if len(str(versao)) > LIMITES_TAMANHO["versao"]:
            erros.append(f"Linha {numero_linha}: 'versao' excede {LIMITES_TAMANHO['versao']} caracteres.")
        else:
            pronto["versao"] = str(versao)

    atributos = item.get("atributos") or []
    erros += _valida_atributos_simples(atributos, numero_linha, "atributos")
    pronto["atributos"] = atributos

    multi = item.get("atributosMultivalorados") or []
    erros += _valida_atributos_multivalorados(multi, numero_linha)
    pronto["atributosMultivalorados"] = multi

    compostos = item.get("atributosCompostos") or []
    erros += _valida_atributos_compostos(compostos, numero_linha, "atributosCompostos", dupla_lista=False)
    pronto["atributosCompostos"] = compostos

    compostos_multi = item.get("atributosCompostosMultivalorados") or []
    erros += _valida_atributos_compostos(compostos_multi, numero_linha, "atributosCompostosMultivalorados", dupla_lista=True)
    pronto["atributosCompostosMultivalorados"] = compostos_multi

    codigos_interno = item.get("codigosInterno") or []
    for c in codigos_interno:
        if len(str(c)) > LIMITES_TAMANHO["codigo_interno"]:
            erros.append(f"Linha {numero_linha}: código interno '{c}' excede {LIMITES_TAMANHO['codigo_interno']} caracteres.")
    pronto["codigosInterno"] = codigos_interno

    data_ref = item.get("dataReferencia", "")
    if data_ref:
        try:
            datetime.strptime(str(data_ref), "%Y-%m-%d")
            pronto["dataReferencia"] = str(data_ref)
        except ValueError:
            erros.append(f"Linha {numero_linha}: 'dataReferencia' deve estar no formato yyyy-MM-dd (veio {data_ref!r}).")

    if not erros:
        resultado.item_pronto = pronto
    return resultado


def gerar_lotes_envio(itens: list[dict], progress_cb=None) -> tuple[list[list[dict]], list[ItemEnvio]]:
    """Valida todos os itens e agrupa os válidos em lotes de até
    MAX_ITENS_POR_LOTE, renumerando 'seq' localmente (1..N) em cada lote
    -- o campo seq só precisa ser único dentro do lote enviado."""
    resultados: list[ItemEnvio] = []
    total = len(itens)
    for i, item in enumerate(itens):
        resultados.append(validar_e_preparar_item_envio(item, numero_linha=i + 2))
        if progress_cb and total:
            progress_cb((i + 1) / total)

    validos = [r for r in resultados if r.item_pronto is not None]
    lotes: list[list[dict]] = []
    for inicio in range(0, len(validos), MAX_ITENS_POR_LOTE):
        bloco = validos[inicio: inicio + MAX_ITENS_POR_LOTE]
        lote = []
        for novo_seq, r in enumerate(bloco, start=1):
            item_final = {"seq": novo_seq, **r.item_pronto}
            lote.append(item_final)
        lotes.append(lote)

    return lotes, resultados


def montar_relatorio_validacao(resultados: list[ItemEnvio]) -> str:
    linhas_relatorio = []
    total_erros = sum(len(r.erros) for r in resultados)
    total_avisos = sum(len(r.avisos) for r in resultados)
    itens_invalidos = sum(1 for r in resultados if r.item_pronto is None)
    linhas_relatorio.append(
        f"Relatório de validação — {len(resultados)} item(ns) processado(s), "
        f"{itens_invalidos} com erro (excluído dos lotes), "
        f"{total_erros} erro(s), {total_avisos} aviso(s).\n"
    )
    for r in resultados:
        if not r.erros and not r.avisos:
            continue
        linhas_relatorio.append(f"--- Linha {r.numero_linha} (seq original: {r.seq_original}) ---")
        for e in r.erros:
            linhas_relatorio.append(f"  [ERRO]  {e}")
        for a in r.avisos:
            linhas_relatorio.append(f"  [AVISO] {a}")
    return "\n".join(linhas_relatorio)


def gerar_zip_lotes(lotes: list[list[dict]], relatorio: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, lote in enumerate(lotes, start=1):
            nome = f"lote_{i:03d}_de_{len(lotes):03d}.json"
            zf.writestr(nome, json.dumps(lote, ensure_ascii=False, indent=2))
        zf.writestr("relatorio_validacao.txt", relatorio)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Leitura/escrita de arquivos (bytes em memória, sem tocar disco)
# ---------------------------------------------------------------------------

def ler_json_upload(arquivo) -> list[dict]:
    conteudo = arquivo.read()
    dados = json.loads(conteudo.decode("utf-8-sig"))
    if isinstance(dados, dict):
        # Alguns exports do Siscomex embrulham a lista em {"itens": [...]}
        for chave_provavel in ("itens", "items", "data", "result"):
            if chave_provavel in dados and isinstance(dados[chave_provavel], list):
                return dados[chave_provavel]
        raise ValueError(
            "O JSON é um objeto único, não uma lista de itens, e não foi "
            "possível localizar automaticamente a lista dentro dele."
        )
    if not isinstance(dados, list):
        raise ValueError("Formato de JSON não reconhecido (esperada uma lista de itens).")
    return dados


def dataframe_para_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Catalogo")
        workbook = writer.book
        worksheet = writer.sheets["Catalogo"]

        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#1F4E78", "font_color": "white", "border": 1}
        )
        for col_idx, col_name in enumerate(df.columns):
            worksheet.write(0, col_idx, col_name, header_fmt)
            largura = 18
            if col_name in ("descricao", "denominacao"):
                largura = 45
            elif col_name in COLUNAS_LISTA_JSON:
                largura = 35
            worksheet.set_column(col_idx, col_idx, largura)

        worksheet.freeze_panes(1, 0)
        if len(df) > 0:
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

    return buffer.getvalue()


def ler_excel_upload(arquivo) -> pd.DataFrame:
    # dtype=str evita que pandas "arrume" códigos numéricos (ex.: perder
    # zeros à esquerda) ou formate datas de forma inesperada.
    df = pd.read_excel(arquivo, dtype=str, engine="openpyxl")
    df = df.fillna("")
    return df


def json_bytes(itens: list[dict]) -> bytes:
    return json.dumps(itens, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# Interface Streamlit
# ---------------------------------------------------------------------------

def cabecalho():
    st.title("🌐 Catálogo de Itens Siscomex — Conversor JSON ⇄ Excel")
    st.caption(
        "Converta o catálogo de itens do Portal Único de Comércio Exterior "
        "entre JSON e Excel para edição em massa. Suporta milhares de itens."
    )


def aba_json_para_excel():
    st.subheader("JSON → Excel")
    st.write(
        "Envie o arquivo JSON exportado do Catálogo de Itens do Siscomex "
        "(lista de objetos com `seq`, `codigo`, `descricao`, `ncm`, etc.) "
        "para gerar uma planilha editável."
    )

    arquivo = st.file_uploader("Arquivo JSON do catálogo", type=["json"], key="upload_json")

    if arquivo is None:
        return

    try:
        with st.spinner("Lendo JSON..."):
            itens = ler_json_upload(arquivo)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        st.error(f"Não foi possível interpretar o JSON: {e}")
        return

    st.success(f"{len(itens):,} item(ns) encontrado(s) no arquivo.".replace(",", "."))

    progresso = st.progress(0.0, text="Processando itens...")
    resultado = json_para_dataframe(itens, progress_cb=lambda p: progresso.progress(p, text=f"Processando itens... {int(p*100)}%"))
    progresso.empty()

    if resultado.avisos:
        with st.expander(f"⚠️ {len(resultado.avisos)} aviso(s)"):
            for a in resultado.avisos:
                st.write("- " + a)

    st.write(f"**Pré-visualização** ({resultado.total_itens:,} linha(s)):".replace(",", "."))
    st.dataframe(resultado.dataframe.head(50), use_container_width=True, height=350)

    with st.spinner("Gerando planilha Excel..."):
        excel_bytes = dataframe_para_excel_bytes(resultado.dataframe)

    nome_saida = f"catalogo_siscomex_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    st.download_button(
        "⬇️ Baixar Excel",
        data=excel_bytes,
        file_name=nome_saida,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    st.info(
        "As colunas **atributos**, **atributosMultivalorados**, "
        "**atributosCompostos** e **atributosCompostosMultivalorados** "
        "contêm o JSON original de cada campo, para permitir reconstrução "
        "exata ao reimportar. Edite com cuidado — texto inválido nessas "
        "colunas será reportado como erro na conversão de volta."
    )


def aba_excel_para_json():
    st.subheader("Excel → JSON (formato Catálogo Siscomex)")
    st.write(
        "Envie uma planilha no formato gerado por este app (ou compatível) "
        "para reconstruir o JSON no padrão do Catálogo de Itens do Siscomex."
    )

    arquivo = st.file_uploader("Arquivo Excel (.xlsx)", type=["xlsx"], key="upload_excel")

    if arquivo is None:
        return

    try:
        with st.spinner("Lendo Excel..."):
            df = ler_excel_upload(arquivo)
    except Exception as e:  # leitura de excel pode falhar de várias formas
        st.error(f"Não foi possível ler a planilha: {e}")
        return

    st.success(f"{len(df):,} linha(s) lida(s) da planilha.".replace(",", "."))

    progresso = st.progress(0.0, text="Reconstruindo itens...")
    itens, avisos, erros = dataframe_para_json(
        df, progress_cb=lambda p: progresso.progress(p, text=f"Reconstruindo itens... {int(p*100)}%")
    )
    progresso.empty()

    if avisos:
        with st.expander(f"⚠️ {len(avisos)} aviso(s)"):
            for a in avisos:
                st.write("- " + a)

    if erros:
        with st.expander(f"❌ {len(erros)} erro(s) encontrado(s)", expanded=True):
            for e in erros[:200]:
                st.write("- " + e)
            if len(erros) > 200:
                st.write(f"... e mais {len(erros) - 200} erro(s).")
        st.warning(
            "Itens com erro de JSON nas colunas de atributos foram exportados "
            "com essa lista vazia ([]). Corrija a planilha e reprocesse se necessário."
        )

    st.write("**Pré-visualização** (primeiros itens reconstruídos):")
    st.json(itens[:3] if itens else [], expanded=False)

    saida = json_bytes(itens)
    nome_saida = f"catalogo_siscomex_{datetime.now():%Y%m%d_%H%M%S}.json"
    st.download_button(
        "⬇️ Baixar JSON",
        data=saida,
        file_name=nome_saida,
        mime="application/json",
        type="primary",
    )

    st.caption(f"Tamanho do arquivo gerado: {len(saida) / 1024:.1f} KB — {len(itens):,} item(ns).".replace(",", "."))


def aba_lotes_envio():
    st.subheader("Lotes para envio/retificação na API do Siscomex")
    st.write(
        "Envie uma planilha (mesmo layout gerado por este app) para validar "
        "cada item contra as regras oficiais da API de importação de "
        "produtos e gerar os arquivos JSON já divididos em lotes de até "
        f"**{MAX_ITENS_POR_LOTE} itens** (limite da API). Itens com erro "
        "são listados no relatório e excluídos dos lotes."
    )
    with st.expander("O que muda em relação ao 'Excel → JSON' simples"):
        st.markdown(
            "- `situacao` e `modalidade` são normalizadas para maiúsculas.\n"
            "- `cpfCnpjRaiz` e `ncm` são completados com zeros à esquerda "
            "se vierem com dígitos a menos (comum quando o Excel remove "
            "zeros de células numéricas).\n"
            "- `seq` é renumerado de 1 a 100 **dentro de cada lote** — a "
            "API só exige que seja único por requisição.\n"
            "- `inicioVigencia` (campo só de leitura) é removido; "
            "`dataReferencia` (campo só de escrita, opcional) é mantido "
            "se preenchido.\n"
            "- Tamanhos de campo (`descricao` ≤ 3700, `denominacao` 1-120, "
            "`atributo` ≤ 25, `valor` ≤ 100, código interno ≤ 60, etc.) "
            "são validados um a um."
        )

    arquivo = st.file_uploader("Arquivo Excel (.xlsx)", type=["xlsx"], key="upload_excel_lotes")
    if arquivo is None:
        return

    try:
        with st.spinner("Lendo Excel..."):
            df = ler_excel_upload(arquivo)
    except Exception as e:
        st.error(f"Não foi possível ler a planilha: {e}")
        return

    st.success(f"{len(df):,} linha(s) lida(s) da planilha.".replace(",", "."))

    progresso1 = st.progress(0.0, text="Reconstruindo itens...")
    itens, avisos_leitura, erros_leitura = dataframe_para_json(
        df, progress_cb=lambda p: progresso1.progress(p, text=f"Reconstruindo itens... {int(p*100)}%")
    )
    progresso1.empty()

    if erros_leitura:
        with st.expander(f"❌ {len(erros_leitura)} erro(s) de leitura da planilha", expanded=True):
            for e in erros_leitura[:200]:
                st.write("- " + e)

    progresso2 = st.progress(0.0, text="Validando contra as regras da API...")
    lotes, resultados = gerar_lotes_envio(
        itens, progress_cb=lambda p: progresso2.progress(p, text=f"Validando... {int(p*100)}%")
    )
    progresso2.empty()

    total_itens = len(resultados)
    total_validos = sum(len(l) for l in lotes)
    total_invalidos = total_itens - total_validos
    total_erros = sum(len(r.erros) for r in resultados)
    total_avisos = sum(len(r.avisos) for r in resultados)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Itens processados", f"{total_itens:,}".replace(",", "."))
    col2.metric("Válidos (nos lotes)", f"{total_validos:,}".replace(",", "."))
    col3.metric("Com erro (excluídos)", f"{total_invalidos:,}".replace(",", "."))
    col4.metric("Lotes gerados", len(lotes))

    if total_invalidos:
        st.error(
            f"{total_invalidos} item(ns) com erro de validação foram "
            "excluídos dos lotes. Veja o relatório para corrigir na planilha."
        )
    if total_avisos:
        st.warning(f"{total_avisos} aviso(s) de normalização automática (zeros à esquerda, maiúsculas etc.).")

    relatorio = montar_relatorio_validacao(resultados)
    with st.expander(f"📋 Relatório completo ({total_erros} erro(s), {total_avisos} aviso(s))"):
        st.text(relatorio if relatorio.strip() else "Nenhum item com erro ou aviso.")

    if not lotes:
        st.warning("Nenhum item válido — nenhum lote foi gerado.")
        return

    st.write(f"**Pré-visualização** (primeiros itens do lote 1, formato de envio):")
    st.json(lotes[0][:3], expanded=False)

    zip_bytes = gerar_zip_lotes(lotes, relatorio)
    nome_zip = f"lotes_siscomex_{datetime.now():%Y%m%d_%H%M%S}.zip"
    st.download_button(
        f"⬇️ Baixar ZIP com {len(lotes)} lote(s) + relatório",
        data=zip_bytes,
        file_name=nome_zip,
        mime="application/zip",
        type="primary",
    )


def barra_lateral():
    with st.sidebar:
        st.header("Sobre")
        st.write(
            "Ferramenta interna para conversão em massa do **Catálogo de "
            "Itens do Siscomex** entre JSON e Excel."
        )
        st.markdown("---")
        st.markdown(
            "**Campos escalares:**\n"
            "seq, codigo, descricao, denominacao, cpfCnpjRaiz, situacao, "
            "modalidade, ncm, versao, inicioVigencia, dataReferencia"
        )
        st.caption(
            "`inicioVigencia` é só de leitura (vem da consulta); "
            "`dataReferencia` é só de escrita (usado ao criar item com "
            "data retroativa) — normalmente só um dos dois estará preenchido."
        )
        st.markdown(
            "**Lista simples:** codigosInterno (separado por `;` na planilha)"
        )
        st.markdown(
            "**Listas complexas (JSON cru na célula):**\n"
            "atributos, atributosMultivalorados, atributosCompostos, "
            "atributosCompostosMultivalorados"
        )
        if CAMPOS_OMITIVEIS_SE_VAZIOS:
            st.markdown(
                "**Campos omitidos do JSON se vazios:** "
                + ", ".join(sorted(CAMPOS_OMITIVEIS_SE_VAZIOS))
                + " — fiel a itens do catálogo original que não têm essa chave."
            )
        st.markdown("---")
        st.caption("Processa milhares de itens em memória (sem gravar em disco).")


def modulo_siscomex():
    botao_voltar()
    barra_lateral()
    cabecalho()
    tab1, tab2, tab3 = st.tabs(
        ["📤 JSON → Excel", "📥 Excel → JSON", "📦 Lotes para envio (API)"]
    )
    with tab1:
        aba_json_para_excel()
    with tab2:
        aba_excel_para_json()
    with tab3:
        aba_lotes_envio()


# ==============================================================================
# NAVEGAÇÃO PRINCIPAL
# ==============================================================================

def main():
    load_css()

    query_params = st.query_params
    modulo = query_params.get("modulo", "home")

    if modulo == "home" or not modulo:
        pagina_home()
        return

    if modulo == "processador_txt":
        modulo_processador_txt()
    elif modulo == "mastersaf":
        modulo_mastersaf()
    elif modulo == "siscomex":
        modulo_siscomex()
    else:
        pagina_home()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        st.code(traceback.format_exc())
