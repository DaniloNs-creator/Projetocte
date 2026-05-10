"""
downloader.py — Lógica de automação Selenium isolada da interface Streamlit.

Separar o scraping da UI permite:
  • Executar em thread sem travar o Streamlit.
  • Facilitar testes unitários independentes.
  • Trocar o frontend sem reescrever a automação.

Credenciais são lidas de st.secrets (arquivo .streamlit/secrets.toml),
nunca escritas diretamente no código.
"""

import os
import time
import zipfile
import tempfile
import streamlit as st

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager  # baixa o driver automaticamente


# ── URL base do sistema ────────────────────────────────────────────────────
LOGIN_URL = "https://p.dfe.mastersaf.com.br/mvc/login"


def _criar_driver(pasta_download: str) -> webdriver.Chrome:
    """
    Instancia o Chrome em modo headless (sem janela visível).
    O ChromeDriverManager baixa o chromedriver compatível automaticamente,
    eliminando a necessidade de o usuário instalar o driver manualmente.

    Args:
        pasta_download: Caminho absoluto onde os XMLs serão salvos pelo Chrome.

    Returns:
        Instância configurada do webdriver.Chrome.
    """
    opts = Options()

    # ── Modo headless: roda sem abrir janela de navegador ──────────────────
    opts.add_argument("--headless=new")          # headless moderno (Chrome ≥ 112)
    opts.add_argument("--no-sandbox")            # necessário em ambientes Linux/container
    opts.add_argument("--disable-dev-shm-usage") # evita crash por falta de memória compartilhada
    opts.add_argument("--disable-gpu")           # estabilidade em headless
    opts.add_argument("--window-size=1920,1080") # resolução virtual

    # ── Pasta de download automático (Chrome salva sem abrir diálogo) ──────
    prefs = {
        "download.default_directory": pasta_download,
        "download.prompt_for_download": False,  # sem popup "Salvar como"
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    opts.add_experimental_option("prefs", prefs)

    # ChromeDriverManager detecta a versão do Chrome instalado e baixa o driver certo
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    return driver


def _aguardar_downloads(pasta: str, timeout: int = 60) -> list[str]:
    """
    Bloqueia até que todos os arquivos .crdownload (downloads em curso)
    desapareçam da pasta, indicando que o Chrome finalizou os downloads.

    Args:
        pasta: Pasta monitorada.
        timeout: Segundos máximos de espera.

    Returns:
        Lista de caminhos dos arquivos baixados.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        pendentes = [f for f in os.listdir(pasta) if f.endswith(".crdownload")]
        if not pendentes:
            break
        time.sleep(1)

    # Retorna todos os arquivos na pasta (exceto temporários)
    return [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if not f.endswith(".crdownload")
    ]


def _compactar_em_zip(arquivos: list[str], destino: str) -> str:
    """
    Compacta todos os arquivos baixados em um único .zip.

    Args:
        arquivos: Lista de caminhos absolutos.
        destino: Caminho do arquivo .zip a ser criado.

    Returns:
        Caminho do .zip gerado.
    """
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for caminho in arquivos:
            zf.write(caminho, arcname=os.path.basename(caminho))
    return destino


# ── Função principal (chamada pela thread do app.py) ───────────────────────
def executar_download(
    dt_ini: str,
    dt_fim: str,
    num_ciclos: int,
    itens_pag: str,
    cb_progresso,   # callable(ciclo, total, mensagem, nivel)
    cb_finalizado,  # callable(caminho_zip | None, erro | None)
) -> None:
    """
    Executa todo o fluxo de automação: login → filtro → loop de downloads.
    Deve ser chamada em uma thread separada para não bloquear o Streamlit.

    Credenciais são lidas de st.secrets para não ficarem expostas no código.

    Args:
        dt_ini:        Data inicial no formato DDMMAAAA.
        dt_fim:        Data final no formato DDMMAAAA.
        num_ciclos:    Número de páginas/ciclos a processar.
        itens_pag:     Quantidade de itens por página ("50", "100" ou "200").
        cb_progresso:  Callback chamado a cada ciclo com atualização de status.
        cb_finalizado: Callback chamado ao encerrar (sucesso ou erro).
    """
    # Diretório temporário isolado para os downloads desta execução
    pasta_temp  = tempfile.mkdtemp(prefix="cte_xmls_")
    caminho_zip = os.path.join(pasta_temp, "ctes_xml.zip")
    driver      = None

    try:
        # ── Lê credenciais do secrets.toml (nunca do código!) ─────────────
        usuario = st.secrets["mastersaf"]["usuario"]
        senha   = st.secrets["mastersaf"]["senha"]

        cb_progresso(0, num_ciclos, "Iniciando navegador...", "info")
        driver = _criar_driver(pasta_temp)
        wait   = WebDriverWait(driver, 20)

        # ── 1. Login ───────────────────────────────────────────────────────
        cb_progresso(0, num_ciclos, f"Acessando {LOGIN_URL}", "info")
        driver.get(LOGIN_URL)

        campo_user = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]')))
        campo_user.send_keys(usuario)

        campo_pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        campo_pwd.send_keys(senha)
        campo_pwd.send_keys(Keys.ENTER)

        time.sleep(5)  # aguarda redirecionamento pós-login

        # ── 2. Navegação para Receptor CTEs ───────────────────────────────
        cb_progresso(0, num_ciclos, "Navegando para Receptor CTEs...", "info")
        receptor = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
        )
        receptor.click()
        time.sleep(5)

        # ── 3. Filtro de datas ─────────────────────────────────────────────
        cb_progresso(0, num_ciclos, f"Aplicando filtro: {dt_ini} → {dt_fim}", "info")

        campo_ini = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="consultaDataInicial"]')))
        campo_ini.click()
        campo_ini.send_keys(Keys.CONTROL + "a")
        campo_ini.send_keys(dt_ini)

        campo_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        campo_fim.click()
        campo_fim.send_keys(dt_fim)
        campo_fim.send_keys(Keys.ENTER)

        time.sleep(2)
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
        time.sleep(2)

        # ── 4. Configura itens por página ──────────────────────────────────
        cb_progresso(0, num_ciclos, f"Configurando {itens_pag} itens por página...", "info")
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + Keys.END)
        time.sleep(2)

        select_pag = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
            )
        )
        select_pag.click()
        select_pag.send_keys(itens_pag)
        select_pag.send_keys(Keys.ENTER)
        time.sleep(3)

        # ── 5. Loop principal de download ──────────────────────────────────
        for i in range(num_ciclos):
            ciclo_atual = i + 1
            cb_progresso(ciclo_atual, num_ciclos, f"Ciclo {ciclo_atual}/{num_ciclos} — selecionando itens...", "info")

            # Vai ao topo e marca todos os registros da página
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + Keys.HOME)
            wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
            ).click()
            time.sleep(6)

            # Dispara download dos XMLs selecionados
            cb_progresso(ciclo_atual, num_ciclos, f"Ciclo {ciclo_atual}/{num_ciclos} — baixando XMLs...", "info")
            driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
            time.sleep(5)
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)

            # Aguarda downloads pendentes antes de avançar a página
            _aguardar_downloads(pasta_temp, timeout=60)

            # Desmarca seleção para não interferir na próxima iteração
            driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
            time.sleep(2)

            # Vai para próxima página
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + Keys.END)
            time.sleep(2)

            try:
                proximo = driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span')
                proximo.click()
                time.sleep(3)
                cb_progresso(ciclo_atual, num_ciclos, f"Ciclo {ciclo_atual} concluído ✓", "ok")
            except Exception:
                # Botão "Próximo" sumiu → chegamos na última página
                cb_progresso(ciclo_atual, num_ciclos, "Última página atingida. Encerrando loop.", "ok")
                break

        # ── 6. Compacta todos os arquivos em um ZIP ────────────────────────
        cb_progresso(num_ciclos, num_ciclos, "Compactando arquivos...", "info")
        todos_arquivos = _aguardar_downloads(pasta_temp)
        _compactar_em_zip(todos_arquivos, caminho_zip)

        cb_progresso(num_ciclos, num_ciclos, f"ZIP gerado com {len(todos_arquivos)} arquivo(s).", "ok")
        cb_finalizado(caminho_zip, None)  # sucesso

    except Exception as exc:
        # Qualquer exceção inesperada é capturada e repassada para a UI
        cb_finalizado(None, str(exc))

    finally:
        # Fecha o navegador em qualquer cenário (sucesso ou erro)
        if driver:
            driver.quit()
