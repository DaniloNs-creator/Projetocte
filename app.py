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

# --- Configuração da página Streamlit ---
st.set_page_config(page_title="Automação MasterSAF", page_icon="🤖")
st.title("Robô de Download de XMLs - MasterSAF")

# --- Interface: Inputs do usuário ---
st.subheader("Configurações da Extração")

# Linha 1: Datas
col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", format="DD/MM/YYYY")
with col2:
    data_fim = st.date_input("Data Final", format="DD/MM/YYYY")

# Linha 2: Configurações de Loop e Paginação
col3, col4 = st.columns(2)
with col3:
    # Opções que normalmente aparecem no dropdown do site (ajuste se necessário)
    itens_por_pagina = st.selectbox("Itens por página", ["50", "100", "200", "500"], index=2)
with col4:
    # Campo para o usuário definir quantas vezes o loop vai rodar (padrão 65)
    qtd_loops = st.number_input("Quantas páginas processar (loops)?", min_value=1, max_value=500, value=65, step=1)

# --- Funções Auxiliares (Prevenção de Erros Headless) ---
def force_click(driver, element):
    """Força o clique via JavaScript, ignorando telas de carregamento sobrepostas."""
    driver.execute_script("arguments[0].click();", element)

def scroll_to_element(driver, element):
    """Centraliza a tela no elemento para garantir que ele esteja visível."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

# --- Lógica Principal de Automação ---
def executar_automacao(dt_ini_str, dt_fim_str, num_itens_pag, num_loops):
    # Pasta temporária segura para os downloads
    temp_download_dir = tempfile.mkdtemp()

    # Configurações do Chrome Headless para servidores na nuvem
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--window-size=1920,1080") 
    
    # Redirecionar downloads para a pasta temporária
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
        # Busca as credenciais de forma segura (configurado no Secrets do Streamlit Cloud)
        usuario = st.secrets["mastersaf"]["username"]
        senha = st.secrets["mastersaf"]["password"]

        # --- 1. Login ---
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        user = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]')))
        user.send_keys(usuario)
        
        pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        pwd.send_keys(senha)
        pwd.send_keys(Keys.ENTER)
        
        time.sleep(5)

        # --- 2. Navegação para Receptor CTEs ---
        receptor = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')))
        force_click(driver, receptor)
        
        time.sleep(5)

        # --- 3. Filtro de Datas ---
        input_dt_ini = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="consultaDataInicial"]')))
        driver.execute_script(f"arguments[0].value = '{dt_ini_str}';", input_dt_ini)

        input_dt_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        driver.execute_script(f"arguments[0].value = '{dt_fim_str}';", input_dt_fim)
        
        input_dt_fim.send_keys(Keys.ENTER)
        time.sleep(4)

        # --- 4. Configurar itens por página (Dinâmico) ---
        select_pag_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')))
        scroll_to_element(driver, select_pag_element)
        
        select = Select(select_pag_element)
        select.select_by_visible_text(num_itens_pag) # Usa o valor selecionado na interface
        time.sleep(4)

        # --- 5. INÍCIO DO LOOP (Dinâmico) ---
        for i in range(num_loops): 
            # Atualiza o status na tela para o usuário saber o progresso
            st.write(f"⏳ Processando página {i+1} de {num_loops}...")

            # Selecionar todos os itens
            checkbox_all = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')))
            scroll_to_element(driver, checkbox_all)
            force_click(driver, checkbox_all)
            time.sleep(3) 
            
            # Clicar em XML Múltiplos
            btn_xml = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="xml_multiplos"]/h3')))
            scroll_to_element(driver, btn_xml)
            force_click(driver, btn_xml)
            time.sleep(6) 
            
            # Desmarcar tudo antes de ir para a próxima página
            force_click(driver, checkbox_all)
            time.sleep(2)
            
            # Ir para próxima página
            try:
                next_btn = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="next_plistagem"]/span')))
                scroll_to_element(driver, next_btn)
                
                # Se o botão estiver desabilitado, significa que chegou na última página antes de completar todos os loops previstos
                if "ui-state-disabled" in next_btn.get_attribute("class"):
                    st.info(f"Fim da listagem atingido na página {i+1}.")
                    break
                    
                force_click(driver, next_btn)
                time.sleep(4) 
            except Exception:
                break
                
        # --- FIM DO LOOP ---
        
        st.write("📦 Compactando arquivos baixados...")
        time.sleep(5) # Aguarda para garantir que o último arquivo terminou de baixar
        
        # Cria o arquivo .zip com todo o conteúdo baixado
        zip_path = shutil.make_archive(
            base_name=tempfile.mktemp(), 
            format='zip', 
            root_dir=temp_download_dir
        )
        
        return zip_path
        
    finally:
        # Garante que o navegador vai fechar e os temporários serão limpos mesmo em caso de erro
        driver.quit() 
        shutil.rmtree(temp_download_dir, ignore_errors=True) 

# --- Ação Final do Usuário ---
st.markdown("---")
if st.button("▶️ Iniciar Extração"):
    dt_ini_formatada = data_inicio.strftime("%d%m%Y")
    dt_fim_formatada = data_fim.strftime("%d%m%Y")

    with st.spinner("Conectando ao sistema e baixando arquivos... Isso pode levar vários minutos."):
        try:
            # Passamos os novos parâmetros dinâmicos para a função
            caminho_arquivo_zip = executar_automacao(dt_ini_formatada, dt_fim_formatada, itens_por_pagina, qtd_loops)
            
            st.success("✅ Automação concluída com sucesso!")
            
            # Habilita o botão de download para o arquivo gerado
            with open(caminho_arquivo_zip, "rb") as file:
                st.download_button(
                    label="⬇️ Baixar Arquivos XML (ZIP)",
                    data=file,
                    file_name="xmls_mastersaf.zip",
                    mime="application/zip"
                )
                
            # Limpa o arquivo zip temporário do servidor
            os.remove(caminho_arquivo_zip)
            
        except Exception as e:
            st.error(f"❌ Ocorreu um erro durante a automação: {e}")
