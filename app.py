import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import tempfile
import shutil
import os

st.set_page_config(page_title="Automação MasterSAF", page_icon="🤖")
st.title("Robô de Download de XMLs - MasterSAF")

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", format="DD/MM/YYYY")
with col2:
    data_fim = st.date_input("Data Final", format="DD/MM/YYYY")

# Função auxiliar para forçar o clique via JavaScript (Resolve o erro Not Interactable)
def force_click(driver, element):
    driver.execute_script("arguments[0].click();", element)

# Função auxiliar para garantir que o elemento está na tela
def scroll_to_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

def executar_automacao(dt_ini_str, dt_fim_str):
    temp_download_dir = tempfile.mkdtemp()

    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--window-size=1920,1080") 
    
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
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
        receptor = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')))
        force_click(driver, receptor) # Clique forçado
        
        time.sleep(5)

        # --- Filtro de Datas ---
        # Limpar datas usando JS é mais seguro que Control + A
        input_dt_ini = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="consultaDataInicial"]')))
        driver.execute_script(f"arguments[0].value = '{dt_ini_str}';", input_dt_ini)

        input_dt_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        driver.execute_script(f"arguments[0].value = '{dt_fim_str}';", input_dt_fim)
        
        # Enviar enter no campo final para processar a busca
        input_dt_fim.send_keys(Keys.ENTER)
        time.sleep(4)

        # --- Configurar 200 itens por página ---
        select_pag_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')))
        scroll_to_element(driver, select_pag_element)
        
        # Usando a classe Select do próprio Selenium (Mais seguro)
        select = Select(select_pag_element)
        select.select_by_visible_text("200") 
        time.sleep(4)

        # --- INÍCIO DO LOOP ---
        for i in range(100): 
            st.write(f"⏳ Processando página {i+1}...")

            # Selecionar todos os itens (usando force_click)
            checkbox_all = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')))
            scroll_to_element(driver, checkbox_all)
            force_click(driver, checkbox_all)
            
            time.sleep(3) # Aguardar a seleção computar
            
            # Clicar em XML Múltiplos
            btn_xml = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="xml_multiplos"]/h3')))
            scroll_to_element(driver, btn_xml)
            force_click(driver, btn_xml)
            
            time.sleep(6) # Tempo para o site gerar/baixar os XMLs
            
            # Desmarcar tudo antes de ir para a próxima página
            force_click(driver, checkbox_all)
            time.sleep(2)
            
            # Ir para próxima página
            try:
                next_btn = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="next_plistagem"]/span')))
                scroll_to_element(driver, next_btn)
                
                # Verifica se o botão tem a classe que indica fim das páginas
                if "ui-state-disabled" in next_btn.get_attribute("class"):
                    break
                    
                force_click(driver, next_btn)
                time.sleep(4) # Tempo para carregar a nova página de tabela
            except Exception as e:
                print("Fim da lista ou erro ao buscar botão de próximo:", e)
                break
                
        # --- FIM DO LOOP ---
        
        time.sleep(10)
        
        zip_path = shutil.make_archive(
            base_name=tempfile.mktemp(), 
            format='zip', 
            root_dir=temp_download_dir
        )
        
        return zip_path
        
    finally:
        driver.quit() 
        shutil.rmtree(temp_download_dir, ignore_errors=True) 

# --- Interface de Ação ---
if st.button("Iniciar Extração"):
    dt_ini_formatada = data_inicio.strftime("%d%m%Y")
    dt_fim_formatada = data_fim.strftime("%d%m%Y")

    with st.spinner("Conectando ao sistema e baixando arquivos... Isso pode levar vários minutos."):
        try:
            caminho_arquivo_zip = executar_automacao(dt_ini_formatada, dt_fim_formatada)
            st.success("Automação concluída com sucesso!")
            
            with open(caminho_arquivo_zip, "rb") as file:
                btn = st.download_button(
                    label="Baixar Arquivos XML (ZIP)",
                    data=file,
                    file_name="xmls_mastersaf.zip",
                    mime="application/zip"
                )
                
            os.remove(caminho_arquivo_zip)
            
        except Exception as e:
            st.error(f"Ocorreu um erro durante a automação: {e}")
