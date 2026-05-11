import streamlit as st
import os
import shutil
import zipfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MasterSAF — Automação XML",
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
    transition: opacity 0.2s !important;
}
[data-testid="stSidebar"] .stButton button:hover { opacity: 0.85 !important; }

.stDownloadButton button {
    background: #0e1117 !important;
    color: #00e5a0 !important;
    border: 1px solid #00e5a0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
    border-radius: 6px !important;
    padding: 0.65rem 1.4rem !important;
    transition: all 0.2s !important;
}
.stDownloadButton button:hover {
    background: #00e5a0 !important;
    color: #020408 !important;
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">⚡ Sistema de Automação Fiscal</div>
    <h1 class="hero-title">Master<span>SAF</span> Downloads XML</h1>
    <p class="hero-subtitle">Captura automatizada de CT-e em massa — suporte a até 1 000 páginas por sessão</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
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

    st.markdown("<br>", unsafe_allow_html=True)
    iniciar = st.button("⚡ Iniciar Automação")

# ─────────────────────────────────────────────
# DRIVER — idêntico ao código funcional
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
# LÓGICA PRINCIPAL — 100% idêntica ao funcional
# ─────────────────────────────────────────────
if iniciar:
    if not usuario or not senha:
        st.error("⚠️ Atenção: Preencha o usuário e a senha para continuar.")
    else:
        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path):
            shutil.rmtree(dl_path)
        os.makedirs(dl_path)

        st.markdown('<div class="section-label">Execução</div>', unsafe_allow_html=True)
        status_box   = st.info("Inicializando ambiente e navegador...")
        progress_bar = st.progress(0)

        try:
            driver = get_driver(dl_path)

            # Login
            status_box.info("Acessando o sistema MasterSAF e realizando autenticação...")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="enter"]'))
            time.sleep(4)

            # Navegação
            status_box.info("Navegando até o módulo de Listagem de CT-es...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(3)

            # Datas
            for xpath, val in [('//*[@id="consultaDataInicial"]', data_ini), ('//*[@id="consultaDataFinal"]', data_fin)]:
                el = driver.find_element(By.XPATH, xpath)
                el.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
                el.send_keys(val)

            status_box.info("Atualizando base de dados com as datas informadas...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
            time.sleep(3)

            # Seleção de visualização
            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
            time.sleep(3)

            # Loop de Downloads
            for i in range(int(qtd_loops)):
                status_box.info(f"⏳ Processando e extraindo página {i+1} de {int(qtd_loops)}...")

                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))

                time.sleep(8)  # Aguarda o download completar

                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))

                progress_bar.progress((i + 1) / int(qtd_loops))
                time.sleep(4)

            # Compactar
            status_box.info("📦 Compactando todos os arquivos extraídos (ZIP)...")
            zip_filename = "/tmp/resultado.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, _, files in os.walk(dl_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            status_box.success("✅ Processamento concluído com sucesso!")

            with open(zip_filename, "rb") as f:
                st.download_button("📥 DOWNLOAD DOS ARQUIVOS (ZIP)", f, "XMLs_MasterSaf.zip", "application/zip")

            driver.quit()

        except Exception as e:
            st.error(f"❌ Ocorreu um erro técnico: {e}")
            if 'driver' in locals():
                driver.quit()