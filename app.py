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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import subprocess
import concurrent.futures
import threading

# ==============================================================================
# CONFIGURAÇÃO AUTOMÁTICA DO SERVIDOR STREAMLIT
# Suporta PDFs gigantes — até 2 GB
# ==============================================================================
_PDF_CHUNK_PAGES = 20   # Streamlit Cloud ~1GB RAM — chunks menores evitam OOM

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

CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# COMPAT HELPER — compatibilidade de largura entre versões do Streamlit
#
# Histórico real das versões:
#   • Streamlit < 1.44  → use_container_width=True/False   (ATUAL no Streamlit Cloud: 1.57.0)
#   • Streamlit >= 1.44 → width='stretch'/'content'        (ainda não lançado publicamente)
#
# ATENÇÃO: 1.57.0 É UMA VERSÃO ATUAL QUE AINDA USA use_container_width.
# A numeração do Streamlit não é linear — 1.57 NÃO é maior que 1.44 no sentido
# de que width= tenha sido adicionado; a API width= foi anunciada para versão
# futura. Por isso usamos uma probe direta no widget, não comparação de versão.
# ==============================================================================
def _w(stretch: bool = True):
    """Retorna o kwarg correto de largura para widgets Streamlit.

    Usa probe segura: tenta inspecionar a assinatura de st.dataframe para
    detectar se o parâmetro 'width' (novo) ou 'use_container_width' (atual)
    está disponível. Isso é 100% à prova de versão.
    """
    try:
        import inspect
        sig = inspect.signature(st.dataframe)
        if "width" in sig.parameters and "use_container_width" not in sig.parameters:
            # API nova: width='stretch'|'content'
            return {"width": "stretch" if stretch else "content"}
        else:
            # API atual (Streamlit ≤ 1.57.x e anteriores)
            return {"use_container_width": stretch}
    except Exception:
        # fallback conservador: use_container_width funciona em todas versões conhecidas
        return {"use_container_width": stretch}

_WS = _w(True)   # largura total (substitui use_container_width=True)
_WC = _w(False)  # largura natural (substitui use_container_width=False)

# ==============================================================================
# SESSION STATE
# ==============================================================================
_defaults = {
    'selected_xml': None, 'cte_data': None,
    'parsed_duimp': None, 'parsed_sigraweb': None,
    'merged_df': None, 'last_duimp': None,
    'layout_app2': 'sigraweb',
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
def show_loading_animation(message="Processando..."):
    with st.spinner(message):
        pb = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            pb.progress(i + 1)
        pb.empty()

def show_processing_animation(message="Analisando dados..."):
    ph_container = st.empty()
    with ph_container.container():
        _, c, _ = st.columns([1, 2, 1])
        with c:
            st.info(f"⏳ {message}")
            sp = st.empty()
            chars = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]
            for i in range(20):
                sp.markdown(
                    f"<div style='text-align:center;font-size:24px'>{chars[i%8]}</div>",
                    unsafe_allow_html=True,
                )
                time.sleep(0.1)
    ph_container.empty()

def show_success_animation(message="Concluído!"):
    ph_container = st.empty()
    with ph_container.container():
        st.success(f"✅ {message}")
        time.sleep(1.2)
    ph_container.empty()

def ph(html: str):
    """Shortcut for st.markdown with unsafe_allow_html=True"""
    st.markdown(html, unsafe_allow_html=True)

