import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import tempfile
import shutil
import os

# Configuração da página Streamlit
st.set_page_config(page_title="Automação MasterSAF", page_icon="🤖")

st.title("Robô de Download de XMLs - MasterSAF")

# Inputs do usuário na interface
col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", format="DD/MM/YYYY")
with col2:
    data_fim = st.date_input("Data Final", format="DD/MM/YYYY")

def executar_automacao(dt_ini_str, dt_fim_str):
    # 1. Cria uma pasta temporária segura no servidor para armazenar os downloads
    temp_download_dir = tempfile.mkdtemp()

    # 2. Configurações do Chrome (Essencial para rodar no Streamlit Cloud)
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Roda sem abrir a janela visual
    chrome_options.add_argument("--no-sandbox") # Necessário para rodar no Linux container
    chrome_options.add_argument("--disable-dev-shm-usage") # Evita travamentos por falta de memória
    chrome_options.add_argument("--window-size=1920,1080") # Garante que os elementos estarão visíveis na tela virtual
    
    # Preferências para baixar arquivos automaticamente na pasta temporária, sem pedir confirmação
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Inicia o WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # Acessa as credenciais seguras configuradas no secrets.toml
        usuario = st.secrets["mastersaf"]["username"]
        senha = st.secrets["mastersaf"]["password"]

        # --- Login ---
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        user = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]')))
        user.send_keys(usuario)
        
        pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        pwd.send_keys(senha)
        pwd.send_keys(Keys.ENTER)
        
        time.sleep(5)

        # --- Navegação para Receptor CTEs ---
        receptor = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')))
        receptor.click()
        
        time.sleep(5)

        # --- Filtro de Datas ---
        input_dt_ini = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="consultaDataInicial"]')))
        input_dt_ini.click()
        input_dt_ini.send_keys(Keys.CONTROL + "a") # Seleciona tudo para sobrescrever
        input_dt_ini.send_keys(dt_ini_str) # Envia a data formatada

        input_dt_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        input_dt_fim.click()
        input_dt_fim.send_keys(dt_fim_str) # Envia a data formatada
        input_dt_fim.send_keys(Keys.ENTER)
        
        time.sleep(2)
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ENTER)
        time.sleep(2)

        # --- Configurar 200 itens por página ---
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.CONTROL + Keys.END)
        time.sleep(2)
        
        select_pag = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')))
        select_pag.click()
        select_pag.send_keys("200")
        select_pag.send_keys(Keys.ENTER)
        
        time.sleep(3)

        # --- INÍCIO DO LOOP ---
        # Removi o limite de 65 rígido e coloquei um limite de segurança (ex: 100). 
        # Ele vai rodar enquanto houver o botão 'Próximo'.
        for i in range(100): 
            # Como roda em background no servidor, atualizamos o status na interface do usuário (não no terminal)
            st.write(f"⏳ Processando página {i+1}...")

            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.CONTROL + Keys.HOME)
            wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))).click()
            
            time.sleep(6)
            
            driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
            time.sleep(5)
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ENTER)
            
            driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
            time.sleep(2)
            
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.CONTROL + Keys.END)
            time.sleep(2)
            
            try:
                next_btn = driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span')
                # Verifica se o botão está desabilitado (fim da lista)
                if "ui-state-disabled" in next_btn.get_attribute("class"):
                    break
                next_btn.click()
            except Exception:
                break # Sai do loop se der erro ao achar o botão
                
        # --- FIM DO LOOP ---
        
        # Espera um pouco extra para garantir que os últimos downloads terminem
        time.sleep(10)
        
        # Cria um arquivo ZIP contendo tudo que foi baixado na pasta temporária
        zip_path = shutil.make_archive(
            base_name=tempfile.mktemp(), 
            format='zip', 
            root_dir=temp_download_dir
        )
        
        return zip_path
        
    finally:
        driver.quit() # É vital fechar o driver para não consumir toda a memória do servidor
        # Remove a pasta temporária do servidor para economizar espaço
        shutil.rmtree(temp_download_dir, ignore_errors=True) 

# --- Interface de Ação ---
if st.button("Iniciar Extração"):
    # Formata as datas no padrão que o site MasterSAF espera (DDMMYYYY, sem barras)
    dt_ini_formatada = data_inicio.strftime("%d%m%Y")
    dt_fim_formatada = data_fim.strftime("%d%m%Y")

    # st.spinner cria a animação de carregamento (rodando em background) até o fim do processo
    with st.spinner("Conectando ao sistema e baixando arquivos... Isso pode levar vários minutos."):
        try:
            caminho_arquivo_zip = executar_automacao(dt_ini_formatada, dt_fim_formatada)
            
            # Quando a função terminar, a animação some e o botão de download aparece
            st.success("Automação concluída com sucesso!")
            
            with open(caminho_arquivo_zip, "rb") as file:
                btn = st.download_button(
                    label="Baixar Arquivos XML (ZIP)",
                    data=file,
                    file_name="xmls_mastersaf.zip",
                    mime="application/zip"
                )
                
            # Limpa o arquivo zip residual do servidor após gerar o botão
            os.remove(caminho_arquivo_zip)
            
        except Exception as e:
            st.error(f"Ocorreu um erro durante a automação: {e}")
