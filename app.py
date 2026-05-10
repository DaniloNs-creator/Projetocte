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

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data Inicial", format="DD/MM/YYYY")
with col2:
    data_fim = st.date_input("Data Final", format="DD/MM/YYYY")

col3, col4 = st.columns(2)
with col3:
    itens_por_pagina = st.selectbox("Itens por página", ["50", "100", "200", "500"], index=2)
with col4:
    qtd_loops = st.number_input("Quantas páginas processar (loops)?", min_value=1, max_value=500, value=65, step=1)

# --- Funções Auxiliares ---
def force_click(driver, element):
    """Força o clique via JavaScript."""
    driver.execute_script("arguments[0].click();", element)

def scroll_to_element(driver, element):
    """Centraliza a tela no elemento."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

# --- Lógica Principal de Automação ---
def executar_automacao(dt_ini_str, dt_fim_str, num_itens_pag, num_loops, container_progresso):
    temp_download_dir = tempfile.mkdtemp()
    total_xmls_baixados = 0  # Inicializa o contador de XMLs

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

        # --- 4. Configurar itens por página ---
        select_pag_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')))
        scroll_to_element(driver, select_pag_element)
        
        select = Select(select_pag_element)
        select.select_by_visible_text(num_itens_pag) 
        time.sleep(4)

        # Tenta pegar a informação de totalização do sistema (opcional, pode não existir no HTML exato)
        try:
            info_paginacao = driver.find_element(By.CLASS_NAME, "ui-paging-info").text
            if info_paginacao:
                st.info(f"📊 Informação do sistema (MasterSAF): {info_paginacao}")
        except Exception:
            pass # Se não encontrar a classe, ignora de forma silenciosa

        # --- 5. INÍCIO DO LOOP ---
        for i in range(num_loops): 
            # Atualiza o texto dinâmico (sobresscreve o anterior em vez de criar novas linhas)
            container_progresso.warning(f"⏳ Processando página {i+1} de {num_loops} | **Total encontrado até agora: {total_xmls_baixados}**")

            # Selecionar todos os itens da tabela
            checkbox_all = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')))
            scroll_to_element(driver, checkbox_all)
            force_click(driver, checkbox_all)
            time.sleep(3) 
            
            # --- CONTAGEM FÍSICA DOS XMLS ---
            # Encontra todos os checkboxes que pertencem às linhas (<td>) para não contar o checkbox mestre (<th>)
            itens_selecionados = driver.find_elements(By.XPATH, '//td//input[@type="checkbox"]')
            qtd_nesta_pagina = len(itens_selecionados)
            total_xmls_baixados += qtd_nesta_pagina
            
            # Atualiza a interface com o novo número computado
            container_progresso.warning(f"⏳ Processando página {i+1} de {num_loops} | **Total encontrado até agora: {total_xmls_baixados}**")

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
                
                if "ui-state-disabled" in next_btn.get_attribute("class"):
                    container_progresso.info(f"Fim da listagem atingido na página {i+1}.")
                    break
                    
                force_click(driver, next_btn)
                time.sleep(4) 
            except Exception:
                break
                
        # --- FIM DO LOOP ---
        
        container_progresso.success(f"📦 Extração finalizada! Compactando {total_xmls_baixados} arquivos...")
        time.sleep(5) 
        
        zip_path = shutil.make_archive(
            base_name=tempfile.mktemp(), 
            format='zip', 
            root_dir=temp_download_dir
        )
        
        return zip_path, total_xmls_baixados
        
    finally:
        driver.quit() 
        shutil.rmtree(temp_download_dir, ignore_errors=True) 

# --- Ação Final do Usuário ---
st.markdown("---")
if st.button("▶️ Iniciar Extração"):
    dt_ini_formatada = data_inicio.strftime("%d%m%Y")
    dt_fim_formatada = data_fim.strftime("%d%m%Y")

    # Cria um espaço vazio (container) que será atualizado em tempo real pela função
    espaco_progresso = st.empty()

    with st.spinner("Conectando ao sistema e aplicando filtros..."):
        try:
            # Chama a função passando o espaço dinâmico
            caminho_arquivo_zip, qtd_total = executar_automacao(
                dt_ini_formatada, 
                dt_fim_formatada, 
                itens_por_pagina, 
                qtd_loops, 
                espaco_progresso # Passando a referência do container do Streamlit
            )
            
            # Mensagem final de sucesso exibindo o total de XMLs encontrados
            st.success(f"✅ Sucesso! O robô localizou e tentou baixar um total de **{qtd_total} XML(s)**.")
            
            with open(caminho_arquivo_zip, "rb") as file:
                st.download_button(
                    label=f"⬇️ Baixar Arquivos (ZIP com {qtd_total} itens)",
                    data=file,
                    file_name="xmls_mastersaf.zip",
                    mime="application/zip"
                )
                
            os.remove(caminho_arquivo_zip)
            
        except Exception as e:
            st.error(f"❌ Ocorreu um erro durante a automação: {e}")
