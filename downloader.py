"""
downloader.py — Automação Selenium com detecção automática de ambiente.

Estratégia de navegador:
  • LOCAL  → Microsoft Edge  (webdriver_manager baixa o msedgedriver correto)
  • DEPLOY → Chromium        (instalado via packages.txt no Streamlit Cloud)

A detecção é feita pela variável STREAMLIT_SHARING_MODE, que o Streamlit Cloud
define automaticamente. Se não existir, assume ambiente local → usa Edge.

Credenciais: lidas de st.secrets["mastersaf"] — nunca escritas no código.
"""

import os
import time
import shutil
import tempfile
import streamlit as st

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


# ─────────────────────────────────────────────────────────────────────────────
# DETECÇÃO DE AMBIENTE
# ─────────────────────────────────────────────────────────────────────────────

def _esta_no_servidor() -> bool:
    """
    Retorna True quando rodando no Streamlit Cloud (Linux/servidor).
    O Streamlit Cloud define STREAMLIT_SHARING_MODE=streamlit automaticamente.
    Em máquina local essa variável não existe → retorna False → usa Edge.
    """
    return os.environ.get("STREAMLIT_SHARING_MODE") == "streamlit"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _force_click(driver, element):
    """
    Clica via JavaScript para contornar elementos fora da viewport
    ou cobertos por overlays/menus que bloqueiam o clique normal.
    """
    driver.execute_script("arguments[0].click();", element)


def _scroll_to(driver, element):
    """Centraliza o elemento na viewport antes de interagir."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)


def _criar_driver_edge(pasta_download: str) -> webdriver.Edge:
    """
    Cria o driver do Microsoft Edge para uso LOCAL.

    O EdgeChromiumDriverManager detecta a versão do Edge instalada na máquina
    e baixa o msedgedriver compatível — sem instalação manual do driver.

    Args:
        pasta_download: Pasta onde o Edge salvará os arquivos baixados.

    Returns:
        Instância configurada do webdriver.Edge.
    """
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    from webdriver_manager.microsoft import EdgeChromiumDriverManager

    opts = EdgeOptions()

    # Headless: roda sem abrir janela visível do navegador
    opts.add_argument("--headless=new")           # API moderna (Edge ≥ 109)
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")  # resolução virtual

    # Configura pasta de download automático sem popup "Salvar como"
    prefs = {
        "download.default_directory":         pasta_download,
        "download.prompt_for_download":       False,
        "download.directory_upgrade":         True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled":               True,
    }
    opts.add_experimental_option("prefs", prefs)

    # Baixa o msedgedriver compatível com a versão do Edge instalada
    service = EdgeService(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=opts)


def _criar_driver_chromium(pasta_download: str) -> webdriver.Chrome:
    """
    Cria o driver do Chromium para uso no SERVIDOR (Streamlit Cloud).

    O Chromium e seu driver são instalados via packages.txt (apt-get).
    Não é necessário webdriver_manager — o driver já está no PATH do servidor.

    Args:
        pasta_download: Pasta onde o Chromium salvará os arquivos baixados.

    Returns:
        Instância configurada do webdriver.Chrome apontando para Chromium.
    """
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService

    opts = ChromeOptions()

    # Obrigatório em Linux sem interface gráfica (servidor)
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    # Aponta para o binário do Chromium instalado pelo apt
    opts.binary_location = "/usr/bin/chromium"

    # Configura pasta de download automático sem popup "Salvar como"
    prefs = {
        "download.default_directory":         pasta_download,
        "download.prompt_for_download":       False,
        "download.directory_upgrade":         True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled":               True,
    }
    opts.add_experimental_option("prefs", prefs)

    # Usa o chromedriver instalado pelo apt (já no PATH do servidor)
    service = ChromeService("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=opts)


def _criar_driver(pasta_download: str):
    """
    Fábrica de drivers: escolhe Edge (local) ou Chromium (servidor)
    com base no ambiente detectado automaticamente.

    Args:
        pasta_download: Pasta de destino dos downloads.

    Returns:
        Driver configurado para o ambiente atual.
    """
    if _esta_no_servidor():
        return _criar_driver_chromium(pasta_download)  # Streamlit Cloud
    else:
        return _criar_driver_edge(pasta_download)      # Máquina local (Edge)


def _aguardar_downloads(pasta: str, timeout: int = 90) -> list:
    """
    Bloqueia até que todos os downloads em andamento terminem.

    Monitora duas extensões temporárias:
      • .crdownload — Edge e Chrome/Chromium usam durante o download
      • .tmp        — Edge usa em alguns cenários específicos

    Args:
        pasta:   Pasta de download monitorada.
        timeout: Tempo máximo de espera em segundos.

    Returns:
        Lista de caminhos absolutos dos arquivos baixados com sucesso.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        pendentes = [
            f for f in os.listdir(pasta)
            if f.endswith(".crdownload") or f.endswith(".tmp")
        ]
        if not pendentes:
            break
        time.sleep(1.5)

    # Retorna apenas arquivos completos (sem temporários)
    return [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if not f.endswith(".crdownload")
        and not f.endswith(".tmp")
        and os.path.isfile(os.path.join(pasta, f))
    ]


