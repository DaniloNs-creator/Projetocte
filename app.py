import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

# Função para configurar o Selenium no Linux do Streamlit Cloud
def get_driver():
    chrome_options = Options()
    
    # Argumentos essenciais para rodar em servidores sem interface gráfica
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    # Aponta para o navegador e driver instalados pelo packages.txt no servidor
    chrome_options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=chrome_options)

# Interface Principal e Execução
if st.sidebar.button("🚀 Iniciar Automação"):
    if not usuario or not senha:
        st.error("Por favor, preencha o usuário e a senha na barra lateral.")
    else:
        progress_bar = st.progress(0)
        
        with st.status("Executando automação...", expanded=True) as status:
            try:
                st.write("Iniciando navegador em modo headless...")
                driver = get_driver()
                
                st.write("Acessando MasterSAF...")
                driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
                time.sleep(2)
                
                # Login
                st.write("Realizando login...")
                driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').click()
                driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
                
                driver.find_element(By.XPATH, '//*[@id="senha"]').click()
                driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
                
                driver.find_element(By.XPATH, '//*[@id="enter"]').click()
                time.sleep(3)
                
                st.write("Navegando até a Listagem de Receptor CTEs...")
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
                time.sleep(3)
                
                st.write("Atualizando listagem...")
                driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
                time.sleep(3)
                
                # Seleção de exibição (Option 5)
                st.write("Ajustando visualização da tabela...")
                driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select').click()
                time.sleep(1)
                driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
                time.sleep(3)
                
                # Loop de Downloads
                st.write(f"Iniciando rotina de downloads para {int(qtd_loops)} página(s)...")
                for i in range(int(qtd_loops)):
                    st.write(f"Processando página {i+1}...")
                    
                    driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
                    time.sleep(3)
                    
                    driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
                    time.sleep(3)
                    
                    driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]').click()
                    time.sleep(2)
                    
                    # Desmarcar e ir para Próxima Página
                    driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
                    time.sleep(1)
                    
                    driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span').click()
                    
                    # Atualiza a barra de progresso na tela do Streamlit
                    progresso = (i + 1) / int(qtd_loops)
                    progress_bar.progress(progresso)
                    
                    time.sleep(4)
                
                status.update(label="✅ Automação Finalizada!", state="complete", expanded=False)
                st.success("Processo concluído com sucesso!")
                
            except Exception as e:
                status.update(label="❌ Erro na automação", state="error", expanded=True)
                st.error(f"Ocorreu um erro: {e}")
                
            finally:
                if 'driver' in locals():
                    driver.quit()
