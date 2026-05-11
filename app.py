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
from webdriver_manager.chrome import ChromeDriverManager

st.set_page_config(
    page_title="MasterSAF — Automação XML",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,300&display=swap');
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
html, body, [data-testid="stAppViewContainer"] { background: #0a0c10 !important; color: #d4dbe8 !important; font-family: 'DM Sans', sans-serif !important; }
[data-testid="stSidebar"] { background: #0e1117 !important; border-right: 1px solid #1e2535 !important; }
[data-testid="stSidebar"] * { color: #c4ccd8 !important; }
.hero { padding: 2.5rem 0 1.5rem; border-bottom: 1px solid #1e2535; margin-bottom: 2rem; }
.hero-tag { font-family: 'Space Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em; color: #00e5a0; text-transform: uppercase; margin-bottom: 0.5rem; }
.hero-title { font-family: 'Space Mono', monospace; font-size: 2.1rem; font-weight: 700; color: #eef2ff; line-height: 1.15; margin: 0; }
.hero-title span { color: #00e5a0; }
.hero-subtitle { font-size: 0.95rem; color: #6b7a99; margin-top: 0.5rem; font-weight: 300; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #00e5a0, #0070f3) !important; border-radius: 4px !important; }
[data-testid="stProgress"] > div { background: #1e2535 !important; border-radius: 4px !important; height: 6px !important; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input { background: #070910 !important; border: 1px solid #1e2535 !important; border-radius: 6px !important; color: #d4dbe8 !important; font-family: 'Space Mono', monospace !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] label { font-family: 'Space Mono', monospace !important; font-size: 0.72rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; color: #4a5568 !important; }
[data-testid="stSidebar"] .stButton button { background: linear-gradient(135deg, #00e5a0, #0070f3) !important; color: #020408 !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; font-size: 0.82rem !important; border: none !important; border-radius: 6px !important; padding: 0.75rem 1.5rem !important; width: 100% !important; }
.stDownloadButton button { background: #0e1117 !important; color: #00e5a0 !important; border: 1px solid #00e5a0 !important; font-family: 'Space Mono', monospace !important; font-size: 0.8rem !important; border-radius: 6px !important; padding: 0.65rem 1.4rem !important; }
.section-label { font-family: 'Space Mono', monospace; font-size: 0.65rem; letter-spacing: 0.2em; color: #4a5568; text-transform: uppercase; margin-bottom: 0.8rem; margin-top: 1.8rem; border-bottom: 1px solid #1e2535; padding-bottom: 0.4rem; }
.sidebar-logo { font-family: 'Space Mono', monospace; font-size: 0.95rem; font-weight: 700; color: #eef2ff; padding: 1.2rem 0 1.5rem; border-bottom: 1px solid #1e2535; margin-bottom: 1.2rem; }
.sidebar-logo span { color: #00e5a0; }
.resumo-card { background: #0e1117; border: 1px solid #1e2535; border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 0.8rem; }
.resumo-card .label { font-family: 'Space Mono', monospace; font-size: 0.65rem; letter-spacing: 0.15em; color: #4a5568; text-transform: uppercase; }
.resumo-card .value { font-family: 'Space Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #00e5a0; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)

# ── NAMESPACES CT-e ───────────────────────────
CTE_NAMESPACES = {'cte': 'http://www.portalfiscal.inf.br/cte'}

# ── CLASSE CTeProcessor (portada do desktop) ──
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
        """Lê bytes de um ZIP e processa cada XML de CT-e interno."""
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
        """Processa todos os ZIPs (e XMLs soltos) em um diretório."""
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
        """Retorna (bytes_excel, num_registros) para st.download_button."""
        if not self.processed_data:
            return None, 0
        df = pd.DataFrame(self.processed_data)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados_CTe')
            ws = writer.sheets['Dados_CTe']
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.utils import get_column_letter
            hf = PatternFill('solid', start_color='0D1B2A', end_color='0D1B2A')
            hfont = Font(bold=True, color='00E5A0', name='Arial', size=10)
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

# ── HERO ──────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">⚡ Sistema de Automação Fiscal</div>
    <h1 class="hero-title">Master<span>SAF</span> Downloads XML</h1>
    <p class="hero-subtitle">Captura e processamento automatizado de CT-e — download + Excel consolidado em uma única operação</p>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">MASTER<span>SAF</span> //</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Credenciais</div>', unsafe_allow_html=True)
    usuario  = st.text_input("Usuário", placeholder="login@empresa.com.br")
    senha    = st.text_input("Senha", type="password", placeholder="••••••••")
    st.markdown('<div class="section-label">Período</div>', unsafe_allow_html=True)
    data_ini = st.text_input("Data Inicial", value="08/05/2026")
    data_fin = st.text_input("Data Final",   value="08/05/2026")
    st.markdown('<div class="section-label">Parâmetros</div>', unsafe_allow_html=True)
    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5)
    st.markdown('<div class="section-label">Saída</div>', unsafe_allow_html=True)
    gerar_excel = st.checkbox("Gerar Excel consolidado dos CT-es", value=True)
    gerar_zip   = st.checkbox("Disponibilizar ZIP com XMLs brutos", value=True)
    st.markdown("<br>", unsafe_allow_html=True)
    iniciar = st.button("⚡ Iniciar Automação")

# ── DRIVER ────────────────────────────────────
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
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    # Descomente se necessário no Windows:
    # opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def esperar_downloads(directory, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        if not list(Path(directory).glob('*.crdownload')):
            return True
        time.sleep(1)
    return False

# ── LÓGICA PRINCIPAL ─────────────────────────
if iniciar:
    if not usuario or not senha:
        st.error("⚠️ Atenção: Preencha o usuário e a senha para continuar.")
    else:
        dl_path = tempfile.mkdtemp(prefix="mastersaf_web_")
        st.markdown('<div class="section-label">Execução</div>', unsafe_allow_html=True)
        status_box   = st.info("Inicializando ambiente e navegador...")
        progress_bar = st.progress(0)
        log_area     = st.empty()
        log_lines    = []

        def log(msg):
            ts = datetime.now().strftime("%H:%M:%S")
            log_lines.append(f"[{ts}] {msg}")
            log_area.code("\n".join(log_lines[-30:]), language=None)

        driver = None
        try:
            log("🌐 Iniciando navegador em modo headless...")
            driver = get_driver(dl_path)

            status_box.info("🔑 Autenticando no MasterSAF...")
            log("🔗 Acessando https://p.dfe.mastersaf.com.br/mvc/login")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            time.sleep(3)
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="enter"]'))
            time.sleep(5)
            log("✅ Login realizado")
            progress_bar.progress(0.05)

            status_box.info("📋 Navegando até Listagem de CT-es...")
            driver.execute_script("arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(5)
            log("📋 Listagem Receptor CT-es acessada")
            progress_bar.progress(0.08)

            log(f"📅 Configurando período: {data_ini} → {data_fin}")
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

            log("⚙️ Configurando 200 itens por página...")
            sel = driver.find_element(
                By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
            sel.click()
            time.sleep(1)
            sel.find_element(By.XPATH, './/option[@value="200"]').click()
            time.sleep(3)
            progress_bar.progress(0.15)

            log(f"📥 Iniciando loop de {int(qtd_loops)} página(s)...")

            for i in range(int(qtd_loops)):
                log(f"📄 Página {i + 1}/{int(qtd_loops)}")
                try:
                    cb = driver.find_element(
                        By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                    if not cb.is_selected():
                        cb.click()
                    time.sleep(2)
                except Exception:
                    log("   ⚠ Não foi possível marcar checkboxes")

                try:
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                except Exception:
                    log("   ⚠ Erro ao clicar no botão de download em massa")

                log("   ⏳ Aguardando download...")
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
                        log("   ⚠ Fim das páginas disponíveis")
                        break

                pct = 0.15 + ((i + 1) / int(qtd_loops)) * 0.60
                progress_bar.progress(pct)
                status_box.info(
                    f"⏳ Baixando XMLs — {i + 1} de {int(qtd_loops)} páginas concluídas...")

            log("✅ Downloads concluídos!")
            driver.quit()
            driver = None
            progress_bar.progress(0.78)

            # ── Processamento XML → Excel ──────────────
            processor = CTeProcessor()
            zip_files_found = list(Path(dl_path).glob('*.zip'))
            log(f"🔍 {len(zip_files_found)} ZIP(s) localizado(s)")

            if gerar_excel and zip_files_found:
                status_box.info("📊 Processando XMLs e gerando Excel...")
                processor.process_directory(dl_path, log)
                log(f"📊 Total de CT-es: {len(processor.processed_data)}")
            progress_bar.progress(0.92)

            # ── ZIP bruto ──────────────────────────────
            zip_buf = None
            if gerar_zip:
                log("📦 Compactando XMLs brutos...")
                buf_io = io.BytesIO()
                with zipfile.ZipFile(buf_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root_dir, _, files in os.walk(dl_path):
                        for file in files:
                            zipf.write(os.path.join(root_dir, file), file)
                buf_io.seek(0)
                zip_buf = buf_io.getvalue()

            progress_bar.progress(1.0)
            status_box.success("✅ Processamento concluído com sucesso!")
            log("🏁 Tudo pronto!")

            # ── Cards de resumo ────────────────────────
            if gerar_excel and processor.processed_data:
                summ = processor.summary()
                st.markdown('<div class="section-label">Resumo dos CT-es Processados</div>', unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                for col, label, value in [
                    (c1, "CT-es",       f"{summ['total']:,}"),
                    (c2, "Peso Bruto",  f"{summ['peso_total']:,.0f} kg"),
                    (c3, "Valor Total", f"R$ {summ['valor_total']:,.2f}"),
                    (c4, "Emitentes",   f"{summ['emitentes']}"),
                ]:
                    with col:
                        st.markdown(f"""
                        <div class="resumo-card">
                            <div class="label">{label}</div>
                            <div class="value">{value}</div>
                        </div>""", unsafe_allow_html=True)

            # ── Botões de download ─────────────────────
            st.markdown('<div class="section-label">Downloads</div>', unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)

            if gerar_excel:
                if processor.processed_data:
                    excel_bytes, n_reg = processor.export_to_excel_bytes()
                    if excel_bytes:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        with dl1:
                            st.download_button(
                                label=f"📊 DOWNLOAD EXCEL ({n_reg} CT-es)",
                                data=excel_bytes,
                                file_name=f"CTe_Processados_{ts}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                else:
                    with dl1:
                        st.warning("Nenhum CT-e extraído dos ZIPs.")

            if gerar_zip and zip_buf:
                with dl2:
                    st.download_button(
                        label="📥 DOWNLOAD ZIP (XMLs brutos)",
                        data=zip_buf,
                        file_name="XMLs_MasterSaf.zip",
                        mime="application/zip",
                    )

            shutil.rmtree(dl_path, ignore_errors=True)

        except Exception as e:
            st.error(f"❌ Ocorreu um erro técnico: {e}")
            log(f"❌ ERRO: {e}")
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            shutil.rmtree(dl_path, ignore_errors=True)