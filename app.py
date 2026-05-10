import streamlit as st
import os
import shutil
import zipfile
import time
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MasterSAF — CT-e para Excel",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,300&display=swap');

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

html, body, [data-testid="stAppViewContainer"] {
    background: #0a0c10 !important;
    color: #d4dbe8 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] {
    background: #0e1117 !important;
    border-right: 1px solid #1e2535 !important;
}
[data-testid="stSidebar"] * { color: #c4ccd8 !important; }

.hero {
    padding: 2.5rem 0 1.5rem;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 2rem;
}
.hero-tag {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    color: #00e5a0;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.1rem;
    font-weight: 700;
    color: #eef2ff;
    line-height: 1.15;
    margin: 0;
}
.hero-title span { color: #00e5a0; }
.hero-subtitle {
    font-size: 0.95rem;
    color: #6b7a99;
    margin-top: 0.5rem;
    font-weight: 300;
}

/* Pipeline steps */
.pipeline {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 1.5rem 0 2rem;
    flex-wrap: wrap;
}
.step {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: #0e1117;
    border: 1px solid #1e2535;
    border-radius: 8px;
    padding: 0.7rem 1.1rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: #4a5568;
    transition: all 0.3s;
}
.step.active {
    border-color: #00e5a0;
    color: #00e5a0;
    box-shadow: 0 0 12px rgba(0,229,160,0.15);
}
.step.done {
    border-color: #0070f3;
    color: #0070f3;
}
.step-arrow {
    color: #1e2535;
    font-size: 1.1rem;
    padding: 0 0.3rem;
    font-family: monospace;
}

[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #00e5a0, #0070f3) !important;
    border-radius: 4px !important;
}
[data-testid="stProgress"] > div {
    background: #1e2535 !important;
    border-radius: 4px !important;
    height: 6px !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #070910 !important;
    border: 1px solid #1e2535 !important;
    border-radius: 6px !important;
    color: #d4dbe8 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.82rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #00e5a0 !important;
    box-shadow: 0 0 0 2px rgba(0,229,160,0.15) !important;
}

[data-testid="stSidebar"] label {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #4a5568 !important;
}

[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #00e5a0, #0070f3) !important;
    color: #020408 !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.08em !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.75rem 1.5rem !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton button:hover { opacity: 0.85 !important; }

.stDownloadButton button {
    background: linear-gradient(135deg, #00e5a0, #0070f3) !important;
    color: #020408 !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    border-radius: 8px !important;
    padding: 0.9rem 2rem !important;
    width: 100% !important;
    border: none !important;
}

[data-testid="stAlert"] {
    background: #0e1117 !important;
    border-radius: 8px !important;
    border-left: 3px solid !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
}

.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: #4a5568;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    margin-top: 1.8rem;
    border-bottom: 1px solid #1e2535;
    padding-bottom: 0.4rem;
}

.sidebar-logo {
    font-family: 'Space Mono', monospace;
    font-size: 0.95rem;
    font-weight: 700;
    color: #eef2ff;
    letter-spacing: 0.05em;
    padding: 1.2rem 0 1.5rem;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 1.2rem;
}
.sidebar-logo span { color: #00e5a0; }

.stat-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.8rem;
    margin: 1.2rem 0;
}
.stat-card {
    background: #0e1117;
    border: 1px solid #1e2535;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    position: relative;
    overflow: hidden;
}
.stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00e5a0, #0070f3);
}
.stat-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    color: #4a5568;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.stat-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #eef2ff;
}
.stat-value.green { color: #00e5a0; }
.stat-value.blue  { color: #0070f3; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────
defaults = {
    "running":     False,
    "done":        False,
    "error_msg":   "",
    "page_atual":  0,
    "page_total":  0,
    "status_msg":  "",
    "stage":       "idle",   # idle | download | extract | excel | done
    "xml_count":   0,
    "excel_bytes": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">⚡ Automação Fiscal Completa</div>
    <h1 class="hero-title">Master<span>SAF</span> → Excel</h1>
    <p class="hero-subtitle">Baixa CT-es do portal, extrai os XMLs e entrega uma planilha Excel — tudo automaticamente</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PIPELINE VISUAL
# ─────────────────────────────────────────────
def render_pipeline():
    stage = st.session_state.stage
    steps = [
        ("download", "01 Download CT-e"),
        ("extract",  "02 Extrair XMLs"),
        ("excel",    "03 Gerar Excel"),
        ("done",     "04 Pronto"),
    ]
    order = [s[0] for s in steps]
    cur_idx = order.index(stage) if stage in order else -1

    html = '<div class="pipeline">'
    for i, (key, label) in enumerate(steps):
        idx = order.index(key)
        if idx < cur_idx:
            cls = "done"
            icon = "✓"
        elif idx == cur_idx:
            cls = "active"
            icon = "●"
        else:
            cls = ""
            icon = str(i + 1).zfill(2)
        html += f'<div class="step {cls}"><span>{icon}</span><span>{label}</span></div>'
        if i < len(steps) - 1:
            html += '<span class="step-arrow">→</span>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

render_pipeline()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">MASTER<span>SAF</span> //</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Credenciais</div>', unsafe_allow_html=True)
    usuario   = st.text_input("Usuário", placeholder="login@empresa.com.br", disabled=st.session_state.running)
    senha     = st.text_input("Senha", type="password", placeholder="••••••••",  disabled=st.session_state.running)

    st.markdown('<div class="section-label">Período</div>', unsafe_allow_html=True)
    data_ini  = st.text_input("Data Inicial", value="08/05/2026", disabled=st.session_state.running)
    data_fin  = st.text_input("Data Final",   value="08/05/2026", disabled=st.session_state.running)

    st.markdown('<div class="section-label">Parâmetros</div>', unsafe_allow_html=True)
    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5, disabled=st.session_state.running)

    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.running:
        iniciar = st.button("⚡ Iniciar Automação")
    else:
        st.button("⏳ Processando...", disabled=True)
        iniciar = False

# ─────────────────────────────────────────────
# CT-e PARSER (extraído do app conversor)
# ─────────────────────────────────────────────
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

def extract_nfe_number_from_key(chave_acesso):
    if not chave_acesso or len(chave_acesso) != 44:
        return None
    try:
        return chave_acesso[25:34]
    except Exception:
        return None

def extract_peso_bruto(root):
    tipos_peso = ['PESO BRUTO', 'PESO BASE DE CALCULO', 'PESO BASE CÁLCULO', 'PESO']
    try:
        for prefix, uri in CTE_NAMESPACES.items():
            for infQ in root.findall(f'.//{{{uri}}}infQ'):
                tpMed  = infQ.find(f'{{{uri}}}tpMed')
                qCarga = infQ.find(f'{{{uri}}}qCarga')
                if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                    for tp in tipos_peso:
                        if tp in tpMed.text.upper():
                            return float(qCarga.text), tp
        # sem namespace
        for infQ in root.findall('.//infQ'):
            tpMed  = infQ.find('tpMed')
            qCarga = infQ.find('qCarga')
            if tpMed is not None and tpMed.text and qCarga is not None and qCarga.text:
                for tp in tipos_peso:
                    if tp in tpMed.text.upper():
                        return float(qCarga.text), tp
    except Exception:
        pass
    return 0.0, "Não encontrado"

def extract_cte_data(xml_content, filename):
    try:
        root = ET.fromstring(xml_content)
        for prefix, uri in CTE_NAMESPACES.items():
            ET.register_namespace(prefix, uri)

        def find_text(element, xpath):
            for prefix, uri in CTE_NAMESPACES.items():
                found = element.find(xpath.replace('cte:', f'{{{uri}}}'))
                if found is not None and found.text:
                    return found.text
            found = element.find(xpath.replace('cte:', ''))
            return found.text if found is not None and found.text else None

        nCT         = find_text(root, './/cte:nCT')
        dhEmi       = find_text(root, './/cte:dhEmi')
        UFIni       = find_text(root, './/cte:UFIni')
        UFFim       = find_text(root, './/cte:UFFim')
        cMunIni     = find_text(root, './/cte:cMunIni')
        cMunFim     = find_text(root, './/cte:cMunFim')
        emit_xNome  = find_text(root, './/cte:emit/cte:xNome')
        vTPrest     = find_text(root, './/cte:vTPrest')
        rem_xNome   = find_text(root, './/cte:rem/cte:xNome')
        dest_xNome  = find_text(root, './/cte:dest/cte:xNome')
        dest_CNPJ   = find_text(root, './/cte:dest/cte:CNPJ')
        dest_CPF    = find_text(root, './/cte:dest/cte:CPF')
        dest_xLgr   = find_text(root, './/cte:dest/cte:enderDest/cte:xLgr')
        dest_nro    = find_text(root, './/cte:dest/cte:enderDest/cte:nro')
        dest_xBairro= find_text(root, './/cte:dest/cte:enderDest/cte:xBairro')
        dest_xMun   = find_text(root, './/cte:dest/cte:enderDest/cte:xMun')
        dest_CEP    = find_text(root, './/cte:dest/cte:enderDest/cte:CEP')
        dest_UF     = find_text(root, './/cte:dest/cte:enderDest/cte:UF')
        infNFe_chave= find_text(root, './/cte:infNFe/cte:chave')

        doc_dest = dest_CNPJ or dest_CPF or 'N/A'
        endereco  = 'N/A'
        if dest_xLgr:
            partes = [dest_xLgr]
            if dest_nro:    partes.append(f", {dest_nro}")
            if dest_xBairro:partes.append(f" - {dest_xBairro}")
            if dest_xMun:   partes.append(f", {dest_xMun}")
            if dest_UF:     partes.append(f"/{dest_UF}")
            if dest_CEP:    partes.append(f" - CEP: {dest_CEP}")
            endereco = "".join(partes)

        # Data
        data_fmt = None
        if dhEmi:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
                try:
                    data_fmt = datetime.strptime(dhEmi[:10], fmt).strftime('%d/%m/%y')
                    break
                except Exception:
                    pass

        try:
            vTPrest_f = float(vTPrest) if vTPrest else 0.0
        except Exception:
            vTPrest_f = 0.0

        peso_bruto, tipo_peso = extract_peso_bruto(root)
        numero_nfe = extract_nfe_number_from_key(infNFe_chave) if infNFe_chave else None

        return {
            'Arquivo':                filename,
            'nCT':                    nCT or 'N/A',
            'Data Emissão':           data_fmt or (dhEmi[:10] if dhEmi else 'N/A'),
            'Código Município Início':cMunIni or 'N/A',
            'UF Início':              UFIni or 'N/A',
            'Código Município Fim':   cMunFim or 'N/A',
            'UF Fim':                 UFFim or 'N/A',
            'Emitente':               emit_xNome or 'N/A',
            'Valor Prestação':        vTPrest_f,
            'Peso Bruto (kg)':        peso_bruto,
            'Tipo de Peso Encontrado':tipo_peso,
            'Remetente':              rem_xNome or 'N/A',
            'Destinatário':           dest_xNome or 'N/A',
            'Documento Destinatário': doc_dest,
            'Endereço Destinatário':  endereco,
            'Município Destino':      dest_xMun or 'N/A',
            'UF Destino':             dest_UF or 'N/A',
            'Chave NFe':              infNFe_chave or 'N/A',
            'Número NFe':             numero_nfe or 'N/A',
            'Data Processamento':     datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        }
    except Exception:
        return None

def xmls_to_excel(xml_folder: str) -> tuple[bytes, int]:
    """Varre a pasta, parseia todos os XMLs de CT-e e devolve bytes do Excel."""
    rows = []
    for fname in os.listdir(xml_folder):
        if not fname.lower().endswith('.xml'):
            continue
        fpath = os.path.join(xml_folder, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            data = extract_cte_data(content, fname)
            if data:
                rows.append(data)
        except Exception:
            pass

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        if not df.empty:
            df.to_excel(writer, sheet_name='CT-e', index=False)
            wb = writer.book
            ws = writer.sheets['CT-e']

            # Formatação básica
            header_fmt = wb.add_format({
                'bold': True, 'bg_color': '#0e1117', 'font_color': '#00e5a0',
                'border': 1, 'border_color': '#1e2535', 'align': 'center'
            })
            money_fmt  = wb.add_format({'num_format': 'R$ #,##0.00'})
            weight_fmt = wb.add_format({'num_format': '#,##0.000'})

            for col_num, col_name in enumerate(df.columns):
                ws.write(0, col_num, col_name, header_fmt)
                col_width = max(len(col_name) + 2, 14)
                ws.set_column(col_num, col_num, col_width)
                if col_name == 'Valor Prestação':
                    ws.set_column(col_num, col_num, 18, money_fmt)
                elif 'Peso' in col_name:
                    ws.set_column(col_num, col_num, 16, weight_fmt)
        else:
            pd.DataFrame([{"Aviso": "Nenhum CT-e válido encontrado"}]).to_excel(
                writer, sheet_name='CT-e', index=False)

    return buf.getvalue(), len(rows)

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

# ─────────────────────────────────────────────
# WORKER — thread isolada do Streamlit
# ─────────────────────────────────────────────
def automation_worker(usuario, senha, data_ini, data_fin, qtd_loops, dl_path, xml_path, state):
    driver = None
    try:
        # ── ETAPA 1: Download ──────────────────────────────────────────
        state["stage"]      = "download"
        state["status_msg"] = "Inicializando navegador..."
        driver = get_driver(dl_path)

        state["status_msg"] = "Autenticando no MasterSAF..."
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
        driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="enter"]'))
        time.sleep(4)

        state["status_msg"] = "Navegando até a listagem de CT-es..."
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
        time.sleep(3)

        for xpath, val in [('//*[@id="consultaDataInicial"]', data_ini), ('//*[@id="consultaDataFinal"]', data_fin)]:
            el = driver.find_element(By.XPATH, xpath)
            el.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
            el.send_keys(val)

        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
        time.sleep(3)

        driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
        time.sleep(3)

        for i in range(int(qtd_loops)):
            state["status_msg"] = f"⏳ Baixando página {i+1} de {int(qtd_loops)}..."

            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))

            time.sleep(8)  # Aguarda download

            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))

            state["page_atual"] = i + 1
            time.sleep(4)

        driver.quit()
        driver = None

        # ── ETAPA 2: Extrair XMLs dos ZIPs baixados ───────────────────
        state["stage"]      = "extract"
        state["status_msg"] = "Extraindo XMLs dos arquivos baixados..."

        os.makedirs(xml_path, exist_ok=True)
        xml_count = 0

        for fname in os.listdir(dl_path):
            fpath = os.path.join(dl_path, fname)
            flower = fname.lower()

            if flower.endswith('.zip'):
                try:
                    with zipfile.ZipFile(fpath, 'r') as zf:
                        for member in zf.namelist():
                            if member.lower().endswith('.xml'):
                                zf.extract(member, xml_path)
                                xml_count += 1
                except Exception:
                    pass

            elif flower.endswith('.xml'):
                shutil.copy2(fpath, os.path.join(xml_path, fname))
                xml_count += 1

        state["xml_count"]  = xml_count
        state["status_msg"] = f"{xml_count} XMLs extraídos. Convertendo para Excel..."

        # ── ETAPA 3: Converter para Excel ─────────────────────────────
        state["stage"]      = "excel"
        excel_bytes, total  = xmls_to_excel(xml_path)
        state["excel_bytes"]= excel_bytes
        state["xml_count"]  = total
        state["status_msg"] = f"✅ Concluído! {total} CT-e(s) convertidos para Excel."
        state["stage"]      = "done"

    except Exception as e:
        state["error_msg"]  = str(e)
        state["status_msg"] = f"❌ Erro: {e}"
    finally:
        state["running"] = False
        state["done"]    = True
        if driver:
            try: driver.quit()
            except Exception: pass

