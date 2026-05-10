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

# Configuração da página (DEVE ser a primeira linha do Streamlit)
st.set_page_config(page_title="Portal MasterSAF", page_icon="🏢", layout="wide")

# ==========================================
# LAYOUT PROFISSIONAL (CSS E HTML INJETADO)
# ==========================================
st.markdown("""
    <style>
        /* Oculta os menus padrão e rodapé do Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Cor de fundo principal mais suave */
        .stApp {
            background-color: #f8f9fa;
        }
        
        /* Estilização do Cabeçalho Customizado */
        .custom-header {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 1.8rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: center;
        }
        .custom-header h1 {
            margin: 0;
            font-size: 2.2rem;
            font-weight: 600;
        }
        .custom-header p {
            margin: 5px 0 0 0;
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        /* Estilização dos Botões */
        .stButton>button {
            width: 100%;
            background-color: #2a5298;
            color: white;
            border-radius: 6px;
            padding: 0.6rem;
            font-weight: bold;
            border: none;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #1e3c72;
            box-shadow: 0 4px 12px rgba(42, 82, 152, 0.4);
            color: #ffffff;
            transform: translateY(-2px);
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            box-shadow: 2px 0 5px rgba(0,0,0,0.05);
        }
    </style>
    
    <div class="custom-header">
        <h1>🏢 Portal Automação MasterSAF</h1>
        <p>Extração e Download em Massa de Arquivos XML (CT-e)</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# BARRA LATERAL (CONFIGURAÇÕES)
# ==========================================
st.sidebar.markdown("### 🔐 Credenciais de Acesso")
usuario = st.sidebar.text_input("Usuário MasterSAF")
senha = st.sidebar.text_input("Senha MasterSAF", type="password")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Parâmetros de Filtro")
data_ini = st.sidebar.text_input("Data Inicial", value="08/05/2026")
data_fin = st.sidebar.text_input("Data Final", value="08/05/2026")

# Permitindo até 1000 loops sem quebrar a UI
qtd_loops = st.sidebar.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5)

# ==========================================
# TUNING DO DRIVER PARA SUPORTAR 1000 LOOPS
# ==========================================
def get_driver(download_path):
    chrome_options = Options()
    
    # Argumentos essenciais de headless
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920x1080")
    
    # OTIMIZAÇÕES DE MEMÓRIA PARA LOOPS LONGOS (Evita travamentos)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage") # Usa disco no lugar da RAM (crucial para nuvem)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--js-flags=--expose-gc") # Permite coleta de lixo de memória do JS
    
    # Configuração de diretório de download
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": False # Evita pausas em verificações de arquivos
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.binary_location = "/usr/bin/chromium"
    
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)

# ==========================================
# LÓGICA PRINCIPAL MANTIDA INTACTA
# ==========================================
if st.sidebar.button("🚀 Iniciar Processamento"):
    if not usuario or not senha:
        st.error("⚠️ Atenção: Preencha o usuário e a senha para continuar.")
    else:
        # Preparar pastas de trabalho
        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path): 
            shutil.rmtree(dl_path)
        os.makedirs(dl_path)
        
        # Componentes visuais do Streamlit
        status_box = st.info("Inicializando ambiente e navegador...")
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
                # Substitui apenas o texto do quadro, sem criar novas linhas na tela
                status_box.info(f"⏳ Processando e extraindo página {i+1} de {int(qtd_loops)}...")
                
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                
                time.sleep(8) # Aguarda o download completar
                
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))
                
                # Atualiza a barra
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
            
            # Botão de download estilizado gerado
            with open(zip_filename, "rb") as f:
                st.download_button("📥 DOWNLOAD DOS ARQUIVOS (ZIP)", f, "XMLs_MasterSaf.zip", "application/zip")
            
            driver.quit()
            
        except Exception as e:
            st.error(f"❌ Ocorreu um erro técnico: {e}")
            if 'driver' in locals(): driver.quit()
