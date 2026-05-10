import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import tempfile
import shutil
import os
from datetime import datetime
import zipfile

# --- Configuração da página Streamlit ---
st.set_page_config(
    page_title="Automação MasterSAF", 
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo CSS personalizado para animações
st.markdown("""
<style>
    /* Animação de pulsação para o botão de download */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .download-button {
        animation: pulse 2s infinite;
        background: linear-gradient(45deg, #4CAF50, #45a049) !important;
        color: white !important;
        padding: 15px 30px !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }
    
    /* Animação de carregamento */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    
    /* Barra de progresso animada */
    .progress-bar {
        width: 100%;
        height: 30px;
        background: linear-gradient(90deg, #4CAF50, #45a049);
        border-radius: 15px;
        transition: width 0.3s ease;
    }
    
    /* Contador animado */
    @keyframes countUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .counter-animation {
        animation: countUp 0.5s ease-out;
        font-size: 48px;
        font-weight: bold;
        color: #4CAF50;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Título principal com emoji animado
st.markdown("""
<h1 style='text-align: center; color: #2E86C1;'>
    🤖 Robô de Download de XMLs - MasterSAF
</h1>
""", unsafe_allow_html=True)

st.markdown("---")

# --- Interface: Inputs do usuário ---
st.subheader("📋 Configurações da Extração")

col1, col2, col3 = st.columns(3)
with col1:
    data_inicio = st.date_input(
        "📅 Data Inicial", 
        format="DD/MM/YYYY",
        help="Selecione a data inicial para filtro"
    )
with col2:
    data_fim = st.date_input(
        "📅 Data Final", 
        format="DD/MM/YYYY",
        help="Selecione a data final para filtro"
    )
with col3:
    itens_por_pagina = st.selectbox(
        "📄 Itens por página", 
        ["50", "100", "200", "500"], 
        index=2,
        help="Quantidade de registros exibidos por página"
    )

qtd_loops = st.number_input(
    "🔄 Quantas páginas processar (loops)?", 
    min_value=1, 
    max_value=500, 
    value=65, 
    step=1,
    help="Número máximo de páginas a serem processadas"
)

# --- Funções Auxiliares ---
def force_click(driver, element):
    """Força o clique via JavaScript quando o clique normal não funciona."""
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        st.warning(f"⚠️ Clique forçado falhou: {e}")
        return False

def scroll_to_element(driver, element):
    """Centraliza a tela no elemento para garantir visibilidade."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
        time.sleep(0.5)
    except Exception as e:
        st.warning(f"⚠️ Scroll falhou: {e}")

def criar_barra_progresso_animada(progresso, total):
    """Cria HTML para uma barra de progresso animada."""
    percentual = min(100, int((progresso / total) * 100))
    return f"""
    <div style="background: #e0e0e0; border-radius: 15px; height: 30px; margin: 10px 0;">
        <div class="progress-bar" style="width: {percentual}%; display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: bold;">{percentual}%</span>
        </div>
    </div>
    """

def animar_contador_xmls(total):
    """Cria animação para o contador de XMLs."""
    return f"""
    <div class="counter-animation">
        📦 {total} XMLs encontrados
    </div>
    """

# --- Lógica Principal de Automação ---
@st.cache_resource
def get_chrome_driver():
    """
    Configura e retorna uma instância do ChromeDriver usando webdriver-manager.
    Isso resolve o problema de não ter os drivers instalados no ambiente de deploy.
    """
    try:
        # Configura o serviço do ChromeDriver com gerenciamento automático
        service = Service(ChromeDriverManager().install())
        return service
    except Exception as e:
        st.error(f"❌ Erro ao configurar ChromeDriver: {e}")
        return None

def executar_automacao(dt_ini_str, dt_fim_str, num_itens_pag, num_loops, status_container, progress_bar_container):
    """
    Executa a automação completa de download dos XMLs.
    """
    temp_download_dir = tempfile.mkdtemp(prefix="xml_downloads_")
    total_xmls_baixados = 0
    paginas_processadas = 0
    
    # Configurações do Chrome para ambiente headless (sem interface gráfica)
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Nova sintaxe para headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    # Configurações específicas para download
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    driver = None
    try:
        # Obtém o serviço do ChromeDriver
        chrome_service = get_chrome_driver()
        if not chrome_service:
            raise Exception("Não foi possível configurar o ChromeDriver")
        
        # Inicializa o driver
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        wait = WebDriverWait(driver, 20)
        
        # Credenciais (devem ser configuradas nos secrets do Streamlit)
        usuario = st.secrets["mastersaf"]["username"]
        senha = st.secrets["mastersaf"]["password"]
        
        # --- Fase 1: Login ---
        status_container.info("🔐 Realizando login no sistema...")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
        time.sleep(3)
        
        # Preenche usuário
        user = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]')))
        user.clear()
        user.send_keys(usuario)
        time.sleep(1)
        
        # Preenche senha e faz login
        pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        pwd.clear()
        pwd.send_keys(senha)
        pwd.send_keys(Keys.ENTER)
        
        time.sleep(5)
        status_container.success("✅ Login realizado com sucesso!")
        
        # --- Fase 2: Navegação para Receptor CTEs ---
        status_container.info("📂 Navegando para Receptor CTEs...")
        receptor = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')))
        force_click(driver, receptor)
        time.sleep(5)
        status_container.success("✅ Página de CTEs acessada!")
        
        # --- Fase 3: Aplicar Filtros de Data ---
        status_container.info("📅 Aplicando filtros de data...")
        
        # Data inicial
        input_dt_ini = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="consultaDataInicial"]')))
        driver.execute_script(f"arguments[0].value = '{dt_ini_str}';", input_dt_ini)
        time.sleep(1)
        
        # Data final
        input_dt_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        driver.execute_script(f"arguments[0].value = '{dt_fim_str}';", input_dt_fim)
        input_dt_fim.send_keys(Keys.ENTER)
        
        time.sleep(4)
        status_container.success(f"✅ Filtros aplicados: {dt_ini_str} até {dt_fim_str}")
        
        # --- Fase 4: Configurar itens por página ---
        status_container.info(f"⚙️ Configurando {num_itens_pag} itens por página...")
        select_pag_element = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
        ))
        scroll_to_element(driver, select_pag_element)
        
        select = Select(select_pag_element)
        select.select_by_visible_text(num_itens_pag)
        time.sleep(4)
        
        # Tenta obter informações de paginação
        try:
            info_paginacao = driver.find_element(By.CLASS_NAME, "ui-paging-info").text
            if info_paginacao:
                status_container.info(f"📊 {info_paginacao}")
        except:
            pass
        
        # --- Fase 5: Loop de Processamento ---
        status_container.info("🔄 Iniciando processamento das páginas...")
        
        for i in range(num_loops):
            paginas_processadas = i + 1
            
            # Atualiza barra de progresso
            with progress_bar_container:
                st.markdown(
                    criar_barra_progresso_animada(paginas_processadas, num_loops), 
                    unsafe_allow_html=True
                )
            
            # Atualiza status
            status_container.info(
                f"⏳ Processando página {paginas_processadas} de {num_loops} | "
                f"XMLs encontrados: {total_xmls_baixados}"
            )
            
            try:
                # Selecionar todos os checkboxes da página
                checkbox_all = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                ))
                scroll_to_element(driver, checkbox_all)
                force_click(driver, checkbox_all)
                time.sleep(2)
                
                # Contar XMLs nesta página
                itens_selecionados = driver.find_elements(By.XPATH, '//td//input[@type="checkbox"]')
                qtd_nesta_pagina = len(itens_selecionados)
                total_xmls_baixados += qtd_nesta_pagina
                
                # Atualiza contador animado
                with progress_bar_container:
                    st.markdown(animar_contador_xmls(total_xmls_baixados), unsafe_allow_html=True)
                
                status_container.success(
                    f"✅ Página {paginas_processadas}: {qtd_nesta_pagina} XMLs selecionados | "
                    f"Total acumulado: {total_xmls_baixados}"
                )
                
                # Clicar em "XML Múltiplos" para download
                btn_xml = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="xml_multiplos"]/h3')
                ))
                scroll_to_element(driver, btn_xml)
                force_click(driver, btn_xml)
                time.sleep(6)
                
                # Desmarcar todos para próxima iteração
                force_click(driver, checkbox_all)
                time.sleep(2)
                
                # Navegar para próxima página
                if i < num_loops - 1:  # Não tenta ir para próxima na última iteração
                    try:
                        next_btn = wait.until(EC.presence_of_element_located(
                            (By.XPATH, '//*[@id="next_plistagem"]/span')
                        ))
                        scroll_to_element(driver, next_btn)
                        
                        # Verifica se botão está desabilitado
                        if "ui-state-disabled" in next_btn.get_attribute("class"):
                            status_container.info(f"🏁 Última página atingida: {paginas_processadas}")
                            break
                        
                        force_click(driver, next_btn)
                        time.sleep(4)
                    except:
                        status_container.info("🏁 Não foi possível navegar para próxima página. Finalizando.")
                        break
                
            except Exception as e:
                status_container.warning(f"⚠️ Erro na página {paginas_processadas}: {str(e)[:100]}")
                continue
        
        # --- Finalização e Compactação ---
        status_container.info("📦 Compactando arquivos baixados...")
        time.sleep(3)
        
        # Criar arquivo ZIP
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"xmls_mastersaf_{timestamp}"
        zip_path = shutil.make_archive(
            base_name=os.path.join(tempfile.gettempdir(), zip_filename),
            format='zip',
            root_dir=temp_download_dir
        )
        
        status_container.success(
            f"🎉 Extração concluída com sucesso! {total_xmls_baixados} XMLs processados em {paginas_processadas} páginas."
        )
        
        return zip_path, total_xmls_baixados, paginas_processadas
        
    except Exception as e:
        status_container.error(f"❌ Erro na automação: {str(e)}")
        raise e
    finally:
        if driver:
            driver.quit()
        # Limpa diretório temporário após 5 segundos
        try:
            time.sleep(5)
            shutil.rmtree(temp_download_dir, ignore_errors=True)
        except:
            pass

