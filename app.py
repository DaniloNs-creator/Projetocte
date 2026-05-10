import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Configuração da Página
st.set_page_config(page_title="MasterSAF Automation", page_icon="🤖", layout="wide")

st.title("🤖 MasterSAF - Automação de XML")
st.markdown("Preencha os dados abaixo para iniciar o processo de download em massa.")

# Barra Lateral com Configurações
st.sidebar.header("Configurações de Acesso")
usuario = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")

st.sidebar.divider()

st.sidebar.header("Parâmetros de Busca")
data_ini = st.sidebar.text_input("Data Inicial", value="08/05/2026")
data_fin = st.sidebar.text_input("Data Final", value="08/05/2026")
qtd_loops = st.sidebar.number_input("Quantidade de Páginas (Loops)", min_value=1, value=5)

# Função para configurar o Selenium
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Essencial para rodar na Nuvem (Streamlit Cloud)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Localmente o webdriver-manager resolve, no deploy o Streamlit usa o driver do sistema
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

# Interface Principal
if st.sidebar.button("🚀 Iniciar Automação"):
    if not usuario or not senha:
        st.error("Por favor, preencha o usuário e a senha.")
    else:
        log_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        with st.status("Executando automação...", expanded=True) as status:
            try:
                st.write("Iniciando navegador em modo headless...")
                driver = get_driver()
                
                st.write("Acessando MasterSAF...")
                driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
                time.sleep(2)
                
                # Login
                driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
                driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
                driver.find_element(By.XPATH, '//*[@id="enter"]').click()
                time.sleep(3)
                
                st.write("Navegando até Receptor CTEs...")
                driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a').click()
                time.sleep(3)
                
                # Datas
                st.write(f"Filtrando datas: {data_ini} até {data_fin}")
                campo_ini = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
                campo_ini.click()
                campo_ini.send_keys(Keys.CONTROL, 'a')
                campo_ini.send_keys(data_ini)
                
                campo_fin = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
                campo_fin.click()
                campo_fin.send_keys(Keys.CONTROL, 'a')
                campo_fin.send_keys(data_fin)
                time.sleep(2)
                
                driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
                time.sleep(3)
                
                # Seleção de exibição
                driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
                time.sleep(3)
                
                # Loop de Downloads
                for i in range(int(qtd_loops)):
                    st.write(f"Processando página {i+1} de {qtd_loops}...")
                    
                    driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
                    time.sleep(2)
                    driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
                    time.sleep(2)
                    driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]').click()
                    time.sleep(2)
                    
                    # Desmarcar e Próximo
                    driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
                    driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span').click()
                    
                    # Atualiza progresso na tela
                    progresso = (i + 1) / qtd_loops
                    progress_bar.progress(progresso)
                    time.sleep(3)
                
                status.update(label="✅ Automação Finalizada!", state="complete", expanded=False)
                st.success("Processo concluído com sucesso!")
                driver.quit()

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
                if 'driver' in locals():
                    driver.quit()
