import streamlit as st
import os
import shutil  # <-- Adicionado aqui para corrigir o erro
import zipfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Configuração da página
st.set_page_config(page_title="MasterSAF Automação", page_icon="🤖", layout="wide")

st.title("🤖 MasterSAF - Automação de Downloads XML")
st.markdown("Preencha as credenciais na barra lateral para iniciar.")

# Barra Lateral
st.sidebar.header("Configurações")
usuario = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")
data_ini = st.sidebar.text_input("Data Inicial", value="08/05/2026")
data_fin = st.sidebar.text_input("Data Final", value="08/05/2026")
qtd_loops = st.sidebar.number_input("Qtd. Páginas (Loops)", min_value=1, value=5)

# Configuração do Driver
def get_driver(download_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    # Define o diretório de download
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)

# Ação principal
if st.sidebar.button("🚀 Iniciar Automação"):
    if not usuario or not senha:
        st.error("Preencha usuário e senha!")
    else:
        # Preparar pastas
        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path): 
            shutil.rmtree(dl_path)
        os.makedirs(dl_path)
        
        status_text = st.empty()
        progress = st.progress(0)
        
        try:
            status_text.info("Iniciando navegador...")
            driver = get_driver(dl_path)
            
            # Login
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="enter"]'))
            time.sleep(4)
            
            # Navegação
            status_text.info("Acessando listagem...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(3)
            
            # Datas
            for xpath, val in [('//*[@id="consultaDataInicial"]', data_ini), ('//*[@id="consultaDataFinal"]', data_fin)]:
                el = driver.find_element(By.XPATH, xpath)
                el.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
                el.send_keys(val)
            
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
            time.sleep(3)
            
            # Seleção de visualização
            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
            time.sleep(3)
            
            # Loop de Downloads
            for i in range(int(qtd_loops)):
                status_text.write(f"Processando página {i+1}...")
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                
                time.sleep(8) # Aguarda o download completar
                
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))
                progress.progress((i + 1) / int(qtd_loops))
                time.sleep(4)

            # Compactar
            status_text.info("Compactando arquivos...")
            zip_filename = "/tmp/resultado.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, _, files in os.walk(dl_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)
            
            st.success("Automação finalizada!")
            with open(zip_filename, "rb") as f:
                st.download_button("📥 BAIXAR XMLs (ZIP)", f, "XMLs_MasterSaf.zip", "application/zip")
            
            driver.quit()
            
        except Exception as e:
            st.error(f"Erro: {e}")
            if 'driver' in locals(): driver.quit()