# --- Interface Principal ---
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    iniciar = st.button(
        "▶️ Iniciar Extração", 
        type="primary", 
        use_container_width=True,
        help="Clique para iniciar o processo de extração dos XMLs"
    )

# Container para status e progresso
status_placeholder = st.empty()
progress_placeholder = st.empty()
resultado_placeholder = st.empty()

if iniciar:
    # Validações básicas
    if data_fim < data_inicio:
        st.error("❌ A data final deve ser maior ou igual à data inicial!")
    else:
        # Formata as datas
        dt_ini_formatada = data_inicio.strftime("%d%m%Y")
        dt_fim_formatada = data_fim.strftime("%d%m%Y")
        
        # Mostra spinner inicial
        with st.spinner("🚀 Inicializando automação..."):
            try:
                # Executa a automação
                caminho_arquivo_zip, qtd_total, paginas = executar_automacao(
                    dt_ini_formatada,
                    dt_fim_formatada,
                    itens_por_pagina,
                    qtd_loops,
                    status_placeholder,
                    progress_placeholder
                )
                
                # Exibe resultados finais
                with resultado_placeholder.container():
                    st.markdown("---")
                    st.markdown("## 📊 Resumo da Extração")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📄 Total de XMLs", qtd_total)
                    with col2:
                        st.metric("📑 Páginas Processadas", paginas)
                    with col3:
                        st.metric("🗓️ Período", f"{data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}")
                    
                    st.markdown("---")
                    
                    # Botão de download com animação
                    with open(caminho_arquivo_zip, "rb") as file:
                        st.download_button(
                            label=f"⬇️ BAIXAR ARQUIVOS (ZIP - {qtd_total} XMLs)",
                            data=file,
                            file_name=f"xmls_mastersaf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    # Limpa o arquivo ZIP após disponibilizar
                    try:
                        os.remove(caminho_arquivo_zip)
                    except:
                        pass
                    
            except Exception as e:
                st.error(f"❌ Erro crítico durante a execução: {str(e)}")
                st.info("💡 Verifique suas credenciais e tente novamente.")

# Informações adicionais
st.markdown("---")
with st.expander("ℹ️ Informações e Ajuda"):
    st.markdown("""
    ### Como usar:
    1. **Datas**: Selecione o período desejado para extração
    2. **Itens por página**: Escolha quantos registros por página (200 recomendado)
    3. **Loops**: Número máximo de páginas a processar
    4. **Iniciar**: Clique para começar a extração automática
    
    ### Observações:
    - O processo roda em segundo plano (headless)
    - Os arquivos são compactados em ZIP automaticamente
    - O botão de download aparece quando tudo estiver pronto
    - As credenciais são armazenadas com segurança nos secrets do Streamlit
    
    ### Configuração dos Secrets:
    Crie um arquivo `.streamlit/secrets.toml` com:
    ```toml
    [mastersaf]
    username = "seu_usuario"
    password = "sua_senha"
    ```
    """)

# Rodapé
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Desenvolvido com ❤️ | Versão 2.0</p>", 
    unsafe_allow_html=True
)