# ─────────────────────────────────────────────
# DISPARO
# ─────────────────────────────────────────────
if iniciar:
    if not usuario or not senha:
        st.error("⚠️ Preencha usuário e senha para continuar.")
    else:
        dl_path  = "/tmp/downloads"
        xml_path = "/tmp/xmls"
        for p in [dl_path, xml_path]:
            if os.path.exists(p): shutil.rmtree(p)
            os.makedirs(p)

        st.session_state.running     = True
        st.session_state.done        = False
        st.session_state.error_msg   = ""
        st.session_state.page_atual  = 0
        st.session_state.page_total  = int(qtd_loops)
        st.session_state.status_msg  = "Iniciando..."
        st.session_state.stage       = "download"
        st.session_state.xml_count   = 0
        st.session_state.excel_bytes = None

        t = threading.Thread(
            target=automation_worker,
            args=(usuario, senha, data_ini, data_fin, qtd_loops, dl_path, xml_path, st.session_state),
            daemon=True,
        )
        t.start()
        st.rerun()

# ─────────────────────────────────────────────
# PAINEL DE STATUS
# ─────────────────────────────────────────────
if st.session_state.running or st.session_state.done:
    st.markdown('<div class="section-label">Status</div>', unsafe_allow_html=True)

    total = st.session_state.page_total or 1
    atual = st.session_state.page_atual

    # Progresso da etapa de download
    if st.session_state.stage == "download":
        pct = atual / total
    elif st.session_state.stage in ("extract", "excel"):
        pct = 0.85
    else:
        pct = 1.0

    if st.session_state.error_msg:
        st.error(f"❌ {st.session_state.error_msg}")
    elif st.session_state.stage == "done":
        st.success(st.session_state.status_msg)
    else:
        st.info(st.session_state.status_msg)

    st.progress(pct)

    # Métricas
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card">
            <div class="stat-label">Páginas Baixadas</div>
            <div class="stat-value green">{atual}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Programado</div>
            <div class="stat-value">{total}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">CT-es Extraídos</div>
            <div class="stat-value blue">{st.session_state.xml_count}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Etapa Atual</div>
            <div class="stat-value" style="font-size:1rem;padding-top:0.4rem">{st.session_state.stage.upper()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botão de download do Excel
    if st.session_state.stage == "done" and st.session_state.excel_bytes:
        st.markdown('<div class="section-label">Download</div>', unsafe_allow_html=True)
        periodo = f"{data_ini.replace('/', '-')}_a_{data_fin.replace('/', '-')}"
        st.download_button(
            label=f"📥 BAIXAR EXCEL — {st.session_state.xml_count} CT-es",
            data=st.session_state.excel_bytes,
            file_name=f"CTe_MasterSAF_{periodo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Auto-refresh a cada 3s enquanto roda
    if st.session_state.running:
        time.sleep(3)
        st.rerun()