def _contar_checkboxes_linha(driver) -> int:
    """
    Conta checkboxes dentro de células <td> (linhas de dados).
    Exclui o checkbox mestre que fica no cabeçalho <th>.

    Returns:
        Número de itens selecionáveis na página atual.
    """
    itens = driver.find_elements(By.XPATH, '//td//input[@type="checkbox"]')
    return len(itens)


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL — chamada pela thread em app.py
# ─────────────────────────────────────────────────────────────────────────────

def executar_automacao(
    dt_ini_str:    str,
    dt_fim_str:    str,
    num_itens_pag: str,
    num_loops:     int,
    cb_progresso,        # callable(pag_atual, total, xmls_pagina, mensagem, nivel)
    cb_finalizado,       # callable(zip_bytes | None, erro | None)
) -> None:
    """
    Fluxo completo de automação:
      1. Detecta ambiente e inicia Edge (local) ou Chromium (servidor)
      2. Login no MasterSAF DFE
      3. Navega para Receptor CTEs
      4. Aplica filtro de datas via JavaScript
      5. Configura itens por página
      6. Loop: seleciona todos → baixa XMLs → aguarda downloads → avança página
      7. Compacta tudo em ZIP e retorna via callback

    Deve ser chamada em uma thread separada para não bloquear o Streamlit.

    Args:
        dt_ini_str:    Data inicial formato DDMMAAAA, ex: "01092025".
        dt_fim_str:    Data final formato DDMMAAAA, ex: "31012026".
        num_itens_pag: Itens por página: "50", "100", "200" ou "500".
        num_loops:     Número máximo de páginas a processar.
        cb_progresso:  Callback chamado a cada ciclo com dados de progresso.
        cb_finalizado: Callback chamado ao encerrar com ZIP (bytes) ou erro.
    """
    pasta_temp  = tempfile.mkdtemp(prefix="mastersaf_xmls_")
    caminho_zip = None  # inicializado aqui para o finally não quebrar
    driver      = None

    try:
        # ── Credenciais do secrets.toml ───────────────────────────────────
        # Configure em .streamlit/secrets.toml (local) ou Streamlit Cloud Secrets.
        # Nunca escreva usuário/senha diretamente no código!
        usuario = st.secrets["mastersaf"]["username"]
        senha   = st.secrets["mastersaf"]["password"]

        # Informa qual navegador será usado neste ambiente
        nav = "Chromium (servidor)" if _esta_no_servidor() else "Microsoft Edge (local)"
        cb_progresso(0, num_loops, 0, f"Iniciando {nav}...", "info")

        driver = _criar_driver(pasta_temp)
        wait   = WebDriverWait(driver, 25)

        # ── 1. Login ───────────────────────────────────────────────────────
        cb_progresso(0, num_loops, 0, "Acessando MasterSAF DFE...", "info")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")

        campo_user = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]'))
        )
        campo_user.send_keys(usuario)

        campo_pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        campo_pwd.send_keys(senha)
        campo_pwd.send_keys(Keys.ENTER)

        cb_progresso(0, num_loops, 0, "Login enviado. Aguardando redirecionamento...", "info")
        time.sleep(5)

        # ── 2. Navega para Receptor CTEs ───────────────────────────────────
        cb_progresso(0, num_loops, 0, "Navegando para Receptor CTEs...", "info")
        receptor = wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
        )
        _force_click(driver, receptor)
        time.sleep(5)

        # ── 3. Filtro de datas via JavaScript ──────────────────────────────
        # JS é mais confiável que send_keys em campos com máscara de data,
        # pois bypassa o formatador automático do Edge.
        ini_fmt = f"{dt_ini_str[:2]}/{dt_ini_str[2:4]}/{dt_ini_str[4:]}"
        fim_fmt = f"{dt_fim_str[:2]}/{dt_fim_str[2:4]}/{dt_fim_str[4:]}"
        cb_progresso(0, num_loops, 0, f"Filtro: {ini_fmt} → {fim_fmt}", "info")

        campo_ini = wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="consultaDataInicial"]'))
        )
        driver.execute_script(f"arguments[0].value = '{dt_ini_str}';", campo_ini)

        campo_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        driver.execute_script(f"arguments[0].value = '{dt_fim_str}';", campo_fim)
        campo_fim.send_keys(Keys.ENTER)
        time.sleep(4)

        # ── 4. Itens por página ────────────────────────────────────────────
        cb_progresso(0, num_loops, 0, f"Configurando {num_itens_pag} itens/página...", "info")

        select_el = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select')
            )
        )
        _scroll_to(driver, select_el)
        Select(select_el).select_by_visible_text(num_itens_pag)
        time.sleep(4)

        # ── 5. Loop de páginas ─────────────────────────────────────────────
        for i in range(num_loops):
            pag_atual = i + 1
            cb_progresso(
                pag_atual, num_loops, 0,
                f"[{pag_atual}/{num_loops}] Selecionando itens...", "info"
            )

            # Marca todos os registros da página com o checkbox mestre
            checkbox_all = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                )
            )
            _scroll_to(driver, checkbox_all)
            _force_click(driver, checkbox_all)
            time.sleep(3)

            # Conta itens selecionados para atualizar o contador acumulado
            qtd = _contar_checkboxes_linha(driver)
            cb_progresso(
                pag_atual, num_loops, qtd,
                f"[{pag_atual}/{num_loops}] {qtd} XML(s) — baixando...", "info"
            )

            # Clica em "XML Múltiplos" para disparar o download
            btn_xml = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="xml_multiplos"]/h3'))
            )
            _scroll_to(driver, btn_xml)
            _force_click(driver, btn_xml)
            time.sleep(5)

            # Aguarda o Edge/Chromium finalizar todos os downloads antes de avançar
            _aguardar_downloads(pasta_temp, timeout=90)

            # Desmarca seleção para não interferir na próxima página
            _force_click(driver, checkbox_all)
            time.sleep(2)

            cb_progresso(
                pag_atual, num_loops, 0,
                f"[{pag_atual}/{num_loops}] Página concluída ✓", "ok"
            )

            # ── Avança para a próxima página ───────────────────────────────
            try:
                next_btn = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="next_plistagem"]/span'))
                )
                _scroll_to(driver, next_btn)

                # Verifica se o botão está desabilitado (chegou na última página)
                classes = next_btn.get_attribute("class") or ""
                if "ui-state-disabled" in classes:
                    cb_progresso(
                        pag_atual, num_loops, 0,
                        "Última página atingida. Encerrando loop.", "ok"
                    )
                    break

                _force_click(driver, next_btn)
                time.sleep(4)

            except Exception:
                # Botão não encontrado = chegamos na última página
                cb_progresso(
                    pag_atual, num_loops, 0,
                    "Botão 'Próximo' não encontrado. Fim da listagem.", "ok"
                )
                break

        # ── 6. Compacta todos os XMLs em um único ZIP ──────────────────────
        cb_progresso(num_loops, num_loops, 0, "Compactando arquivos em ZIP...", "info")

        # Aguarda downloads residuais antes de zipar
        _aguardar_downloads(pasta_temp, timeout=30)

        zip_base    = tempfile.mktemp(prefix="mastersaf_zip_")
        caminho_zip = shutil.make_archive(
            base_name=zip_base,
            format="zip",
            root_dir=pasta_temp,
        )

        # Lê o ZIP em memória (bytes) para entregar ao Streamlit via callback.
        # Passar bytes evita problemas de caminho entre threads diferentes.
        with open(caminho_zip, "rb") as f:
            zip_bytes = f.read()

        total = st.session_state.get("total_xmls", 0)
        cb_progresso(num_loops, num_loops, 0, f"ZIP gerado — {total} XML(s).", "ok")
        cb_finalizado(zip_bytes, None)  # ✅ sucesso

    except Exception as exc:
        # Captura qualquer exceção inesperada e repassa para a UI
        cb_finalizado(None, str(exc))

    finally:
        # Sempre fecha o navegador — mesmo em caso de erro
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

        # Remove pasta temporária de downloads
        shutil.rmtree(pasta_temp, ignore_errors=True)

        # Remove o arquivo ZIP temporário do disco (já foi lido em memória)
        if caminho_zip:
            try:
                os.remove(caminho_zip)
            except Exception:
                pass
