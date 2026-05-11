import streamlit as st
import os
import shutil
import zipfile
import time
import re
import subprocess
import platform
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <div class="topbar-brand">MASTER<span>SAF</span> &nbsp;// XML AUTOMATION ENGINE</div>
    <div class="topbar-meta">v3.0.0 &nbsp;·&nbsp; CT-e RECEPTOR &nbsp;·&nbsp; MÓDULO FISCAL</div>
</div>
""", unsafe_allow_html=True)

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
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.66rem; color:#8b8f98; line-height:1.6; margin-bottom:1.2rem;">Extração automatizada de CT-e<br>via portal MasterSAF · até 1000 págs.</div>
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
        usuario = st.text_input("Usuário", placeholder="login@empresa.com.br", key="usr")
        senha   = st.text_input("Senha", type="password", placeholder="••••••••", key="pwd")
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
        data_ini = st.text_input("Data Inicial", value="08/05/2026", key="di")
    with col_b:
        data_fin = st.text_input("Data Final", value="08/05/2026", key="df")

    # ── PARÂMETROS ──
    st.markdown("""
    <div style="background:#111318; padding:0 2rem;">
        <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">⚙️ Parâmetros</div>
    </div>
    """, unsafe_allow_html=True)

    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5)

    # ── PÓS-PROCESSAMENTO ──
    st.markdown("""
    <div style="background:#111318; padding:0 2rem;">
        <hr style="border:none; border-top:1px solid #1f2329; margin:1.2rem 0 0.8rem;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.2em; text-transform:uppercase; color:#5a5e66; margin-bottom:0.5rem;">📊 Pós-Processamento</div>
    </div>
    """, unsafe_allow_html=True)

    processar_xml = st.checkbox("Extrair ZIPs e processar XMLs para Excel", value=True, key="processar")

    st.markdown("""
    <div style="background:#111318; padding:0 2rem 2rem;">
        <br>
    </div>
    """, unsafe_allow_html=True)
    
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
    excel_placeholder    = st.empty()

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
# CT-e PROCESSOR
# ─────────────────────────────────────────────

CTE_NAMESPACES = {
    'cte': 'http://www.portalfiscal.inf.br/cte'
}


class CTeProcessor:
    """Processa arquivos XML de CT-e extraindo campos fiscais"""
    
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
        """Extrai o peso bruto do CT-e"""
        try:
            tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
            
            for prefix, uri in CTE_NAMESPACES.items():
                infQ_elements = root.findall(f'.//{{{uri}}}infQ')
                for infQ in infQ_elements:
                    tpMed = infQ.find(f'{{{uri}}}tpMed')
                    qCarga = infQ.find(f'{{{uri}}}qCarga')
                    
                    if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                        for tipo_peso in tipos_peso:
                            if tipo_peso in tpMed.text.upper():
                                return float(qCarga.text)
            
            infQ_elements = root.findall('.//infQ')
            for infQ in infQ_elements:
                tpMed = infQ.find('tpMed')
                qCarga = infQ.find('qCarga')
                
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tipo_peso in tipos_peso:
                        if tipo_peso in tpMed.text.upper():
                            return float(qCarga.text)
            
            return 0.0
        except Exception:
            return 0.0
    
    def extract_cte_data(self, xml_content, filename):
        """Extrai dados do CT-e"""
        try:
            root = ET.fromstring(xml_content)
            
            def find_text(element, xpath):
                try:
                    for prefix, uri in CTE_NAMESPACES.items():
                        full_xpath = xpath.replace('cte:', f'{{{uri}}}')
                        found = element.find(full_xpath)
                        if found is not None and found.text:
                            return found.text
                    
                    found = element.find(xpath.replace('cte:', ''))
                    if found is not None and found.text:
                        return found.text
                    return None
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
            documento_destinatario = dest_CNPJ or dest_CPF or 'N/A'
            
            dest_xLgr = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
            dest_nro = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
            dest_xBairro = find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
            dest_xMun = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
            dest_UF = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
            dest_CEP = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')
            
            endereco_destinatario = ""
            if dest_xLgr:
                endereco_destinatario += f"{dest_xLgr}"
                if dest_nro:
                    endereco_destinatario += f", {dest_nro}"
                if dest_xBairro:
                    endereco_destinatario += f" - {dest_xBairro}"
                if dest_xMun:
                    endereco_destinatario += f", {dest_xMun}"
                if dest_UF:
                    endereco_destinatario += f"/{dest_UF}"
                if dest_CEP:
                    endereco_destinatario += f" - CEP: {dest_CEP}"
            
            if not endereco_destinatario:
                endereco_destinatario = "N/A"
            
            infNFe_chave = find_text(root, './/cte:infNFe/cte:chave')
            numero_nfe = self.extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None
            
            peso_bruto = self.extract_peso_bruto(root)
            
            data_formatada = None
            if dhEmi:
                try:
                    data_obj = datetime.strptime(dhEmi[:10], '%Y-%m-%d')
                    data_formatada = data_obj.strftime('%d/%m/%y')
                except:
                    try:
                        data_obj = datetime.strptime(dhEmi[:10], '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%d/%m/%y')
                    except:
                        data_formatada = dhEmi[:10]
            
            try:
                vTPrest = float(vTPrest) if vTPrest else 0.0
            except (ValueError, TypeError):
                vTPrest = 0.0
            
            return {
                'Arquivo': filename,
                'nCT': nCT or 'N/A',
                'Data Emissão': data_formatada or dhEmi or 'N/A',
                'Código Município Início': cMunIni or 'N/A',
                'UF Início': UFIni or 'N/A',
                'Código Município Fim': cMunFim or 'N/A',
                'UF Fim': UFFim or 'N/A',
                'Emitente': emit_xNome or 'N/A',
                'Valor Prestação': vTPrest,
                'Peso Bruto (kg)': peso_bruto,
                'Remetente': rem_xNome or 'N/A',
                'Destinatário': dest_xNome or 'N/A',
                'Documento Destinatário': documento_destinatario,
                'Endereço Destinatário': endereco_destinatario,
                'Município Destino': dest_xMun or 'N/A',
                'UF Destino': dest_UF or 'N/A',
                'Chave NFe': infNFe_chave or 'N/A',
                'Número NFe': numero_nfe or 'N/A',
                'Data Processamento': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }
        except Exception:
            return None
    
    def process_xml_files_from_directory(self, directory_path):
        """Processa todos os arquivos XML em um diretório"""
        xml_files = list(Path(directory_path).glob('*.xml'))
        count = 0
        
        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'CTe' in content or 'conhecimento' in content.lower():
                    data = self.extract_cte_data(content, xml_file.name)
                    if data:
                        self.processed_data.append(data)
                        count += 1
            except Exception:
                pass
        
        return count, len(xml_files)
    
    def export_to_excel(self, output_path):
        """Exporta os dados processados para Excel"""
        if self.processed_data:
            df = pd.DataFrame(self.processed_data)
            df.to_excel(output_path, index=False, sheet_name='Dados_CTe', engine='openpyxl')
            return True, len(df)
        return False, 0
    
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
# LÓGICA PRINCIPAL DE AUTOMAÇÃO
# ─────────────────────────────────────────────

if iniciar:
    if not usuario or not senha:
        with right_col:
            st.error("⚠️  Preencha usuário e senha para continuar.")
    else:
        # Prepara diretório de downloads
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
            # ── ETAPA 1: Localizar browser ──
            log("Procurando Chrome/Chromium no sistema...", "info")
            chrome_binary = find_chrome_binary()
            
            if not chrome_binary:
                raise Exception(
                    "Chrome/Chromium não encontrado. "
                    "Instale: sudo apt-get install chromium-browser"
                )
            
            log(f"Browser encontrado: {chrome_binary}", "info")
            
            # ── ETAPA 2: Detectar versão ──
            chrome_version = get_chrome_version(chrome_binary)
            
            if chrome_version:
                log(f"Versão detectada: {chrome_version}", "info")
            else:
                log("Não foi possível detectar a versão do browser", "warn")
            
            # ── ETAPA 3: Inicializar driver ──
            log("Inicializando ChromeDriver...", "info")
            driver = get_driver(dl_path, chrome_binary, chrome_version)
            log("ChromeDriver inicializado com sucesso!", "ok")
            
            # ── ETAPA 4: Login ──
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
            
            # ── ETAPA 5: Navegar ──
            log("Navegando até Listagem de CT-es (Receptor)...", "info")
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')
            )
            time.sleep(4)
            
            # ── ETAPA 6: Configurar período ──
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
            log("Base de dados atualizada.", "ok")
            
            # ── ETAPA 7: Selecionar 100 registros ──
            log("Configurando exibição: 100 registros por página...", "info")
            driver.find_element(
                By.XPATH,
                '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]'
            ).click()
            time.sleep(4)
            
            # ── ETAPA 8: Loop de captura ──
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
                
                esperar_downloads(dl_path)
                time.sleep(5)
                
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
            
            log("Captura finalizada!", "ok")
            
            # Fecha o navegador
            driver.quit()
            driver = None
            
            # ── ETAPA 9: Pós-processamento ──
            if processar_xml:
                log("=" * 50, "info")
                log("📦 INICIANDO PROCESSAMENTO DOS ARQUIVOS", "info")
                log("=" * 50, "info")
                
                # Localiza ZIPs
                zip_files = list(Path(dl_path).glob('*.zip'))
                log(f"🔍 {len(zip_files)} arquivos ZIP encontrados", "info")
                
                if not zip_files:
                    log("⚠ Nenhum arquivo ZIP para processar!", "warn")
                else:
                    # Cria diretório de extração
                    extract_dir = tempfile.mkdtemp(prefix="mastersaf_extracted_")
                    
                    # Extrai ZIPs
                    log("📂 Extraindo arquivos ZIP...", "info")
                    all_xml_dirs = []
                    
                    for zip_file in zip_files:
                        try:
                            zip_name = zip_file.stem
                            extract_path = os.path.join(extract_dir, zip_name)
                            os.makedirs(extract_path, exist_ok=True)
                            
                            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                                zip_ref.extractall(extract_path)
                            
                            all_xml_dirs.append(extract_path)
                            log(f"   ✔ {zip_file.name}", "ok")
                        except Exception as e:
                            log(f"   ❌ Erro ao extrair {zip_file.name}: {e}", "err")
                    
                    # Processa XMLs
                    log("📄 Processando arquivos XML de CT-e...", "info")
                    
                    processor = CTeProcessor()
                    total_xml_encontrados = 0
                    total_xml_lidos = 0
                    
                    for xml_dir in all_xml_dirs:
                        processados, encontrados = processor.process_xml_files_from_directory(xml_dir)
                        total_xml_encontrados += encontrados
                        total_xml_lidos += processados
                    
                    log(f"📊 XMLs encontrados: {total_xml_encontrados}", "info")
                    log(f"📊 CT-es identificados: {total_xml_lidos}", "info")
                    
                    # Gera Excel
                    if total_xml_lidos > 0:
                        log("📊 Gerando arquivo Excel consolidado...", "info")
                        
                        # Cria pasta de resultados
                        results_dir = "/tmp/mastersaf_resultados"
                        os.makedirs(results_dir, exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        excel_filename = f"CTe_Processados_{timestamp}.xlsx"
                        excel_path = os.path.join(results_dir, excel_filename)
                        
                        success, num_registros = processor.export_to_excel(excel_path)
                        
                        if success:
                            # Calcula totais
                            df = pd.DataFrame(processor.processed_data)
                            peso_total = df['Peso Bruto (kg)'].sum()
                            valor_total = df['Valor Prestação'].sum()
                            
                            log(f"✅ Excel gerado com sucesso!", "ok")
                            log(f"📈 Resumo:", "info")
                            log(f"   • Registros: {num_registros}", "dim")
                            log(f"   • Peso Bruto Total: {peso_total:,.2f} kg", "dim")
                            log(f"   • Valor Total: R$ {valor_total:,.2f}", "dim")
                            
                            # Botão de download do Excel
                            with open(excel_path, "rb") as f:
                                excel_placeholder.download_button(
                                    f"📥  BAIXAR EXCEL CONSOLIDADO ({num_registros} CT-es)",
                                    f,
                                    excel_filename,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                )
                            
                            # Preview da tabela
                            st.dataframe(
                                df.head(10),
                                use_container_width=True,
                                hide_index=True
                            )
                            st.caption(f"Mostrando 10 de {num_registros} registros")
                        else:
                            log("⚠ Erro ao gerar Excel", "err")
                    else:
                        log("⚠ Nenhum CT-e identificado nos XMLs", "warn")
                    
                    processor.clear_data()
                    
                    # Limpa diretório de extração
                    try:
                        shutil.rmtree(extract_dir)
                    except:
                        pass
            else:
                # Se não processar, oferece ZIP
                log("⚠ Processamento desativado. Compactando ZIPs...", "warn")
                
                zip_filename = "/tmp/resultado.zip"
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(dl_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, file)
                
                with open(zip_filename, "rb") as f:
                    download_placeholder.download_button(
                        "📥  BAIXAR ARQUIVOS XML (.ZIP)",
                        f,
                        "XMLs_MasterSaf.zip",
                        "application/zip",
                    )
            
            log("Processo finalizado com sucesso!", "ok")
            log_placeholder.markdown(render_log(logs, active=False), unsafe_allow_html=True)
            
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