def page_header(icon: str, title: str, sub: str):
    ph(f"""
    <div class="ph-hdr">
        <span class="ph-icon">{icon}</span>
        <div>
            <div class="ph-title">{title}</div>
            <div class="ph-sub">{sub}</div>
        </div>
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
# CSS — DESIGN SYSTEM PROFISSIONAL RESPONSIVO
# ==============================================================================
def load_css():
    ph("""<style>
    /* ── Google Fonts ─────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Design Tokens ────────────────────────────────────── */
    :root{
        --navy:#0A0F1E;
        --blue-dark:#0F2040;
        --blue:#1E3A8A;
        --blue-m:#2563EB;
        --blue-l:#3B82F6;
        --blue-xl:#60A5FA;
        --blue-bg:#EFF6FF;
        --blue-b:#BFDBFE;
        --green:#059669;
        --green-l:#10B981;
        --green-bg:#D1FAE5;
        --amber:#D97706;
        --amber-bg:#FEF3C7;
        --red:#DC2626;
        --red-bg:#FEE2E2;
        --bg:#F0F4FA;
        --surface:#FFFFFF;
        --surface2:#F8FAFC;
        --border:#E2E8F0;
        --border-strong:#CBD5E1;
        --muted:#64748B;
        --muted2:#94A3B8;
        --text:#0F172A;
        --r:10px;
        --r-lg:16px;
        --r-xl:24px;
        --r-2xl:32px;
        --sh0:0 1px 3px rgba(0,0,0,.06);
        --sh1:0 2px 8px rgba(0,0,0,.08),0 1px 3px rgba(0,0,0,.05);
        --sh2:0 8px 24px rgba(0,0,0,.10),0 2px 8px rgba(0,0,0,.06);
        --sh3:0 20px 60px rgba(0,0,0,.14),0 4px 16px rgba(0,0,0,.08);
        --sh-blue:0 8px 32px rgba(37,99,235,.20);
        --tr:all .2s cubic-bezier(.4,0,.2,1);
        --glow:0 0 0 3px rgba(59,130,246,.25);
        --glow-green:0 0 0 3px rgba(16,185,129,.25);
    }

    /* ── Base ─────────────────────────────────────────────── */
    html,body,[class*="css"]{
        font-family:'Inter','Segoe UI',system-ui,sans-serif;
        -webkit-font-smoothing:antialiased;
        color:var(--text);
    }
    ::-webkit-scrollbar{width:6px;height:6px}
    ::-webkit-scrollbar-track{background:var(--bg);border-radius:10px}
    ::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:10px}
    ::-webkit-scrollbar-thumb:hover{background:var(--muted2)}
    .block-container{padding-top:1rem!important;padding-bottom:2rem!important;max-width:1400px!important;}

    /* ── HERO ──────────────────────────────────────────────── */
    .hero{
        position:relative;
        background:linear-gradient(135deg,#050D1F 0%,#0F2040 35%,#1E3A8A 65%,#1D4ED8 100%);
        border-radius:var(--r-2xl);
        padding:2.8rem 3.5rem 2.4rem;
        margin-bottom:1.6rem;
        text-align:center;
        overflow:hidden;
        border:1px solid rgba(255,255,255,.06);
        box-shadow:var(--sh3),var(--sh-blue);
    }
    .hero::before{
        content:'';position:absolute;inset:0;
        background-image:
            linear-gradient(rgba(255,255,255,.03) 1px,transparent 1px),
            linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px);
        background-size:48px 48px;pointer-events:none;
    }
    .hero::after{
        content:'';position:absolute;right:-80px;top:-80px;
        width:340px;height:340px;border-radius:50%;
        background:radial-gradient(circle,rgba(96,165,250,.15) 0%,transparent 65%);
        pointer-events:none;
    }
    .hero-glow-left{
        position:absolute;left:-100px;bottom:-80px;
        width:280px;height:280px;border-radius:50%;
        background:radial-gradient(circle,rgba(16,185,129,.10) 0%,transparent 65%);
        pointer-events:none;
    }
    .hero-logo{
        max-width:180px;margin-bottom:1rem;
        filter:drop-shadow(0 4px 18px rgba(0,0,0,.40));
        position:relative;z-index:1;
        transition:var(--tr);
    }
    .hero-logo:hover{transform:scale(1.03);}
    .hero-title{
        font-size:2.2rem;font-weight:900;color:#fff;
        margin:0 0 .4rem;letter-spacing:-.8px;
        line-height:1.12;position:relative;z-index:1;
        text-shadow:0 2px 12px rgba(0,0,0,.3);
    }
    .hero-sub{
        font-size:.95rem;color:rgba(255,255,255,.65);
        margin:0 0 1.4rem;position:relative;z-index:1;
        letter-spacing:.1px;
    }
    .hero-chips{
        display:flex;justify-content:center;
        gap:.5rem;flex-wrap:wrap;position:relative;z-index:1;
    }
    .chip{
        display:inline-flex;align-items:center;gap:.3rem;
        background:rgba(255,255,255,.10);
        border:1px solid rgba(255,255,255,.20);
        color:rgba(255,255,255,.90);border-radius:20px;
        padding:.22rem .8rem;font-size:.74rem;
        font-weight:600;letter-spacing:.3px;
        transition:var(--tr);backdrop-filter:blur(6px);
    }
    .chip:hover{background:rgba(255,255,255,.20);transform:translateY(-1px);}

    /* ── PAGE HEADER ───────────────────────────────────────── */
    .ph-hdr{
        display:flex;align-items:center;gap:1rem;
        background:var(--surface);
        border:1px solid var(--border);
        border-left:4px solid var(--blue-l);
        border-radius:var(--r);padding:.9rem 1.4rem;
        margin-bottom:1.2rem;box-shadow:var(--sh0);
        transition:var(--tr);
    }
    .ph-hdr:hover{box-shadow:var(--sh1);border-left-color:var(--blue-m);}
    .ph-icon{font-size:2rem;flex-shrink:0;line-height:1;}
    .ph-title{font-size:1.3rem;font-weight:800;color:var(--blue);line-height:1.2;}
    .ph-sub{font-size:.8rem;color:var(--muted);margin-top:.15rem;}

    /* ── SECTION TITLE ─────────────────────────────────────── */
    .stitle{
        display:flex;align-items:center;
        font-size:.88rem;font-weight:700;
        color:var(--blue);
        padding:.5rem 0 .5rem .85rem;
        border-left:3px solid var(--blue-l);
        margin:1.1rem 0 .7rem;
        background:linear-gradient(90deg,rgba(59,130,246,.07),transparent 80%);
        border-radius:0 var(--r) var(--r) 0;
        letter-spacing:.2px;
    }

    /* ── CARD ──────────────────────────────────────────────── */
    .card{
        background:var(--surface);
        border-radius:var(--r-lg);
        border:1px solid var(--border);
        box-shadow:var(--sh1);
        padding:1.3rem 1.5rem;
        margin-bottom:1rem;
        transition:var(--tr);
    }
    .card:hover{box-shadow:var(--sh2);border-color:var(--blue-b);}
    .card-accent{border-top:3px solid var(--blue-l);}

    /* ── UPLOAD ZONE ───────────────────────────────────────── */
    .uzone{
        background:linear-gradient(135deg,var(--blue-bg),#DBEAFE88);
        border:2px dashed #93C5FD;
        border-radius:var(--r-lg);padding:1.1rem 1rem;
        text-align:center;margin-bottom:.5rem;
        transition:var(--tr);cursor:pointer;
    }
    .uzone:hover{border-color:var(--blue-l);background:linear-gradient(135deg,#DBEAFE,#EFF6FF);}
    .uzone-icon{font-size:1.7rem;line-height:1;margin-bottom:.3rem;}
    .uzone-title{font-weight:700;color:var(--blue);font-size:.9rem;margin-top:.2rem;}
    .uzone-sub{font-size:.75rem;color:var(--muted);margin-top:.15rem;}

    /* ── STATUS BOXES ──────────────────────────────────────── */
    .sbox{
        padding:.7rem 1.1rem;border-radius:var(--r);
        font-size:.88rem;font-weight:500;margin:.4rem 0;
        display:flex;align-items:center;gap:.5rem;
    }
    .sbox-ok{
        background:var(--green-bg);color:#065F46;
        border:1px solid #A7F3D0;border-left:3px solid var(--green);
    }
    .sbox-warn{
        background:var(--amber-bg);color:#78350F;
        border:1px solid #FDE68A;border-left:3px solid var(--amber);
    }
    .sbox-err{
        background:var(--red-bg);color:#991B1B;
        border:1px solid #FECACA;border-left:3px solid var(--red);
    }

    /* ── LABEL BADGE ───────────────────────────────────────── */
    .lbadge{
        display:inline-flex;align-items:center;gap:.35rem;
        background:var(--blue-m);color:#fff;
        border-radius:var(--r);padding:.3rem .85rem;
        font-size:.78rem;font-weight:700;
        margin-top:.5rem;box-shadow:var(--sh-blue);
        letter-spacing:.2px;
    }
    .lbadge.amber{background:var(--amber);}
    .lbadge.green{background:var(--green-l);}

    /* ── PILL ──────────────────────────────────────────────── */
    .ipill{
        display:inline-flex;align-items:center;gap:.35rem;
        background:var(--blue-bg);border:1px solid var(--blue-b);
        color:var(--blue);border-radius:20px;
        padding:.22rem .8rem;font-size:.78rem;font-weight:600;
        margin-bottom:.5rem;
    }

    /* ── FIELD LABEL ───────────────────────────────────────── */
    .flabel{
        font-size:.76rem;font-weight:600;color:var(--muted);
        text-transform:uppercase;letter-spacing:.6px;margin-bottom:.3rem;
    }

    /* ── EMPTY STATE ───────────────────────────────────────── */
    .empty{
        text-align:center;padding:3.5rem 1.5rem;
        color:var(--muted);border:2px dashed var(--border);
        border-radius:var(--r-xl);background:var(--surface2);
    }
    .empty-icon{font-size:3rem;margin-bottom:.6rem;opacity:.5;}
    .empty-title{font-size:1rem;font-weight:700;color:var(--muted2);margin-bottom:.3rem;}
    .empty-sub{font-size:.82rem;color:#CBD5E1;}

    /* ── TABS ──────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"]{
        gap:3px;background:var(--bg);
        border-radius:var(--r-lg);
        padding:5px;border:1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"]{
        border-radius:8px;font-weight:600;font-size:.85rem;
        padding:.42rem 1rem;transition:var(--tr);color:var(--muted);
        border:none;
    }
    .stTabs [data-baseweb="tab"]:hover{
        color:var(--blue-m);background:rgba(59,130,246,.08);
    }
    .stTabs [aria-selected="true"]{
        background:var(--surface)!important;
        color:var(--blue)!important;
        box-shadow:var(--sh1)!important;
    }

    /* ── BUTTONS ───────────────────────────────────────────── */
    .stButton>button{
        border-radius:var(--r)!important;font-weight:600!important;
        font-size:.86rem!important;letter-spacing:.1px;
        transition:var(--tr)!important;
    }
    .stButton>button:hover{
        transform:translateY(-1px)!important;
        box-shadow:var(--sh2)!important;
    }
    .stButton>button:active{
        transform:translateY(0)!important;
        box-shadow:var(--sh0)!important;
    }
    .stButton>button[kind="primary"]{
        background:linear-gradient(135deg,var(--blue-m),var(--blue))!important;
        box-shadow:var(--sh-blue)!important;border:none!important;
    }
    .stButton>button[kind="primary"]:hover{
        background:linear-gradient(135deg,#1D4ED8,var(--blue))!important;
    }

    /* ── RADIO ─────────────────────────────────────────────── */
    div[data-testid="stRadio"]>div{gap:.5rem;}
    div[data-testid="stRadio"] label{
        background:var(--surface);
        border:1.5px solid var(--border);
        border-radius:var(--r);padding:.55rem 1rem;
        cursor:pointer;transition:var(--tr);
        font-weight:500;font-size:.86rem;
    }
    div[data-testid="stRadio"] label:hover{
        border-color:var(--blue-l);
        background:var(--blue-bg);
    }

    /* ── EXPANDER ──────────────────────────────────────────── */
    .streamlit-expanderHeader{
        font-weight:600;font-size:.88rem;color:var(--blue);
        background:var(--surface2);border-radius:8px;
        padding:.48rem .8rem!important;
    }
    [data-testid="stExpander"]{
        border:1px solid var(--border)!important;
        border-radius:var(--r)!important;
    }

    /* ── METRICS ───────────────────────────────────────────── */
    [data-testid="metric-container"]{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:var(--r-lg);
        padding:.8rem 1rem;
        box-shadow:var(--sh0);
        transition:var(--tr);
        position:relative;overflow:hidden;
    }
    [data-testid="metric-container"]::after{
        content:'';position:absolute;top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,var(--blue-l),var(--blue-m));
        border-radius:var(--r) var(--r) 0 0;
    }
    [data-testid="metric-container"]:hover{
        box-shadow:var(--sh1);border-color:var(--blue-b);
    }
    [data-testid="stMetricValue"]{
        font-size:1.25rem!important;font-weight:700!important;
        color:var(--blue)!important;font-family:'Inter',sans-serif!important;
    }
    [data-testid="stMetricLabel"]{
        font-size:.72rem!important;font-weight:600!important;
        color:var(--muted)!important;text-transform:uppercase;
        letter-spacing:.5px;
    }

    /* ── INPUTS ────────────────────────────────────────────── */
    .stTextInput input,.stNumberInput input{
        border-radius:var(--r)!important;
        border:1.5px solid var(--border)!important;
        font-size:.86rem!important;transition:var(--tr);
        background:var(--surface)!important;
    }
    .stTextInput input:focus,.stNumberInput input:focus{
        border-color:var(--blue-l)!important;
        box-shadow:var(--glow)!important;
    }
    .stPasswordInput input{
        border-radius:var(--r)!important;
        border:1.5px solid var(--border)!important;
        font-size:.86rem!important;transition:var(--tr);
    }
    .stPasswordInput input:focus{
        border-color:var(--blue-l)!important;
        box-shadow:var(--glow)!important;
    }

    /* ── DATA TABLES ───────────────────────────────────────── */
    [data-testid="stDataFrame"],[data-testid="stDataEditor"]{
        border-radius:var(--r-lg)!important;
        border:1px solid var(--border)!important;
        overflow:hidden;
        box-shadow:var(--sh1)!important;
    }

    /* ── DIVIDER ───────────────────────────────────────────── */
    hr{border:none;border-top:1px solid var(--border);margin:1rem 0;}

    /* ── MASTERSAF COMPONENTS ──────────────────────────────── */
    .ms-log-area{
        background:#080D18;
        border:1px solid rgba(59,130,246,.15);
        border-radius:var(--r-lg);
        padding:1.1rem 1.2rem;
        font-family:'JetBrains Mono',monospace;
        font-size:.75rem;color:#CBD5E1;
        max-height:420px;overflow-y:auto;
        white-space:pre-wrap;line-height:1.6;
        box-shadow:inset 0 2px 8px rgba(0,0,0,.3);
    }
    .ms-log-area .log-ts{color:#334155;}
    .ms-log-area .log-ok{color:#22D3EE;}
    .ms-log-area .log-warn{color:#F59E0B;}
    .ms-log-area .log-err{color:#F87171;}
    .ms-log-area .log-info{color:#60A5FA;}

    .ms-stat-grid{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:1rem;margin:1rem 0;
    }
    .ms-stat-card{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:var(--r-lg);
        padding:1.2rem 1.4rem;
        position:relative;overflow:hidden;
        transition:var(--tr);
        box-shadow:var(--sh0);
    }
    .ms-stat-card::before{
        content:'';position:absolute;
        top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,var(--blue-l),var(--green-l));
    }
    .ms-stat-card:hover{
        box-shadow:var(--sh2);
        transform:translateY(-2px);
    }
    .ms-stat-label{
        font-size:.68rem;font-weight:700;color:var(--muted);
        text-transform:uppercase;letter-spacing:.12em;margin-bottom:.55rem;
    }
    .ms-stat-value{
        font-family:'JetBrains Mono',monospace;
        font-size:1.6rem;font-weight:600;
        color:var(--green-l);line-height:1;
    }
    .ms-stat-sub{font-size:.72rem;color:var(--muted2);margin-top:.35rem;}

    /* ── PROGRESS / ANIMATIONS ─────────────────────────────── */
    @keyframes spin{to{transform:rotate(360deg)}}
    .spinner{animation:spin 1.2s linear infinite;display:inline-block;}

    @keyframes fadeUp{
        from{opacity:0;transform:translateY(10px)}
        to{opacity:1;transform:translateY(0)}
    }
    .fade-up{animation:fadeUp .3s ease forwards;}

    @keyframes pulse-glow{
        0%,100%{box-shadow:0 0 0 0 rgba(59,130,246,.4)}
        50%{box-shadow:0 0 0 8px rgba(59,130,246,.0)}
    }
    .pulse{animation:pulse-glow 2s ease-in-out infinite;}

    @keyframes shimmer{
        0%{background-position:-200% 0}
        100%{background-position:200% 0}
    }
    .skeleton{
        background:linear-gradient(90deg,var(--border) 25%,var(--surface2) 50%,var(--border) 75%);
        background-size:200% 100%;animation:shimmer 1.4s ease infinite;
        border-radius:var(--r);height:1rem;
    }

    /* ── RESPONSIVE ────────────────────────────────────────── */
    @media(max-width:1024px){
        .ms-stat-grid{grid-template-columns:repeat(2,1fr);}
        .hero{padding:2rem 2rem 1.8rem;}
        .hero-title{font-size:1.8rem;}
    }
    @media(max-width:768px){
        .hero{padding:1.6rem 1.2rem 1.4rem;border-radius:var(--r-xl);}
        .hero-title{font-size:1.45rem;letter-spacing:-.4px;}
        .hero-logo{max-width:140px;}
        .hero-sub{font-size:.85rem;}
        .ms-stat-grid{grid-template-columns:1fr 1fr;}
        .stTabs [data-baseweb="tab"]{padding:.35rem .6rem;font-size:.78rem;}
        .chip{font-size:.68rem;padding:.15rem .55rem;}
        .ph-title{font-size:1.1rem;}
        .block-container{padding-left:.75rem!important;padding-right:.75rem!important;}
    }
    @media(max-width:480px){
        .hero-title{font-size:1.2rem;}
        .hero{padding:1.2rem .9rem 1rem;border-radius:var(--r-lg);}
        .ms-stat-grid{grid-template-columns:1fr;}
        .hero-sub{display:none;}
    }
    </style>""")


# ==============================================================================
# PARTE 1 — PROCESSADOR TXT
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
            padroes = padroes_default + [
                p.strip() for p in padroes_add.split(",") if p.strip()
            ] if padroes_add else padroes_default
        ph(f'<div class="ipill">🔍 {len(padroes)} padrões ativos</div>')

    if arquivo is not None:
        st.markdown("")
        if st.button("🔄 Processar Arquivo TXT", type="primary", **_WS):
            try:
                show_loading_animation("Analisando arquivo...")
                conteudo = arquivo.read()
                show_processing_animation("Processando linhas...")
                resultado, total = processar_arquivo(conteudo, padroes)
                if resultado is not None:
                    show_success_animation("Processamento concluído!")
                    mantidas  = len(resultado.splitlines())
                    removidas = total - mantidas
                    k1, k2, k3 = st.columns(3)
                    k1.metric("📋 Originais",  total)
                    k2.metric("✅ Mantidas",   mantidas)
                    k3.metric("🗑️ Removidas",  removidas,
                              delta=f"-{removidas}", delta_color="inverse")
                    section_title("👁️ Prévia")
                    st.text_area("Conteúdo processado", resultado, height=260)
                    buf = BytesIO()
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
        empty_state("📂", "Nenhum arquivo carregado",
                    "Selecione um arquivo .TXT acima para começar")


# ==============================================================================
# PARTE 2 — MASTERSAF AUTOMAÇÃO XML
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


# ── FUNÇÕES DO WEBDRIVER ──────────────────────────────────────────
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

    # Estratégias em ordem de prioridade:
    # 1. chromedriver do sistema (instalado pelo apt junto com chromium — VERSÃO COMPATÍVEL)
    # 2. chromium-driver (nome alternativo no Debian/Ubuntu)
    # 3. google-chrome + chromedriver padrão do PATH
    # 4. chromium binary explícito
    # NUNCA usar webdriver-manager: baixa ChromeDriver 114 para Chrome 136+ → crash
    for strategy in [
        lambda: _try_fixed_path(opts, '/usr/bin/chromedriver'),
        lambda: _try_fixed_path(opts, '/usr/lib/chromium/chromedriver'),
        lambda: _try_fixed_path(opts, '/usr/bin/chromium-driver'),
        lambda: _try_default(opts),
        lambda: _try_chromium_binary(opts),
    ]:
        try:
            drv = strategy()
            if drv:
                return drv
        except Exception:
            continue
    raise RuntimeError("Nenhuma estratégia de ChromeDriver funcionou. Verifique se chromium e chromium-driver estão instalados via packages.txt.")

def _try_fixed_path(opts, path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"ChromeDriver não encontrado em: {path}")
    return webdriver.Chrome(service=Service(path), options=opts)

def _try_default(opts):
    return webdriver.Chrome(options=opts)

def _try_chromium_binary(opts):
    for binary in ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']:
        if os.path.exists(binary):
            opts.binary_location = binary
            return webdriver.Chrome(options=opts)
    raise FileNotFoundError("Nenhum binário Chromium/Chrome encontrado")

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


# ── UI MASTERSAF AUTOMAÇÃO ────────────────────────────────────────
def mastersaf_automacao():
    page_header("⚡", "MasterSAF — Automação XML",
                "Download e processamento em massa de CT-es direto do portal")

    tab_exec, tab_resultados, tab_export = st.tabs([
        "🚀  Executar Automação",
        "📊  Resultados & Análise",
        "📥  Exportar Dados",
    ])

    # ════════════════════════════════════════════════════════════
    # TAB EXECUTAR
    # ════════════════════════════════════════════════════════════
    with tab_exec:
        section_title("⚙️ Configuração da Automação")
        col_a, col_b = st.columns(2, gap="large")

        with col_a:
            with st.container():
                ph('<div class="card card-accent"><div class="flabel">🔑 Credenciais de Acesso</div>')
                usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="ms_usuario")
                senha   = st.text_input("Senha",   type="password", placeholder="••••••••", key="ms_senha")
                ph('</div>')

            with st.container():
                ph('<div class="card" style="margin-top:1.2rem"><div class="flabel">📅 Período de Busca</div>')
                p1, p2 = st.columns(2)
                with p1:
                    data_ini = st.text_input("Data Inicial", value="08/05/2026", key="ms_dt_ini")
                with p2:
                    data_fin = st.text_input("Data Final",   value="08/05/2026", key="ms_dt_fin")
                ph('</div>')

        with col_b:
            with st.container():
                ph('<div class="card card-accent"><div class="flabel">⚙️ Parâmetros de Execução</div>')
                qtd_loops = st.number_input(
                    "Quantidade de Páginas (Loops)",
                    min_value=1, max_value=1000, value=5,
                    help="Cada loop processa uma página de até 200 CT-es.",
                    key="ms_qtd_loops",
                )
                gerar_excel = st.checkbox("Gerar Excel consolidado dos CT-es", value=True, key="ms_gerar_excel")
                gerar_zip   = st.checkbox("Disponibilizar ZIP com XMLs brutos", value=True, key="ms_gerar_zip")
                ph('</div>')

            with st.container():
                ph("""<div class="card" style="margin-top:1.2rem">
                <div class="flabel">🚀 Executar</div>
                <p style="font-size:0.82rem;color:var(--muted);margin-bottom:1rem;line-height:1.6;">
                    O navegador será executado em <strong style="color:var(--blue-m)">modo headless</strong>.
                    Acompanhe o progresso em tempo real abaixo.
                </p>""")
                iniciar = st.button("⚡  Iniciar Automação", key="ms_btn_iniciar",
                                    type="primary", **_WS)
                ph('</div>')

        # ── Execução ──────────────────────────────────────────
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
                status_box   = st.info("⏳ Inicializando ambiente e navegador...")
                progress_bar = st.progress(0)
                log_placeholder = st.empty()

                driver = None
                processor = CTeProcessor()

                def _refresh_log():
                    log_placeholder.markdown(
                        '\n'.join([f"[{e['ts']}] {e['msg']}"
                                   for e in st.session_state.ms_logs[-15:]]),
                    )

                try:
                    chrome_version = get_chrome_version()
                    if chrome_version:
                        add_ms_log(f"📊 Versão do navegador: {chrome_version}", 'info')

                    add_ms_log("🌐 Iniciando Chrome em modo headless...", 'info')
                    driver = get_driver(dl_path)
                    _refresh_log()

                    status_box.info("🔑 Autenticando no MasterSAF...")
                    add_ms_log("🔗 Acessando https://p.dfe.mastersaf.com.br/mvc/login", 'info')
                    driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
                    time.sleep(3)

                    driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
                    driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="enter"]'))
                    time.sleep(5)
                    add_ms_log("✅ Login realizado com sucesso", 'ok')
                    progress_bar.progress(0.05)
                    _refresh_log()

                    status_box.info("📋 Navegando até Listagem de CT-es...")
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
                    time.sleep(5)
                    add_ms_log("📋 Módulo Listagem Receptor CT-es acessado", 'info')
                    progress_bar.progress(0.08)
                    _refresh_log()

                    add_ms_log(f"📅 Definindo período: {data_ini} → {data_fin}", 'info')
                    for xpath, val in [
                        ('//*[@id="consultaDataInicial"]', data_ini),
                        ('//*[@id="consultaDataFinal"]',   data_fin),
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
                    _refresh_log()

                    add_ms_log("⚙️ Configurando 200 itens por página...", 'info')
                    sel = driver.find_element(
                        By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
                    sel.click()
                    time.sleep(1)
                    sel.find_element(By.XPATH, './/option[@value="200"]').click()
                    time.sleep(3)
                    progress_bar.progress(0.15)
                    _refresh_log()

                    add_ms_log(f"📥 Loop de download iniciado — {int(qtd_loops)} página(s)", 'info')
                    _refresh_log()

                    for i in range(int(qtd_loops)):
                        add_ms_log(f"━━ Página {i + 1} / {int(qtd_loops)}", 'info')
                        _refresh_log()

                        try:
                            cb = driver.find_element(
                                By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                            if not cb.is_selected():
                                cb.click()
                            time.sleep(2)
                        except Exception:
                            add_ms_log("   ⚠  Não foi possível marcar checkboxes", 'warn')

                        try:
                            driver.execute_script("arguments[0].click();",
                                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                            time.sleep(2)
                            driver.execute_script("arguments[0].click();",
                                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                        except Exception:
                            add_ms_log("   ⚠  Botão de download em massa não encontrado", 'warn')

                        add_ms_log("   ⏳ Aguardando download finalizar...", 'info')
                        _refresh_log()
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
                                add_ms_log("   ⚠  Fim das páginas disponíveis", 'warn')
                                break

                        pct = 0.15 + ((i + 1) / int(qtd_loops)) * 0.60
                        progress_bar.progress(pct)
                        status_box.info(
                            f"⏳ Baixando XMLs — {i + 1} de {int(qtd_loops)} páginas concluídas...")

                    add_ms_log("✅ Todos os downloads concluídos", 'ok')
                    driver.quit()
                    driver = None
                    progress_bar.progress(0.78)
                    _refresh_log()

                    zip_found = list(Path(dl_path).glob('*.zip'))
                    add_ms_log(f"🔍 {len(zip_found)} arquivo(s) ZIP localizado(s)", 'info')
                    _refresh_log()

                    if gerar_excel and zip_found:
                        status_box.info("📊 Processando XMLs e montando Excel...")
                        processor.process_directory(dl_path, add_ms_log)
                        add_ms_log(f"📊 CT-es identificados: {len(processor.processed_data)}", 'ok')
                    progress_bar.progress(0.92)
                    _refresh_log()

                    st.session_state.ms_processed_data = processor.processed_data.copy()

                    zip_buf = None
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
                    _refresh_log()

                    shutil.rmtree(dl_path, ignore_errors=True)

                    if processor.processed_data:
                        summ = processor.summary()
                        ph('<div style="margin-top:1.5rem;"></div>')
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
                    _refresh_log()
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                    if dl_path and os.path.exists(dl_path):
                        shutil.rmtree(dl_path, ignore_errors=True)

    # ════════════════════════════════════════════════════════════
    # TAB RESULTADOS
    # ════════════════════════════════════════════════════════════
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
            pf = (
                st.slider("Faixa de Peso (kg)", pmin, pmax, (pmin, pmax),
                          format="%.1f kg", key="ms_peso_range")
                if pmin < pmax else (pmin, pmax)
            )

            fdf = df.copy()
            if uf_f:   fdf = fdf[fdf['UF Inicio'].isin(uf_f)]
            if uf_d:   fdf = fdf[fdf['UF Destino'].isin(uf_d)]
            if emit_f: fdf = fdf[fdf['Emitente'].isin(emit_f)]
            fdf = fdf[(fdf['Peso Bruto (kg)'] >= pf[0]) & (fdf['Peso Bruto (kg)'] <= pf[1])]

            section_title("📊 Métricas")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Valor Total",    f"R$ {fdf['Valor Prestacao'].sum():,.2f}")
            m2.metric("⚖️ Peso Total",     f"{fdf['Peso Bruto (kg)'].sum():,.2f} kg")
            m3.metric("📈 Peso Médio",     f"{fdf['Peso Bruto (kg)'].mean():,.2f} kg")
            m4.metric("📋 CT-es",          len(fdf))

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
                    fig.update_layout(margin=dict(t=38,b=8,l=8,r=8))
                    st.plotly_chart(fig, **_WS)
            with g2:
                if not fdf.empty:
                    fig2 = px.scatter(fdf, x='Peso Bruto (kg)', y='Valor Prestacao',
                                      color='UF Destino',
                                      title="Peso vs Valor Prestação",
                                      color_discrete_sequence=px.colors.qualitative.Set2)
                    try:
                        x = fdf['Peso Bruto (kg)'].values
                        y = fdf['Valor Prestacao'].values
                        mask = ~np.isnan(x) & ~np.isnan(y)
                        xc, yc = x[mask], y[mask]
                        if len(xc) > 1:
                            xs = np.linspace(xc.min(), xc.max(), 100)
                            fig2.add_trace(go.Scatter(
                                x=xs, y=np.poly1d(np.polyfit(xc, yc, 1))(xs),
                                mode='lines', name='Tendência',
                                line=dict(color='#EF4444', dash='dash'), opacity=.7))
                    except Exception:
                        pass
                    fig2.update_layout(margin=dict(t=38,b=8,l=8,r=8),
                                       legend=dict(orientation="h", y=-0.22))
                    st.plotly_chart(fig2, **_WS)
        else:
            empty_state("📊", "Nenhum CT-e processado ainda",
                        "Execute a automação na aba 'Executar Automação' para ver os resultados")

    # ════════════════════════════════════════════════════════════
    # TAB EXPORTAR
    # ════════════════════════════════════════════════════════════
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
                out = BytesIO()
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
                    "📥  Download ZIP — XMLs brutos",
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
# PARTE 3 — PARSER EXTRATO DUIMP (HafelePDFParser)
# ==============================================================================
class HafelePDFParser:
    """
    Parser para o layout Extrato DUIMP (APP2 original).
    Processa em lotes de _PDF_CHUNK_PAGES páginas.
    Buffer residual limitado a _MAX_BUF_CHARS para evitar OOM.
    """
    _MAX_BUF_CHARS = 500_000  # ~500KB de texto — suficiente para qualquer item

    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}
        self._buffer   = ""

    @staticmethod
    def _parse_valor(v: str) -> float:
        try:
            return float(v.strip().replace('.','').replace(',','.')) if v else 0.0
        except Exception:
            return 0.0

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
                    prog_txt.text(
                        f"Processando páginas {start+1}–{end} de {total} "
                        f"(Extrato DUIMP)... {int((end/total)*100)}%"
                    )
                    prog_bar.progress(end / total)

                    chunk_lines = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_lines.append(t)

                    chunk_text = self._buffer + "\n".join(chunk_lines)
                    del chunk_lines

                    is_last = (end == total)
                    new_items, self._buffer = self._extract_items_from_chunk(
                        chunk_text, is_last=is_last
                    )
                    items_found.extend(new_items)
                    del chunk_text, new_items

                    # Proteção OOM: buffer residual não pode crescer infinitamente
                    if len(self._buffer) > self._MAX_BUF_CHARS:
                        # Mantém apenas os últimos MAX_BUF_CHARS (dados recentes)
                        self._buffer = self._buffer[-self._MAX_BUF_CHARS:]

                    gc.collect()

            prog_txt.empty()
            prog_bar.empty()

            if self._buffer.strip():
                new_items, _ = self._extract_items_from_chunk(self._buffer, is_last=True)
                items_found.extend(new_items)

            self._buffer = ""
            gc.collect()

            if not items_found:
                st.warning("⚠️ Padrão 'ITENS DA DUIMP' não encontrado. Verifique o formato do PDF.")

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
            header  = parts[i]
            content = parts[i+1] if (i+1) < len(parts) else ''
            m = re.search(r'(\d+)', header)
            num = int(m.group(1)) if m else (i // 2)
            item = self._parse_item_block(num, content)
            if item:
                items_found.append(item)

        if not is_last and len(parts) >= 2:
            last_header  = parts[-2] if len(parts) % 2 == 0 else ""
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
                item['local_aduaneiro']    = pv(m.group(1))
                item['aduaneiro_reais']    = item['local_aduaneiro']
                item['valorAduaneiroReal'] = item['local_aduaneiro']
            tax_pats = re.findall(
                r'Base de Cálculo.*?\(R\$\)\s*([\d\.,]+).*?% Alíquota\s*([\d\.,]+)'
                r'.*?Valor.*?(?:Devido|A Recolher|Calculado).*?\(R\$\)\s*([\d\.,]+)',
                text, re.DOTALL | re.IGNORECASE)
            for base_s, aliq_s, val_s in tax_pats:
                base = pv(base_s); aliq = pv(aliq_s); val = pv(val_s)
                if 1.60<=aliq<=3.00:
                    item['pis_aliquota']=aliq; item['pis_base_calculo']=base; item['pis_valor_devido']=val
                elif 7.00<=aliq<=12.00:
                    item['cofins_aliquota']=aliq; item['cofins_base_calculo']=base; item['cofins_valor_devido']=val
                elif aliq>12.00:
                    item['ii_aliquota']=aliq; item['ii_base_calculo']=base; item['ii_valor_devido']=val
                elif aliq>=0 and item['ipi_aliquota']==0:
                    item['ipi_aliquota']=aliq; item['ipi_base_calculo']=base; item['ipi_valor_devido']=val
            item['total_impostos'] = (
                item['ii_valor_devido'] + item['ipi_valor_devido']
                + item['pis_valor_devido'] + item['cofins_valor_devido']
            )
            item['valor_total_com_impostos'] = item['valor_total'] + item['total_impostos']
            return item
        except Exception as e:
            logger.error(f"Erro item {item_num}: {e}")
            return None

    def _calculate_totals(self):
        if self.documento['itens']:
            itens = self.documento['itens']
            self.documento['totais'] = {
                'valor_total_mercadoria': sum(i['valor_total'] for i in itens),
                'total_valor_aduaneiro':  sum(i.get('aduaneiro_reais',0) for i in itens),
                'total_ii':     sum(i['ii_valor_devido'] for i in itens),
                'total_ipi':    sum(i['ipi_valor_devido'] for i in itens),
                'total_pis':    sum(i['pis_valor_devido'] for i in itens),
                'total_cofins': sum(i['cofins_valor_devido'] for i in itens),
                'total_frete':  sum(i['frete_internacional'] for i in itens),
                'total_seguro': sum(i['seguro_internacional'] for i in itens),
                'quantidade_adicoes': len(itens),
            }


# ==============================================================================
# PARTE 3B — PARSER SIGRAWEB (layout novo)
# ==============================================================================
class SigrawebPDFParser:
    """
    Parser para o layout Sigraweb — Conferência do Processo Detalhado.
    Processa em lotes de _PDF_CHUNK_PAGES páginas.
    """

    def __init__(self):
        self.documento = {'cabecalho': {}, 'itens': [], 'totais': {}}

    @staticmethod
    def _parse_valor(v: str) -> float:
        try:
            return float(str(v).strip().replace('.','').replace(',','.')) if v else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _fmt_date(d: str) -> str:
        try:
            return datetime.strptime(d.strip(), '%d/%m/%Y').strftime('%Y%m%d')
        except Exception:
            return d.replace('/','').replace('-','')[:8]

    _MAX_BUF_CHARS = 500_000  # ~500KB — proteção OOM

    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            prog_txt = st.empty()
            prog_bar = st.progress(0)
            items_found: list = []
            buffer = ""

            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                chunk = _PDF_CHUNK_PAGES

                p1 = pdf.pages[0].extract_text(layout=False) or "" if total > 0 else ""
                p2 = pdf.pages[1].extract_text(layout=False) or "" if total > 1 else ""
                self._extract_header(p1, p2)
                del p1, p2

                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(
                        f"Processando páginas {start+1}–{end} de {total} "
                        f"(Sigraweb)... {int((end/total)*100)}%"
                    )
                    prog_bar.progress(end / total)

                    chunk_pages = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_pages.append(t)

                    chunk_text = buffer + "\n".join(chunk_pages)
                    del chunk_pages

                    is_last    = (end == total)
                    new_items, buffer = self._extract_items_from_chunk(
                        chunk_text, is_last=is_last
                    )
                    items_found.extend(new_items)
                    del chunk_text, new_items

                    # Proteção OOM: buffer residual não pode crescer infinitamente
                    if len(buffer) > self._MAX_BUF_CHARS:
                        buffer = buffer[-self._MAX_BUF_CHARS:]

                    gc.collect()

            prog_txt.empty()
            prog_bar.empty()

            if buffer.strip():
                new_items, _ = self._extract_items_from_chunk(buffer, is_last=True)
                items_found.extend(new_items)

            buffer = ""
            gc.collect()

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
        parts   = re.split(pattern, text)
        items_found = []

        if len(parts) <= 1:
            return items_found, (text if not is_last else "")

        n_complete = len(parts) - 1 if not is_last else len(parts)

        for i in range(1, n_complete, 2):
            num_str = parts[i].strip()
            content = parts[i+1] if (i+1) < len(parts) else ''
            item    = self._parse_item_block(num_str, content)
            if item:
                items_found.append(item)

        if not is_last and len(parts) >= 2:
            last_num     = parts[-2] if len(parts) % 2 == 0 else ""
            last_content = parts[-1]
            residual = (f"Informações da Adição Nº: {last_num}\n"
                        if last_num else "") + last_content
        else:
            residual = ""

        return items_found, residual

    def _extract_header(self, p1: str, p2: str):
        def _f(pat, text, default=''):
            m = re.search(pat, text)
            return m.group(1).strip() if m else default
        h = {}
        h['numeroDI']       = _f(r'Número DI:\s*([\w]+)', p1)
        h['sigraweb']       = _f(r'SIGRAWEB:\s*([\w]+)', p1)
        h['cnpj']           = _f(r'CNPJ:\s*([\d\.\/\-]+)', p1)
        h['nomeImportador'] = _f(r'Nome da Empresa:\s*(.+?)(?:\n|CNPJ)', p1)
        dr = _f(r'Data Registro:([\d\-T:\.+]+)', p1)
        h['dataRegistro']   = dr[:10].replace('-','') if dr else ''
        h['pesoBruto']      = _f(r'Peso Bruto:([\d\.,]+)', p1)
        h['pesoLiquido']    = _f(r'Peso Líquido:([\d\.,]+)', p1)
        h['volumes']        = _f(r'Volumes:([\d]+)', p1)
        h['embalagem']      = _f(r'Embalagem:(\w+)', p1)
        h['urf']            = _f(r'URF de Entrada:\s*(\d+)', p1, '0917900')
        h['urfDespacho']    = _f(r'URF de Despacho:\s*(\d+)', p1, '0917900')
        h['modalidade']     = _f(r'Modalidade de Despacho:\s*(.+?)(?:\n)', p1, 'Normal')
        h['viaTransporte']  = _f(r'Via Transporte:\s*(.+?)(?:\n)', p1, 'Aéreo')
        pais_raw = _f(r'País de Procedência:\s*\d+\s*(.+?)(?:\n|Local|Incoterms)', p1)
        h['paisProcedencia']= pais_raw.strip() if pais_raw else 'Alemanha'
        h['localEmbarque']  = _f(r'Local de Embarque:\s*(.+?)(?:\n|Data)', p1)
        h['dataEmbarque']   = _f(r'Data de Embarque:\s*([\d\/]+)', p1)
        h['dataChegada']    = _f(r'Data de Chegada no Brasil:\s*([\d\/]+)', p1)
        h['incoterms']      = _f(r'Incoterms:\s*(\w+)', p1, 'FCA')
        h['idtConhecimento']= _f(r'IDT\. Conhecimento:\s*([\w]+)', p1)
        h['idtMaster']      = _f(r'IDT\. Master:\s*([\w]+)', p1)
        h['transportador']  = _f(r'Transportador:\s*(.+?)(?:\n|Agente)', p1)
        h['agenteCarga']    = _f(r'Agente de Carga:\s*(.+?)(?:\n|CE)', p1)
        combined = p1 + "\n" + p2
        h['taxaEUR']  = _f(r'Taxa EUR:\s*([\d\.,]+)', combined)
        h['taxaDolar']= _f(r'Taxa do Dólar:\s*([\d\.,]+)', combined)
        h['fobEUR']   = _f(r'FOB:\s*([\d\.,]+)\s*\(EUR\)', combined)
        h['fobUSD']   = _f(r'FOB:.*?\(EUR\)\s*;\s*([\d\.,]+)\s*\(USD\)', combined)
        h['fobBRL']   = _f(r'FOB:.*?\(USD\);\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['freteEUR'] = _f(r'Frete:\s*([\d\.,]+)\s*\(EUR\)', combined)
        h['freteUSD'] = _f(r'Frete:.*?\(EUR\)\s*;\s*([\d\.,]+)\s*\(USD\)', combined)
        h['freteBRL'] = _f(r'Frete:.*?\(USD\);\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['seguroUSD']= _f(r'Seguro:\s*([\d\.,]+)\s*\(USD\)', combined)
        h['seguroBRL']= _f(r'Seguro:.*?;\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['cifUSD']   = _f(r'CIF:\s*([\d\.,]+)\s*\(USD\)', combined)
        h['cifBRL']   = _f(r'CIF:.*?;\s*([\d\.,]+)\s*\(BRL\)', combined)
        h['valorAduaneiroUSD'] = _f(r'Valor Aduaneiro:\s*([\d\.,]+)\s*\(USD\)', combined)
        h['valorAduaneiroBRL'] = _f(r'Valor Aduaneiro:.*?;\s*([\d\.,]+)\s*\(BRL\)', combined)
        tm = re.search(
            r'([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)'
            r'\s+Itau\s+(\d+)\s+([\d\-]+)',
            p1)
        if tm:
            h['totalII']=tm.group(1); h['totalIPI']=tm.group(2)
            h['totalPIS']=tm.group(3); h['totalCOFINS']=tm.group(4)
            h['totalSiscomex']=tm.group(5); h['banco']='Itau'
            h['agencia']=tm.group(6); h['conta']=tm.group(7)
        else:
            h['totalII']=h['totalIPI']=h['totalPIS']=h['totalCOFINS']='0'
            h['totalSiscomex']='0'
            h['banco']  = _f(r'Banco:\s*(\w+)', p2, 'Itau')
            h['agencia']= _f(r'Agência:\s*([\d]+)', p2, '3715')
            h['conta']  = _f(r'Conta Corrente:\s*([\w\-]+)', p2, '')
        h['dataEmbarqueISO'] = self._fmt_date(h['dataEmbarque']) if h['dataEmbarque'] else ''
        h['dataChegadaISO']  = self._fmt_date(h['dataChegada'])  if h['dataChegada']  else ''
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
            m = re.search(
                r'Part Number:\s*([\S]+)\s*\|\s*Descrição:\s*(.+?)(?=\nFabricante:|$)',
                text, re.DOTALL)
            if m:
                item['codigo_interno'] = m.group(1).strip()
                item['descricao']      = re.sub(r'\s+',' ', m.group(2).strip())
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
                item['aduaneiro_reais']    = pv(m.group(1))
                item['ii_base_calculo']    = pv(m.group(1))
            m = re.search(r'Valor Frete:\s*([\d\.,]+)\s+USD', text)
            if m: item['freteUSD'] = pv(m.group(1))
            m = re.search(r'Valor Frete Real:\s*([\d\.,]+)', text)
            if m:
                item['freteReal'] = pv(m.group(1))
                item['frete_internacional'] = item['freteReal']
            m = re.search(r'Valor Seguro:\s*([\d\.,]+)\s+USD', text)
            if m: item['seguroUSD'] = pv(m.group(1))
            m = re.search(r'Valor Seguro Real:\s*([\d\.,]+)', text)
            if m:
                item['seguroReal'] = pv(m.group(1))
                item['seguro_internacional'] = item['seguroReal']
            m = re.search(r'Moeda LI:\s*(.+?)(?:\n|Valor)', text)
            if m: item['moeda'] = m.group(1).strip()
            m = re.search(r'País Origem:\s*(.+?)(?:\n|Fabricante)', text)
            if m: item['paisOrigem'] = m.group(1).strip()
            m = re.search(r'Fornecedor:\s*(.+?)(?:\n|País)', text)
            if m: item['fornecedor_raw'] = m.group(1).strip()
            m = re.search(
                r'^II\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+'
                r'([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m:
                item['ii_aliquota']=pv(m.group(1))
                item['ii_base_calculo']=pv(m.group(2))
                item['ii_valor_devido']=pv(m.group(3))
            m = re.search(
                r'^IPI\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+'
                r'([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m:
                item['ipi_aliquota']=pv(m.group(1))
                item['ipi_base_calculo']=pv(m.group(2))
                item['ipi_valor_devido']=pv(m.group(3))
            m = re.search(
                r'^PIS\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+'
                r'([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m:
                item['pis_aliquota']=pv(m.group(1))
                item['pis_base_calculo']=pv(m.group(2))
                item['pis_valor_devido']=pv(m.group(3))
            m = re.search(
                r'^COFINS\s+([\d\.,]+)\s+[\d\.,]+\s+[\d\.,]+\s+[\d\.,]+\s+'
                r'([\d\.,]+)\s+([\d\.,]+)', text, re.MULTILINE)
            if m:
                item['cofins_aliquota']=pv(m.group(1))
                item['cofins_base_calculo']=pv(m.group(2))
                item['cofins_valor_devido']=pv(m.group(3))
            item['total_impostos'] = (
                item['ii_valor_devido'] + item['ipi_valor_devido']
                + item['pis_valor_devido'] + item['cofins_valor_devido']
            )
            item['valor_total_com_impostos'] = (
                pv(str(item['valorTotal'])) + item['total_impostos']
            )
            return item
        except Exception as e:
            logger.error(f"Erro item {num_str}: {e}")
            return None

    def _calculate_totals(self):
        if self.documento['itens']:
            pv = self._parse_valor
            itens = self.documento['itens']
            self.documento['totais'] = {
                'valor_total_fob':       sum(pv(str(i.get('valorTotal',0))) for i in itens),
                'peso_liquido_total':    sum(pv(str(i.get('pesoLiq',0))) for i in itens),
                'total_valor_aduaneiro': sum(i.get('aduaneiro_reais',0) for i in itens),
                'total_ii':    sum(i.get('ii_valor_devido',0) for i in itens),
                'total_ipi':   sum(i.get('ipi_valor_devido',0) for i in itens),
                'total_pis':   sum(i.get('pis_valor_devido',0) for i in itens),
                'total_cofins':sum(i.get('cofins_valor_devido',0) for i in itens),
                'total_frete': sum(i.get('frete_internacional',0) for i in itens),
                'total_seguro':sum(i.get('seguro_internacional',0) for i in itens),
                'quantidade_adicoes': len(itens),
            }


# ==============================================================================
# PARTE 4 — montar_descricao_final + DuimpPDFParser
# ==============================================================================
def montar_descricao_final(desc_complementar, codigo_extra, detalhamento):
    return f"{str(desc_complementar).strip()} - {str(codigo_extra).strip()} - {str(detalhamento).strip()}"


class DuimpPDFParser:
    """
    Parser de DUIMP com processamento STREAMING — nunca acumula o texto
    completo na memória. Extrai cabeçalho e itens página a página,
    mantendo apenas um buffer residual mínimo entre chunks.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        # full_text REMOVIDO — substituído por processamento streaming
        self.header   = {}
        self.items    = []
        # Buffer interno usado APENAS durante parse (liberado ao final)
        self._buf     = ""

    # ------------------------------------------------------------------
    # Filtra uma linha do PDF (remove ruído de paginação)
    # ------------------------------------------------------------------
    @staticmethod
    def _filter(line: str) -> bool:
        ls = line.strip()
        if not ls:                                      return False
        if "Extrato da DUIMP" in ls:                   return False
        if "Data, hora e responsável" in ls:           return False
        if re.match(r'^\d+\s*/\s*\d+$', ls):          return False
        return True

    # ------------------------------------------------------------------
    # preprocess() + extract_header() + extract_items() fundidos em um
    # único passo streaming — lê, filtra, extrai e descarta por chunk.
    # ------------------------------------------------------------------
    def preprocess(self):
        """
        Lê o PDF em blocos de _PDF_CHUNK_PAGES páginas.
        Extrai cabeçalho das primeiras páginas e itens incrementalmente.
        NUNCA mantém o texto completo em memória simultaneamente.
        """
        prog_txt = st.empty()
        prog_bar = st.progress(0)
        doc      = fitz.open(self.pdf_path)
        total    = doc.page_count
        self._buf = ""

        for start in range(0, total, _PDF_CHUNK_PAGES):
            end = min(start + _PDF_CHUNK_PAGES, total)
            prog_txt.text(f"Processando páginas {start+1}–{end} de {total} (DUIMP)...")
            prog_bar.progress(end / total)

            # Extrai texto do chunk e filtra linhas de ruído
            lines = []
            for idx in range(start, end):
                page = doc[idx]
                for line in page.get_text("text").split('\n'):
                    if self._filter(line):
                        lines.append(line)
                page = None   # libera objeto página imediatamente

            chunk_text = "\n".join(lines)
            del lines
            gc.collect()

            # Extrai cabeçalho apenas das primeiras páginas (chunk 0)
            if start == 0 and not self.header:
                self._extract_header_from_chunk(chunk_text)

            # Extrai itens incrementalmente com buffer residual
            self._buf, new_items = self._extract_items_streaming(
                self._buf + chunk_text, is_last=(end == total)
            )
            self.items.extend(new_items)

            del chunk_text
            gc.collect()

        doc.close()
        prog_txt.empty()
        prog_bar.empty()

        # Processa qualquer residual final
        if self._buf.strip():
            _, remaining = self._extract_items_streaming(self._buf, is_last=True)
            self.items.extend(remaining)

        self._buf = ""  # libera buffer
        gc.collect()

    def extract_header(self):
        """Compatibilidade — cabeçalho já extraído em preprocess()."""
        pass  # já feito no streaming

    def extract_items(self):
        """Compatibilidade — itens já extraídos em preprocess()."""
        pass  # já feito no streaming

    # ------------------------------------------------------------------
    # Extração de cabeçalho a partir de um bloco de texto
    # ------------------------------------------------------------------
    def _extract_header_from_chunk(self, text: str):
        self.header["numeroDUIMP"]    = self._r(r"Extrato da Duimp\s+([\w\-\/]+)", text)
        self.header["cnpj"]           = self._r(r"CNPJ do importador:\s*([\d\.\/\-]+)", text)
        self.header["nomeImportador"] = self._r(r"Nome do importador:\s*\n?(.+)", text)
        self.header["pesoBruto"]      = self._r(r"Peso Bruto \(kg\):\s*([\d\.,]+)", text)
        self.header["pesoLiquido"]    = self._r(r"Peso Liquido \(kg\):\s*([\d\.,]+)", text)
        self.header["urf"]            = self._r(r"Unidade de despacho:\s*([\d]+)", text)
        self.header["paisProcedencia"]= self._r(r"País de Procedência:\s*\n?(.+)", text)

    # ------------------------------------------------------------------
    # Extração streaming de itens — retorna (buffer_residual, [itens])
    # ------------------------------------------------------------------
    def _extract_items_streaming(self, text: str, is_last: bool):
        """
        Divide o texto pelo padrão 'Item N', processa os blocos completos
        e retorna o bloco final incompleto como buffer para o próximo chunk.
        Nunca guarda mais do que um bloco de item por vez na memória.
        """
        parts = re.split(r"Item\s+(\d+)", text)
        items_found = []

        if len(parts) <= 1:
            residual = "" if is_last else text
            return residual, items_found

        # Quantos blocos podemos processar com segurança
        # Se não é último chunk, o último bloco pode estar incompleto
        n_safe = len(parts) - 1 if not is_last else len(parts)

        for i in range(1, n_safe, 2):
            num     = parts[i]
            content = parts[i + 1] if (i + 1) < len(parts) else ""
            item    = self._parse_item_block(num, content)
            if item:
                items_found.append(item)
            # Libera conteúdo do bloco imediatamente após parsear
            parts[i + 1] = ""

        # Buffer residual = último bloco incompleto
        if not is_last and len(parts) >= 2:
            last_num     = parts[-2] if len(parts) % 2 == 0 else ""
            last_content = parts[-1]
            residual = (f"Item {last_num}\n" if last_num else "") + last_content
        else:
            residual = ""

        del parts
        return residual, items_found

    # ------------------------------------------------------------------
    # Parseia um bloco de item individual
    # ------------------------------------------------------------------
    def _parse_item_block(self, num: str, content: str) -> Optional[Dict]:
        item = {"numeroAdicao": num.strip()}
        item["ncm"]                  = self._r(r"NCM:\s*([\d\.]+)", content)
        item["paisOrigem"]           = self._r(r"País de origem:\s*\n?(.+)", content)
        item["quantidade"]           = self._r(r"Quantidade na unidade estatística:\s*([\d\.,]+)", content)
        item["quantidade_comercial"] = self._r(r"Quantidade na unidade comercializada:\s*([\d\.,]+)", content)
        item["unidade"]              = self._r(r"Unidade estatística:\s*(.+)", content)
        item["pesoLiq"]              = self._r(r"Peso líquido \(kg\):\s*([\d\.,]+)", content)
        item["valorUnit"]            = self._r(r"Valor unitário na condição de venda:\s*([\d\.,]+)", content)
        item["valorTotal"]           = self._r(r"Valor total na condição de venda:\s*([\d\.,]+)", content)
        item["moeda"]                = self._r(r"Moeda negociada:\s*(.+)", content)
        m = re.search(r"Código do Exportador Estrangeiro:\s*(.+?)(?=\n\s*(?:Endereço|Dados))",
                      content, re.DOTALL)
        item["fornecedor_raw"] = m.group(1).strip() if m else ""
        m = re.search(r"Endereço:\s*(.+?)(?=\n\s*(?:Dados da Mercadoria|Aplicação))",
                      content, re.DOTALL)
        item["endereco_raw"] = m.group(1).strip() if m else ""
        m = re.search(r"Detalhamento do Produto:\s*(.+?)"
                      r"(?=\n\s*(?:Número de Identificação|Versão|Código de Class|Descrição complementar))",
                      content, re.DOTALL)
        item["descricao"] = m.group(1).strip() if m else ""
        m = re.search(r"Descrição complementar da mercadoria:\s*(.+?)(?=\n|$)",
                      content, re.DOTALL)
        item["desc_complementar"] = m.group(1).strip() if m else ""
        return item

    def _r(self, pat, text):
        m = re.search(pat, text)
        return m.group(1).strip() if m else ""


# ==============================================================================
# PARTE 5 — ADICAO_FIELDS_ORDER, FOOTER_TAGS, DataFormatter, XMLBuilder
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
            if isinstance(value, str):
                value = value.replace('.','').replace(',','.')
            return str(int(round(float(value)*100))).zfill(length)
        except Exception:
            return "0"*length

    @staticmethod
    def format_high_precision(value, length=15):
        try:
            if isinstance(value, str):
                value = value.replace('.','').replace(',','.')
            return str(int(round(float(value)*10000000))).zfill(length)
        except Exception:
            return "0"*length

    @staticmethod
    def format_quantity(value, length=14):
        try:
            if isinstance(value, str):
                value = value.replace('.','').replace(',','.')
            return str(int(round(float(value)*100000))).zfill(length)
        except Exception:
            return "0"*length

    @staticmethod
    def calculate_cbs_ibs(base_xml_string):
        try:
            bf  = int(base_xml_string)/100.0
            cbs = str(int(round(bf*0.009*100))).zfill(14)
            ibs = str(int(round(bf*0.001*100))).zfill(14)
            return cbs, ibs
        except Exception:
            return "0".zfill(14), "0".zfill(14)

    @staticmethod
    def parse_supplier_info(raw_name, raw_addr):
        data = {"fornecedorNome":"","fornecedorLogradouro":"","fornecedorNumero":"S/N","fornecedorCidade":""}
        if raw_name:
            parts = raw_name.split('-',1)
            data["fornecedorNome"] = parts[-1].strip() if len(parts)>1 else raw_name.strip()
        if raw_addr:
            ca  = DataFormatter.clean_text(raw_addr)
            pd_ = ca.rsplit('-',1)
            if len(pd_)>1:
                data["fornecedorCidade"] = pd_[1].strip()
                street = pd_[0].strip()
            else:
                data["fornecedorCidade"] = "EXTERIOR"
                street = ca
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
        self.root  = etree.Element("ListaDeclaracoes")
        self.duimp = etree.SubElement(self.root, "duimp")

    def build(self, user_inputs=None):
        h = self.p.header
        duimp_fmt = h.get("numeroDUIMP","").split("/")[0].replace("-","").replace(".","")
        totals = {"frete":0.0,"seguro":0.0,"ii":0.0,"ipi":0.0,"pis":0.0,"cofins":0.0}

        def gf(val):
            try:
                if isinstance(val,str): val=val.replace('.','').replace(',','.')
                return float(val)
            except Exception:
                return 0.0

        for it in self.items_to_use:
            totals["frete"]  += gf(it.get("Frete (R$)"))
            totals["seguro"] += gf(it.get("Seguro (R$)"))
            totals["ii"]     += gf(it.get("II (R$)"))
            totals["ipi"]    += gf(it.get("IPI (R$)"))
            totals["pis"]    += gf(it.get("PIS (R$)"))
            totals["cofins"] += gf(it.get("COFINS (R$)"))

        for it in self.items_to_use:
            adicao = etree.SubElement(self.duimp, "adicao")
            input_number  = str(it.get("NUMBER","")).strip()
            original_desc = DataFormatter.clean_text(it.get("descricao",""))
            desc_compl    = DataFormatter.clean_text(it.get("desc_complementar",""))
            final_desc    = montar_descricao_final(desc_compl, input_number, original_desc)
            vtvf  = DataFormatter.format_high_precision(it.get("valorTotal","0"), 11)
            vuf   = DataFormatter.format_high_precision(it.get("valorUnit","0"), 20)
            qcr   = it.get("quantidade_comercial") or it.get("quantidade")
            qcf   = DataFormatter.format_quantity(qcr, 14)
            qef   = DataFormatter.format_quantity(it.get("quantidade"), 14)
            plf   = DataFormatter.format_quantity(it.get("pesoLiq"), 15)
            btrf  = DataFormatter.format_input_fiscal(it.get("valorTotal","0"), 15)
            rf    = gf(it.get("Frete (R$)",0))
            rs    = gf(it.get("Seguro (R$)",0))
            ra    = gf(it.get("Aduaneiro (R$)",0))
            ff    = DataFormatter.format_input_fiscal(rf)
            sf    = DataFormatter.format_input_fiscal(rs)
            af    = DataFormatter.format_input_fiscal(ra)
            iibf  = DataFormatter.format_input_fiscal(it.get("II Base (R$)",0))
            iiaf  = DataFormatter.format_input_fiscal(it.get("II Alíq. (%)",0),5,True)
            iivf  = DataFormatter.format_input_fiscal(gf(it.get("II (R$)",0)))
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

        pbf  = DataFormatter.format_quantity(h.get("pesoBruto"), 15)
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
            {"code":"0086","val":totals["ii"]},
            {"code":"1038","val":totals["ipi"]},
            {"code":"5602","val":totals["pis"]},
            {"code":"5629","val":totals["cofins"]},
        ]
        if user_inputs and user_inputs.get("valorReceita7811","0") not in ("0","000000000000000"):
            receitas.append({"code":"7811","val":float(user_inputs["valorReceita7811"])})

        for tag, dval in FOOTER_TAGS.items():
            if tag == "embalagem" and user_inputs:
                parent = etree.SubElement(self.duimp, tag)
                for sf in dval:
                    v = (user_inputs.get("quantidadeVolume", sf["default"])
                         if sf["tag"] == "quantidadeVolume" else sf["default"])
                    etree.SubElement(parent, sf["tag"]).text = v
                continue
            if tag == "pagamento":
                agencia = user_inputs.get("agenciaPagamento","3715") if user_inputs else "3715"
                banco   = user_inputs.get("bancoPagamento","341")    if user_inputs else "341"
                for rec in receitas:
                    if rec["val"] > 0:
                        pag = etree.SubElement(self.duimp, "pagamento")
                        etree.SubElement(pag, "agenciaPagamento").text = agencia
                        etree.SubElement(pag, "bancoPagamento").text   = banco
                        etree.SubElement(pag, "codigoReceita").text    = rec["code"]
                        if rec["code"]=="7811" and user_inputs:
                            etree.SubElement(pag, "valorReceita").text = user_inputs["valorReceita7811"].zfill(15)
                        else:
                            etree.SubElement(pag, "valorReceita").text = DataFormatter.format_input_fiscal(rec["val"])
                continue
            if tag in fmap:
                etree.SubElement(self.duimp, tag).text = fmap[tag]
                continue
            if user_inputs and tag in user_inputs:
                etree.SubElement(self.duimp, tag).text = user_inputs[tag]
                continue
            if isinstance(dval, list):
                parent = etree.SubElement(self.duimp, tag)
                for sf in dval:
                    etree.SubElement(parent, sf["tag"]).text = sf["default"]
            elif isinstance(dval, dict):
                parent = etree.SubElement(self.duimp, tag)
                etree.SubElement(parent, dval["tag"]).text = dval["default"]
            else:
                etree.SubElement(self.duimp, tag).text = fmap.get(tag, dval)

        xml_bytes = etree.tostring(self.root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
        return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_bytes


# ==============================================================================
# PARTE 6 — _merge_app2_items + _render_totais_grade
# ==============================================================================
def _merge_app2_items(df_dest: pd.DataFrame, itens: list) -> tuple:
    src_map: Dict[int, Dict] = {}
    for item in itens:
        try:
            src_map[int(item['numero_item'])] = item
        except Exception:
            pass

    count, not_found = 0, []
    for idx, row in df_dest.iterrows():
        try:
            num = int(str(row['numeroAdicao']).strip())
            if num not in src_map:
                not_found.append(num)
                continue
            src = src_map[num]
            df_dest.at[idx,'NUMBER']           = src.get('codigo_interno','')
            df_dest.at[idx,'Frete (R$)']       = src.get('frete_internacional',0.0)
            df_dest.at[idx,'Seguro (R$)']      = src.get('seguro_internacional',0.0)
            df_dest.at[idx,'Aduaneiro (R$)']   = src.get('aduaneiro_reais',
                                                   src.get('valorAduaneiroReal',
                                                   src.get('local_aduaneiro',0.0)))
            df_dest.at[idx,'II (R$)']          = src.get('ii_valor_devido',0.0)
            df_dest.at[idx,'II Base (R$)']     = src.get('ii_base_calculo',
                                                   src.get('aduaneiro_reais',
                                                   src.get('valorAduaneiroReal',0.0)))
            df_dest.at[idx,'II Alíq. (%)']     = src.get('ii_aliquota',0.0)
            df_dest.at[idx,'IPI (R$)']         = src.get('ipi_valor_devido',0.0)
            df_dest.at[idx,'IPI Base (R$)']    = src.get('ipi_base_calculo',0.0)
            df_dest.at[idx,'IPI Alíq. (%)']    = src.get('ipi_aliquota',0.0)
            df_dest.at[idx,'PIS (R$)']         = src.get('pis_valor_devido',0.0)
            df_dest.at[idx,'PIS Base (R$)']    = src.get('pis_base_calculo',0.0)
            df_dest.at[idx,'PIS Alíq. (%)']    = src.get('pis_aliquota',0.0)
            df_dest.at[idx,'COFINS (R$)']      = src.get('cofins_valor_devido',0.0)
            df_dest.at[idx,'COFINS Base (R$)'] = src.get('cofins_base_calculo',0.0)
            df_dest.at[idx,'COFINS Alíq. (%)'] = src.get('cofins_aliquota',0.0)
            count += 1
        except Exception:
            continue
    return df_dest, count, not_found


def _render_totais_grade(df: pd.DataFrame):
    def _s(col):
        return pd.to_numeric(df[col], errors='coerce').sum() if col in df.columns else 0
    t1,t2,t3,t4,t5,t6 = st.columns(6)
    t1.metric("II Total",     f"R$ {_s('II (R$)'):,.2f}")
    t2.metric("IPI Total",    f"R$ {_s('IPI (R$)'):,.2f}")
    t3.metric("PIS Total",    f"R$ {_s('PIS (R$)'):,.2f}")
    t4.metric("COFINS Total", f"R$ {_s('COFINS (R$)'):,.2f}")
    t5.metric("Frete Total",  f"R$ {_s('Frete (R$)'):,.2f}")
    t6.metric("Seguro Total", f"R$ {_s('Seguro (R$)'):,.2f}")


# ==============================================================================
# PARTE 7 — SISTEMA INTEGRADO DUIMP
# ==============================================================================
def sistema_integrado_duimp():
    page_header("📊", "Sistema Integrado DUIMP 2026",
                "Upload · Vinculação · Conferência · Geração de XML 8686")

    tab_up, tab_conf, tab_xml = st.tabs([
        "📂  Upload & Vinculação",
        "📋  Conferência",
        "💾  Exportar XML",
    ])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1 — UPLOAD & VINCULAÇÃO
    # ══════════════════════════════════════════════════════════════════════
    with tab_up:
        section_title("⚙️ Formato do Arquivo de Tributos (APP2)")
        col_radio, col_badge = st.columns([3, 1], gap="large")

        with col_radio:
            layout_choice = st.radio(
                "Selecione o layout do APP2",
                options=[
                    "🔵  Sigraweb — Conferência do Processo Detalhado (layout novo)",
                    "🟠  Extrato DUIMP — Itens da DUIMP (layout antigo)",
                ],
                index=0 if st.session_state["layout_app2"] == "sigraweb" else 1,
                key="layout_radio",
                horizontal=False,
            )
            novo = "sigraweb" if layout_choice.startswith("🔵") else "extrato_duimp"
            if novo != st.session_state["layout_app2"]:
                st.session_state["layout_app2"]     = novo
                st.session_state["parsed_sigraweb"] = None
                st.session_state["merged_df"]       = None
                st.rerun()

        with col_badge:
            is_sgw = st.session_state["layout_app2"] == "sigraweb"
            bc  = "lbadge" if is_sgw else "lbadge amber"
            btx = "🔵 Sigraweb (ativo)" if is_sgw else "🟠 Extrato DUIMP (ativo)"
            ph(f'<div class="{bc}">{btx}</div>')

        st.divider()
        section_title("📂 Carregar Arquivos")
        c1, c2 = st.columns(2, gap="large")

        with c1:
            ph("""<div class="uzone">
                <div class="uzone-icon">📄</div>
                <div class="uzone-title">Passo 1 — Extrato DUIMP</div>
                <div class="uzone-sub">Siscomex · PDF</div></div>""")
            file_duimp = st.file_uploader("Arquivo DUIMP (PDF)", type="pdf", key="u1")

        with c2:
            lbl2 = "Sigraweb · Conferência Detalhada" if is_sgw else "Extrato DUIMP · Itens"
            ph(f"""<div class="uzone">
                <div class="uzone-icon">📑</div>
                <div class="uzone-title">Passo 2 — {lbl2}</div>
                <div class="uzone-sub">PDF</div></div>""")
            key2  = "Arquivo Sigraweb (PDF)" if is_sgw else "Arquivo Extrato DUIMP (PDF)"
            file_app2 = st.file_uploader(key2, type="pdf", key="u2")

        if file_duimp:
            if (st.session_state["parsed_duimp"] is None or
                    file_duimp.name != getattr(st.session_state.get("last_duimp"), "name", "")):
                _td_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as _td:
                        _td.write(file_duimp.read())
                        _td_path = _td.name
                    p = DuimpPDFParser(_td_path)
                    p.preprocess(); p.extract_header(); p.extract_items()
                    st.session_state["parsed_duimp"] = p
                    st.session_state["last_duimp"]   = file_duimp
                    df = pd.DataFrame(p.items)
                    for col in ["NUMBER","Frete (R$)","Seguro (R$)",
                                "II (R$)","II Base (R$)","II Alíq. (%)",
                                "IPI (R$)","IPI Base (R$)","IPI Alíq. (%)",
                                "PIS (R$)","PIS Base (R$)","PIS Alíq. (%)",
                                "COFINS (R$)","COFINS Base (R$)","COFINS Alíq. (%)","Aduaneiro (R$)"]:
                        df[col] = 0.00 if col != "NUMBER" else ""
                    st.session_state["merged_df"] = df
                    status_ok(f"DUIMP lida — {len(p.items)} adições encontradas.")
                except Exception as e:
                    st.error(f"Erro ao ler DUIMP: {e}")
                finally:
                    if _td_path and os.path.exists(_td_path):
                        try:
                            os.unlink(_td_path)
                        except Exception:
                            pass

        if file_app2 and st.session_state["parsed_sigraweb"] is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_app2.getvalue())
                tmp_path = tmp.name
            try:
                parser_a2 = SigrawebPDFParser() if is_sgw else HafelePDFParser()
                doc_a2    = parser_a2.parse_pdf(tmp_path)
                st.session_state["parsed_sigraweb"] = doc_a2
                n = len(doc_a2['itens'])
                if n > 0:
                    lname = "Sigraweb" if is_sgw else "Extrato DUIMP"
                    status_ok(f"{lname} lido — {n} itens encontrados.")
                    if is_sgw:
                        cab = doc_a2.get('cabecalho',{})
                        tot = doc_a2.get('totais',{})
                        with st.expander("📋 Resumo do Processo (Sigraweb)", expanded=True):
                            r1,r2,r3,r4 = st.columns(4)
                            r1.metric("Número DI",       cab.get('numeroDI','N/A'))
                            r2.metric("Adições",         n)
                            r3.metric("Peso Bruto (kg)", cab.get('pesoBruto','N/A'))
                            r4.metric("Via Transporte",  cab.get('viaTransporte','N/A'))
                            m1,m2,m3,m4 = st.columns(4)
                            m1.metric("II Total",   f"R$ {tot.get('total_ii',0):,.2f}")
                            m2.metric("IPI Total",  f"R$ {tot.get('total_ipi',0):,.2f}")
                            m3.metric("PIS Total",  f"R$ {tot.get('total_pis',0):,.2f}")
                            m4.metric("COFINS Total",f"R$ {tot.get('total_cofins',0):,.2f}")
                            n1,n2,n3,n4 = st.columns(4)
                            n1.metric("Vlr Adu. (R$)", f"R$ {tot.get('total_valor_aduaneiro',0):,.2f}")
                            n2.metric("Frete (R$)",    f"R$ {tot.get('total_frete',0):,.2f}")
                            n3.metric("Seguro (R$)",   f"R$ {tot.get('total_seguro',0):,.2f}")
                            n4.metric("Peso Líq. (kg)",f"{tot.get('peso_liquido_total',0):,.2f}")
                    else:
                        tot = doc_a2.get('totais',{})
                        with st.expander("📋 Resumo Extrato DUIMP", expanded=True):
                            e1,e2,e3,e4 = st.columns(4)
                            e1.metric("Itens",       n)
                            e2.metric("II Total",    f"R$ {tot.get('total_ii',0):,.2f}")
                            e3.metric("PIS Total",   f"R$ {tot.get('total_pis',0):,.2f}")
                            e4.metric("COFINS Total",f"R$ {tot.get('total_cofins',0):,.2f}")
                else:
                    st.warning("Nenhum item detectado. Verifique se o layout selecionado está correto.")
            except Exception as e:
                st.error(f"Erro ao ler APP2: {e}")
                st.code(traceback.format_exc())
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        st.divider()
        section_title("🔗 Ações")
        col_btn, col_reset = st.columns([2, 1], gap="large")

        with col_btn:
            if st.button("🔗 VINCULAR DADOS (Cruzamento Automático)",
                         type="primary", **_WS):
                if (st.session_state["merged_df"] is not None and
                        st.session_state["parsed_sigraweb"] is not None):
                    try:
                        doc_a2  = st.session_state["parsed_sigraweb"]
                        df_dest = st.session_state["merged_df"].copy()
                        df_dest, count, nf = _merge_app2_items(df_dest, doc_a2['itens'])
                        st.session_state["merged_df"] = df_dest
                        st.success(f"✅ **{count}** adições vinculadas.")
                        if nf: st.warning(f"⚠️ {len(nf)} não encontradas: {nf}")
                        with st.expander("📊 Resumo da Vinculação"):
                            _render_totais_grade(df_dest)
                    except Exception as e:
                        st.error(f"Erro na vinculação: {e}")
                        st.code(traceback.format_exc())
                else:
                    st.warning("Carregue os dois arquivos antes de vincular.")

        with col_reset:
            st.markdown('<div style="height:.05rem"></div>', unsafe_allow_html=True)
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("🔄 DUIMP", type="secondary", **_WS):
                    st.session_state["parsed_duimp"] = None
                    st.session_state["merged_df"]    = None
                    st.rerun()
            with rc2:
                if st.button("🔄 APP2", type="secondary", **_WS):
                    st.session_state["parsed_sigraweb"] = None
                    st.rerun()
            if st.button("🗑️ Limpar Tudo", type="secondary", **_WS):
                for k in ["parsed_duimp","parsed_sigraweb","merged_df","last_duimp"]:
                    st.session_state[k] = None
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2 — CONFERÊNCIA
    # ══════════════════════════════════════════════════════════════════════
    with tab_conf:
        section_title("📋 Conferência e Edição")

        doc_a2 = st.session_state.get("parsed_sigraweb")
        if doc_a2:
            itens_a2 = doc_a2.get('itens',[])

            if st.session_state["layout_app2"] == "sigraweb":
                cab = doc_a2.get('cabecalho',{})
                with st.expander("📄 Dados do Processo — Sigraweb"):
                    dados = {"Campo":["Número DI","SIGRAWEB ID","Empresa","CNPJ",
                                      "URF Entrada","Via Transporte","País Procedência",
                                      "Incoterms","IDT Conhecimento","IDT Master",
                                      "Data Embarque","Data Chegada","Data Registro",
                                      "Peso Bruto (kg)","Peso Líquido (kg)","Volumes",
                                      "Embalagem","Banco","Agência","Taxa EUR","Taxa USD",
                                      "FOB EUR","FOB BRL","Frete USD","Frete BRL",
                                      "Seguro USD","Seguro BRL","CIF USD","CIF BRL",
                                      "Vlr Aduaneiro USD","Vlr Aduaneiro BRL"],
                             "Valor":[cab.get(k,'') for k in [
                                 'numeroDI','sigraweb','nomeImportador','cnpj',
                                 'urf','viaTransporte','paisProcedencia','incoterms',
                                 'idtConhecimento','idtMaster','dataEmbarque','dataChegada',
                                 'dataRegistro','pesoBruto','pesoLiquido','volumes',
                                 'embalagem','banco','agencia','taxaEUR','taxaDolar',
                                 'fobEUR','fobBRL','freteUSD','freteBRL',
                                 'seguroUSD','seguroBRL','cifUSD','cifBRL',
                                 'valorAduaneiroUSD','valorAduaneiroBRL']]}
                    st.dataframe(pd.DataFrame(dados), **_WS, hide_index=True)

            lbl_exp = "Sigraweb" if st.session_state["layout_app2"]=="sigraweb" else "Extrato DUIMP"
            with st.expander(f"📑 Adições Extraídas — {lbl_exp}"):
                if itens_a2:
                    rows = [{
                        'Adição':       it.get('numeroAdicao',''),
                        'Part Number':  it.get('codigo_interno',''),
                        'NCM':          it.get('ncm',''),
                        'Descrição':    str(it.get('descricao',it.get('nome_produto','')))[:55],
                        'País':         it.get('paisOrigem',''),
                        'Qtd Est.':     it.get('quantidade',0),
                        'Qtd Com.':     it.get('quantidade_comercial',0),
                        'Und':          it.get('unidade',''),
                        'Peso Líq.':    it.get('pesoLiq',it.get('peso_liquido',0)),
                        'Vlr Adu. BRL': it.get('aduaneiro_reais',it.get('valorAduaneiroReal',it.get('local_aduaneiro',0))),
                        'Frete BRL':    it.get('frete_internacional',0),
                        'Seguro BRL':   it.get('seguro_internacional',0),
                        'II %':         it.get('ii_aliquota',0),
                        'II Base':      it.get('ii_base_calculo',0),
                        'II R$':        it.get('ii_valor_devido',0),
                        'IPI %':        it.get('ipi_aliquota',0),
                        'IPI R$':       it.get('ipi_valor_devido',0),
                        'PIS %':        it.get('pis_aliquota',0),
                        'PIS R$':       it.get('pis_valor_devido',0),
                        'COFINS %':     it.get('cofins_aliquota',0),
                        'COFINS R$':    it.get('cofins_valor_devido',0),
                        'Total Imp.':   it.get('total_impostos',0),
                    } for it in itens_a2]
                    dfa2 = pd.DataFrame(rows)
                    st.dataframe(dfa2, **_WS, height=340)
                    tt1,tt2,tt3,tt4,tt5 = st.columns(5)
                    tt1.metric("Vlr Adu. Total",f"R$ {dfa2['Vlr Adu. BRL'].sum():,.2f}")
                    tt2.metric("II Total",      f"R$ {dfa2['II R$'].sum():,.2f}")
                    tt3.metric("IPI Total",     f"R$ {dfa2['IPI R$'].sum():,.2f}")
                    tt4.metric("PIS Total",     f"R$ {dfa2['PIS R$'].sum():,.2f}")
                    tt5.metric("COFINS Total",  f"R$ {dfa2['COFINS R$'].sum():,.2f}")
                else:
                    st.info("Nenhum item extraído.")

        if st.session_state["merged_df"] is not None:
            section_title("✏️ Grade de Edição — DUIMP + APP2")
            ccfg = {
                "numeroAdicao":     st.column_config.TextColumn("Item",      width="small",  disabled=True),
                "NUMBER":           st.column_config.TextColumn("Part Number",width="medium"),
                "ncm":              st.column_config.TextColumn("NCM",       width="small",  disabled=True),
                "descricao":        st.column_config.TextColumn("Descrição", width="large",  disabled=True),
                "quantidade":       st.column_config.TextColumn("Qtd Est.",  disabled=True),
                "quantidade_comercial": st.column_config.TextColumn("Qtd Com.", disabled=True),
                "unidade":          st.column_config.TextColumn("Unidade",   disabled=True),
                "pesoLiq":          st.column_config.TextColumn("Peso Líq.", disabled=True),
                "valorTotal":       st.column_config.TextColumn("FOB",       disabled=True),
                "Frete (R$)":       st.column_config.NumberColumn(format="R$ %.2f"),
                "Seguro (R$)":      st.column_config.NumberColumn(format="R$ %.2f"),
                "Aduaneiro (R$)":   st.column_config.NumberColumn("Vlr Adu.", format="R$ %.2f"),
                "II Base (R$)":     st.column_config.NumberColumn("II Base",  format="R$ %.2f"),
                "II Alíq. (%)":     st.column_config.NumberColumn("II %",    format="%.4f"),
                "II (R$)":          st.column_config.NumberColumn("II R$",   format="R$ %.2f"),
                "IPI Base (R$)":    st.column_config.NumberColumn("IPI Base", format="R$ %.2f"),
                "IPI Alíq. (%)":    st.column_config.NumberColumn("IPI %",   format="%.4f"),
                "IPI (R$)":         st.column_config.NumberColumn("IPI R$",  format="R$ %.2f"),
                "PIS Base (R$)":    st.column_config.NumberColumn("PIS Base", format="R$ %.2f"),
                "PIS Alíq. (%)":    st.column_config.NumberColumn("PIS %",   format="%.4f"),
                "PIS (R$)":         st.column_config.NumberColumn("PIS R$",  format="R$ %.2f"),
                "COFINS Base (R$)": st.column_config.NumberColumn("COF Base", format="R$ %.2f"),
                "COFINS Alíq. (%)": st.column_config.NumberColumn("COF %",   format="%.4f"),
                "COFINS (R$)":      st.column_config.NumberColumn("COF R$",  format="R$ %.2f"),
            }
            edf = st.data_editor(
                st.session_state["merged_df"],
                hide_index=True, column_config=ccfg,
                **_WS, height=540,
            )
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
            empty_state("📋", "Nenhum dado vinculado ainda",
                        "Carregue os arquivos e execute a vinculação na aba Upload")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3 — EXPORTAR XML
    # ══════════════════════════════════════════════════════════════════════
    with tab_xml:
        section_title("⚙️ Configurações do XML Final (Layout 8686)")

        cab_sgw = {}
        if (st.session_state.get("parsed_sigraweb") and
                st.session_state["layout_app2"] == "sigraweb"):
            cab_sgw = st.session_state["parsed_sigraweb"].get("cabecalho",{})

        with st.expander("📅 Datas, Pesos e Locais", expanded=True):
            xc1, xc2, xc3 = st.columns(3, gap="large")
            with xc1:
                st.markdown("**Quantidade & Datas**")
                _v = cab_sgw.get('volumes','')
                inp_vol    = st.text_input("Qtd. Volume",      value=str(_v).zfill(5) if _v else '00001')
                inp_cheg   = st.text_input("Data Chegada",     value=cab_sgw.get('dataChegadaISO','20251120') or '20251120')
                inp_desemb = st.text_input("Data Desembaraço", value=cab_sgw.get('dataRegistro','20251124') or '20251124')
                inp_reg    = st.text_input("Data Registro",    value=cab_sgw.get('dataRegistro','20251124') or '20251124')
                inp_emb    = st.text_input("Data Embarque",    value=cab_sgw.get('dataEmbarqueISO','20251025') or '20251025')
            with xc2:
                st.markdown("**Pesos (formato XML)**")
                _pb = DataFormatter.format_quantity(cab_sgw.get('pesoBruto','0'),15) if cab_sgw.get('pesoBruto') else '000000000000000'
                _pl = DataFormatter.format_quantity(cab_sgw.get('pesoLiquido','0'),15) if cab_sgw.get('pesoLiquido') else '000000000000000'
                inp_pb  = st.text_input("Peso Bruto (XML)",   value=_pb)
                inp_pl  = st.text_input("Peso Líquido (XML)", value=_pl)
                st.markdown("**Locais (R$ / US$)**")
                inp_ldd = st.text_input("Descarga US$", value="000000000000000")
                inp_ldr = st.text_input("Descarga R$",  value="000000000000000")
                inp_led = st.text_input("Embarque US$", value="000000000000000")
                inp_ler = st.text_input("Embarque R$",  value="000000000000000")
            with xc3:
                st.markdown("**Pagamento & Conhecimento**")
                inp_ag  = st.text_input("Agência",         value=cab_sgw.get('agencia','3715') or '3715')
                inp_bco = st.text_input("Banco",           value="341")
                inp_idc = st.text_input("IDT Conhecimento",value=cab_sgw.get('idtConhecimento','CE123456') or 'CE123456')
                inp_idm = st.text_input("IDT Master",      value=cab_sgw.get('idtMaster','CE123456') or 'CE123456')
                st.markdown("**Receita 7811**")
                inp_r78 = st.text_input("Valor 7811", value="000000000000000")

        user_xml = {
            "quantidadeVolume":              inp_vol,
            "cargaDataChegada":              inp_cheg,
            "dataDesembaraco":               inp_desemb,
            "dataRegistro":                  inp_reg,
            "conhecimentoCargaEmbarqueData": inp_emb,
            "cargaPesoBruto":                inp_pb,
            "cargaPesoLiquido":              inp_pl,
            "agenciaPagamento":              inp_ag,
            "bancoPagamento":                inp_bco,
            "valorReceita7811":              inp_r78,
            "localDescargaTotalDolares":     inp_ldd,
            "localDescargaTotalReais":       inp_ldr,
            "localEmbarqueTotalDolares":     inp_led,
            "localEmbarqueTotalReais":       inp_ler,
            "conhecimentoCargaId":           inp_idc,
            "conhecimentoCargaIdMaster":     inp_idm,
        }

        st.divider()

        if st.session_state["merged_df"] is not None:
            if st.button("⚙️ Gerar XML (Layout 8686)", type="primary", **_WS):
                try:
                    p       = st.session_state["parsed_duimp"]
                    records = st.session_state["merged_df"].to_dict("records")
                    for i, item in enumerate(p.items):
                        if i < len(records):
                            item.update(records[i])
                    builder   = XMLBuilder(p)
                    xml_bytes = builder.build(user_inputs=user_xml)
                    duimp_num = p.header.get("numeroDUIMP","0000").replace("/","-")
                    st.download_button(
                        "⬇️ Baixar XML", data=xml_bytes,
                        file_name=f"DUIMP_{duimp_num}_INTEGRADO.xml",
                        mime="text/xml", **_WS,
                    )
                    st.success("✅ XML gerado com sucesso!")
                    with st.expander("👁️ Preview XML"):
                        st.code(xml_bytes.decode('utf-8', errors='ignore')[:3000], language='xml')
                except Exception as e:
                    st.error(f"Erro: {e}")
                    st.code(traceback.format_exc())
        else:
            empty_state("💾", "Nenhum dado disponível",
                        "Realize o upload e a vinculação antes de gerar o XML")


# ==============================================================================
# APLICAÇÃO PRINCIPAL
# ==============================================================================
def main():
    load_css()

    ph("""
    <div class="hero">
        <div class="hero-glow-left"></div>
        <img src="https://raw.githubusercontent.com/DaniloNs-creator/final/7ea6ab2a610ef8f0c11be3c34f046e7ff2cdfc6a/haefele_logo.png"
             class="hero-logo" alt="Häfele">
        <h1 class="hero-title">Sistema de Processamento Unificado 2026</h1>
        <p class="hero-sub">TXT · MasterSAF Automação · DUIMP — Análise e geração de XML fiscal</p>
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
        "⚡  MasterSAF Automação",
        "📊  Sistema Integrado DUIMP",
    ])
    with tab1: processador_txt()
    with tab2: mastersaf_automacao()
    with tab3: sistema_integrado_duimp()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
        st.code(traceback.format_exc())
