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

# ==========================================
# CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="MasterSAF Automator", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# CSS AVANÇADO (UI/UX)
# ==========================================
st.markdown("""
    <style>
        /* Oculta elementos nativos do Streamlit para visual de App independente */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Fundo principal e tipografia */
        .stApp {
            background-color: #f4f7f6;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
        
        /* Cabeçalho principal com gradiente */
        .hero-header {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            text-align: left;
        }
        .hero-header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .hero-header p {
            margin: 8px 0 0 0;
            font-size: 1.1rem;
            color: #e0e0e0;
        }

        /* Estilo dos Cards de Métrica nativos do Streamlit */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }

        /* Botão de Ação Principal */
        .stButton>button {
            background-color: #0066cc;
            color: white;
            font-weight: 600;
            font-size: 1.1rem;
            padding: 0.75rem 0;
            border-radius: 8px;
            border: none;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #004c99;
            box-shadow: 0 6px 15px rgba(0, 102, 204, 0.4);
            transform: translateY(-2px);
            color: white;
        }
        
        /* Estilo da Sidebar */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #eaeaea;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# BARRA LATERAL (CREDENCIAIS OCULTAS)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=60) # Ícone decorativo genérico
    st.markdown("## 🔐 Autenticação")
    st.markdown("Insira seus dados do MasterSAF.")
    usuario = st.text_input("Usuário", placeholder="Digite seu login")
    senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
    
    st.markdown("---")
    st.markdown("<small>Desenvolvido para extração de alto volume (Até 1000 páginas).</small>", unsafe_allow_html=True)

# ==========================================
# PAINEL CENTRAL (UI PRINCIPAL)
# ==========================================
# Cabeçalho customizado
st.markdown("""
    <div class="hero-header">
        <h1>⚡ Portal MasterSAF - Automação</h1>
        <p>Motor de Extração de Arquivos XML de CT-e em Massa</p>
    </div>
""", unsafe_allow_html=True)

# Container de Configurações
st.markdown("### ⚙️ Parâmetros da Extração")
with st.container():
    # Usando 3 colunas para um layout responsivo lado a lado
    col1, col2, col3 = st.columns(3)
    with col1:
        data_ini = st.text_input("📅 Data Inicial", value="08/05/2026")
    with col2:
        data_fin = st.text_input("📅 Data Final", value="08/05/2026")
    with col3:
        qtd_loops = st.number_input("🔁 Páginas (Loops)", min_value=1, max_value=1000, value=5)

st.markdown("<br>", unsafe_allow_html=True) # Espaçamento

# ==========================================
# FUNÇÃO DO DRIVER (LÓGICA INTACTA)
# ==========================================
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
        "safebrowsing.enabled": False 
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)

# ==========================================
# EXECUÇÃO E DASHBOARD DINÂMICO
# ==========================================
if st.button("🚀 INICIAR PROCESSAMENTO", use_container_width=True):
    if not usuario or not senha:
        st.error("⚠️ Erro: As credenciais na barra lateral estão vazias. Preencha Usuário e Senha.")
    else:
        # Criação dos "Slots" vazios na tela para atualizar dinamicamente
        st.markdown("---")
        st.markdown("### 📊 Status da Operação")
        
        # Linha de Métricas
        metrica_col1, metrica_col2 = st.columns(2)
        card_paginas = metrica_col1.empty()
        card_status = metrica_col2.empty()
        
        # Barra de Progresso
        progress_bar = st.progress(0)
        
        # Log detalhado
        log_box = st.empty()

        # Configuração inicial do Dashboard
        card_paginas.metric(label="Páginas Concluídas", value=f"0 / {int(qtd_loops)}")
        card_status.metric(label="Status Atual", value="Preparando ambiente...")
        
        # Pastas
        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path): shutil.rmtree(dl_path)
        os.makedirs(dl_path)
        
        try:
            driver = get_driver(dl_path)
            
            # Login
            log_box.info("Acessando o sistema MasterSAF e realizando autenticação...")
            card_status.metric(label="Status Atual", value="Autenticando...")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="enter"]'))
            time.sleep(4)
            
            # Navegação
            log_box.info("Navegando até o módulo de CT-es...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
            time.sleep(3)
            
            # Datas
            card_status.metric(label="Status Atual", value="Aplicando Filtros...")
            for xpath, val in [('//*[@id="consultaDataInicial"]', data_ini), ('//*[@id="consultaDataFinal"]', data_fin)]:
                el = driver.find_element(By.XPATH, xpath)
                el.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
                el.send_keys(val)
            
            log_box.info("Atualizando base de dados com as datas informadas...")
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]'))
            time.sleep(3)
            
            # Seleção de visualização
            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
            time.sleep(3)
            
            # Loop de Downloads
            card_status.metric(label="Status Atual", value="Extraindo Arquivos", delta="Executando")
            for i in range(int(qtd_loops)):
                # Atualiza as métricas e logs em tempo real
                card_paginas.metric(label="Páginas Concluídas", value=f"{i+1} / {int(qtd_loops)}")
                log_box.info(f"⏳ Processando e extraindo página {i+1} de {int(qtd_loops)}...")
                
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]'))
                
                time.sleep(8) 
                
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
                driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span'))
                
                progress_bar.progress((i + 1) / int(qtd_loops))
                time.sleep(4)

            # Compactar
            card_status.metric(label="Status Atual", value="Compactando Arquivos", delta="Finalizando", delta_color="normal")
            log_box.info("📦 Criando arquivo ZIP...")
            zip_filename = "/tmp/resultado.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, _, files in os.walk(dl_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)
            
            # Finalização Visual
            card_status.metric(label="Status Atual", value="Concluído! ✅", delta="Pronto")
            log_box.success("🎉 Processamento finalizado com sucesso! Seu arquivo está pronto para download abaixo.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Botão de download
            with open(zip_filename, "rb") as f:
                st.download_button(
                    label="📥 DOWNLOAD DOS ARQUIVOS (ZIP)", 
                    data=f, 
                    file_name="XMLs_MasterSaf.zip", 
                    mime="application/zip",
                    use_container_width=True
                )
            
            driver.quit()
            
        except Exception as e:
            card_status.metric(label="Status Atual", value="Falha Crítica ❌", delta="Erro", delta_color="inverse")
            log_box.error(f"Ocorreu um erro técnico: {e}")
            if 'driver' in locals(): driver.quit()
