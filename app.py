import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import tempfile
import shutil
import os
import glob

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
    """Força o clique via JavaScript para evitar erros de elemento não clicável."""
    driver.execute_script("arguments[0].click();", element)

def scroll_to_element(driver, element):
    """Centraliza a tela no elemento."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

def aguardar_downloads(diretorio, timeout=60):
    """
    Trava o código até que todos os downloads da pasta terminem.
    O Chrome cria arquivos terminados em '.crdownload' enquanto baixa.
    """
    segundos_passados = 0
    while segundos_passados < timeout:
        # Verifica se existe algum arquivo temporário de download na pasta
        arquivos_temp = glob.glob(os.path.join(diretorio, '*.crdownload'))
        if not arquivos_temp:
            time.sleep(1) # Dá 1 segundo de margem extra
            return True # Nenhum arquivo baixando, podemos prosseguir!
        time.sleep(1)
        segundos_passados += 1
    return False

# --- Lógica Principal de Automação ---
def executar_automacao(dt_ini_str, dt_fim_str, num_itens_pag, num_loops, status_ui):
    # Cria uma pasta temporária isolada no servidor
    temp_download_dir = tempfile.mkdtemp()
    total_xmls_baixados = 0 

    # --- Configurações vitais para rodar na nuvem (Streamlit Cloud) ---
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Modo invisível mais moderno do Chrome
    chrome_options.add_argument("--no-sandbox") # Essencial para rodar em containers Linux
    chrome_options.add_argument("--disable-dev-shm-usage") # Evita travamento por falta de memória RAM
    chrome_options.add_argument("--window-size=1920,1080") 
    chrome_options.add_argument("--disable-gpu")
    
    # Preferências de download
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False # Evita bloqueios de segurança em arquivos XML
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # O Selenium v4 mais recente cuida do driver, mas na nuvem precisamos garantir as opções
    driver = webdriver.Chrome(options=chrome_options)
    
    # COMANDO CDP: Vital! Sem isso, o Chrome no modo Headless recusa fazer downloads silenciosos.
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": temp_download_dir
    })

    wait = WebDriverWait(driver, 20)

    try:
        usuario = st.secrets["mastersaf"]["username"]
        senha = st.secrets["mastersaf"]["password"]

        status_ui.write("🔑 Fazendo login no MasterSAF...")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        user = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]')))
        user.send_keys(usuario)
        
        pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        pwd.send_keys(senha)
        pwd.send_keys(Keys.ENTER)
        time.sleep(5)

        status_ui.write("🧭 Navegando para Receptor CTEs...")
        receptor = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')))
        force_click(driver, receptor)
        time.sleep(5)

        status_ui.write("📅 Aplicando filtros de data...")
        input_dt_ini = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="consultaDataInicial"]')))
        driver.execute_script(f"arguments[0].value = '{dt_ini_str}';", input_dt_ini)

        input_dt_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        driver.execute_script(f"arguments[0].value = '{dt_fim_str}';", input_dt_fim)
        input_dt_fim.send_keys(Keys.ENTER)
        time.sleep(4)

        status_ui.write(f"⚙️ Configurando exibição para {num_itens_pag} itens...")
        select_pag_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')))
        scroll_to_element(driver, select_pag_element)
        select = Select(select_pag_element)
        select.select_by_visible_text(num_itens_pag) 
        time.sleep(4)

        # --- INÍCIO DO LOOP ---
        for i in range(num_loops): 
            status_ui.write(f"⏳ Processando página {i+1} de {num_loops}...")

            # Selecionar todos os itens
            checkbox_all = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')))
            scroll_to_element(driver, checkbox_all)
            force_click(driver, checkbox_all)
            time.sleep(2) 
            
            # Contagem
            itens_selecionados = driver.find_elements(By.XPATH, '//td//input[@type="checkbox"]')
            qtd_nesta_pagina = len(itens_selecionados)
            total_xmls_baixados += qtd_nesta_pagina
            
            status_ui.write(f"📥 Disparando download de {qtd_nesta_pagina} itens (Total até agora: {total_xmls_baixados})...")

            # Clicar no botão de download (XML Múltiplos)
            btn_xml = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="xml_multiplos"]/h3')))
            scroll_to_element(driver, btn_xml)
            force_click(driver, btn_xml)
            
            # ESPERA INTELIGENTE: Trava o código até os downloads da página acabarem de verdade
            aguardar_downloads(temp_download_dir)
            
            # Desmarcar tudo
            force_click(driver, checkbox_all)
            time.sleep(1)
            
            # Ir para próxima página
            try:
                next_btn = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="next_plistagem"]/span')))
                scroll_to_element(driver, next_btn)
                
                # Se o botão estiver desativado, acabaram as páginas
                if "ui-state-disabled" in next_btn.get_attribute("class"):
                    status_ui.write(f"🏁 Fim da listagem atingido na página {i+1}.")
                    break
                    
                force_click(driver, next_btn)
                time.sleep(4) # Espera a tabela da próxima página carregar
            except Exception:
                break
                
        status_ui.write(f"📦 Compactando todos os {total_xmls_baixados} arquivos...")
        
        # Cria o ZIP a partir da pasta temporária
        zip_path = shutil.make_archive(
            base_name=tempfile.mktemp(), 
            format='zip', 
            root_dir=temp_download_dir
        )
        
        return zip_path, total_xmls_baixados
        
    finally:
        # Garante que o navegador vai fechar e a pasta vai ser apagada mesmo se der erro
        driver.quit() 
        shutil.rmtree(temp_download_dir, ignore_errors=True) 

# --- Ação Final do Usuário ---
st.markdown("---")
if st.button("▶️ Iniciar Extração", type="primary"):
    dt_ini_formatada = data_inicio.strftime("%d%m%Y")
    dt_fim_formatada = data_fim.strftime("%d%m%Y")

    # st.status cria uma caixa sanfona com animação de carregamento
    with st.status("Iniciando o robô... Por favor, aguarde.", expanded=True) as status:
        try:
            caminho_arquivo_zip, qtd_total = executar_automacao(
                dt_ini_formatada, 
                dt_fim_formatada, 
                itens_por_pagina, 
                qtd_loops, 
                status # Passamos o status para ser atualizado lá dentro
            )
            
            # Muda a cor do status para verde quando terminar
            status.update(label=f"Extração finalizada com sucesso! {qtd_total} XMLs processados.", state="complete", expanded=False)
            
            st.success(f"✅ Sucesso! O robô baixou **{qtd_total} arquivos**.")
            
            # Botão de download exibido no final
            with open(caminho_arquivo_zip, "rb") as file:
                st.download_button(
                    label="⬇️ Baixar Arquivos ZIP",
                    data=file,
                    file_name="xmls_mastersaf.zip",
                    mime="application/zip",
                    type="primary"
                )
                
            # Limpa o arquivo zip gerado após a disponibilização do botão
            os.remove(caminho_arquivo_zip)
            
        except Exception as e:
            status.update(label="Ocorreu um erro na automação.", state="error", expanded=True)
            st.error(f"❌ Detalhes do erro: {e}")
