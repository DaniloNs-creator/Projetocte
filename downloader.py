"""
downloader.py — Lógica de automação Selenium completamente isolada da UI.

Por que separado do app.py?
  • Roda em thread separada sem travar o Streamlit.
  • Fácil de testar de forma independente.
  • A UI pode ser reescrita sem mexer aqui.

Credenciais: lidas de st.secrets["mastersaf"] — nunca no código.
Driver:      ChromeDriverManager baixa o chromedriver correto automaticamente.
             Nenhum cliente precisa instalar nada manualmente.
"""

import os
import time
import shutil
import tempfile
import streamlit as st

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager  # resolve o driver automaticamente


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _force_click(driver, element):
    """
    Clica via JavaScript para contornar elementos que ficam fora
    da área visível ou cobertos por outros elementos.
    """
    driver.execute_script("arguments[0].click();", element)


def _scroll_to(driver, element):
    """Centraliza o elemento na viewport antes de interagir."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)


def _criar_driver(pasta_download: str) -> webdriver.Chrome:
    """
    Cria e configura o Chrome em modo headless (sem janela visual).

    O ChromeDriverManager detecta a versão instalada do Chrome/Chromium
    e baixa o chromedriver compatível automaticamente — sem instalação manual.

    Args:
        pasta_download: Pasta onde o Chrome vai salvar os arquivos baixados.

    Returns:
        Instância configurada do webdriver.Chrome.
    """
    opts = Options()

    # Modo headless: indispensável para rodar em servidores sem interface gráfica
    opts.add_argument("--headless=new")           # API moderna (Chrome ≥ 112)
    opts.add_argument("--no-sandbox")             # necessário em containers Linux
    opts.add_argument("--disable-dev-shm-usage")  # evita crash por /dev/shm cheio
    opts.add_argument("--disable-gpu")            # estabilidade adicional em headless
    opts.add_argument("--window-size=1920,1080")  # resolução virtual

    # Configura pasta de download sem diálogo "Salvar como"
    prefs = {
        "download.default_directory":  pasta_download,
        "download.prompt_for_download": False,
        "download.directory_upgrade":   True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True,
    }
    opts.add_experimental_option("prefs", prefs)

    # ChromeDriverManager resolve a versão correta do driver na primeira execução
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def _aguardar_downloads(pasta: str, timeout: int = 90) -> list[str]:
    """
    Bloqueia até que todos os downloads pendentes (.crdownload) terminem.

    O Chrome cria arquivos .crdownload durante o download e os remove
    ao finalizar. Monitoramos isso para saber quando é seguro avançar.

    Args:
        pasta:   Pasta de download monitorada.
        timeout: Tempo máximo de espera em segundos.

    Returns:
        Lista de caminhos completos dos arquivos baixados.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        pendentes = [f for f in os.listdir(pasta) if f.endswith(".crdownload")]
        if not pendentes:
            break
        time.sleep(1.5)

    # Retorna apenas arquivos completos (sem temporários)
    return [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if not f.endswith(".crdownload") and os.path.isfile(os.path.join(pasta, f))
    ]


def _contar_checkboxes_linha(driver) -> int:
    """
    Conta os checkboxes nas células <td> da tabela (linhas de dados).
    Exclui o checkbox mestre que fica no cabeçalho <th>.

    Returns:
        Número de itens selecionados na página atual.
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
    Executa o fluxo completo de automação:
      1. Login no MasterSAF
      2. Navega para Receptor CTEs
      3. Aplica filtro de datas
      4. Configura itens por página
      5. Loop: seleciona → baixa XMLs → avança página
      6. Compacta tudo em ZIP e retorna via callback

    Deve ser chamada em uma thread separada para não bloquear a UI do Streamlit.

    Args:
        dt_ini_str:    Data inicial no formato DDMMAAAA (ex: "01092025").
        dt_fim_str:    Data final no formato DDMMAAAA (ex: "31012026").
        num_itens_pag: Itens por página como string ("50", "100", "200", "500").
        num_loops:     Máximo de páginas/ciclos a processar.
        cb_progresso:  Callback de atualização de progresso chamado a cada ciclo.
        cb_finalizado: Callback chamado ao encerrar (com ZIP ou com erro).
    """
    # Diretório temporário isolado para os downloads desta execução
    pasta_temp = tempfile.mkdtemp(prefix="mastersaf_xmls_")
    driver = None

    try:
        # ── Lê credenciais do secrets.toml ───────────────────────────────
        # As chaves devem estar em .streamlit/secrets.toml ou nas Secrets
        # do Streamlit Cloud. Nunca as coloque diretamente no código!
        usuario = st.secrets["mastersaf"]["username"]
        senha   = st.secrets["mastersaf"]["password"]

        cb_progresso(0, num_loops, 0, "Iniciando navegador headless...", "info")
        driver = _criar_driver(pasta_temp)
        wait   = WebDriverWait(driver, 25)

        # ── 1. Login ──────────────────────────────────────────────────────
        cb_progresso(0, num_loops, 0, "Acessando MasterSAF DFE...", "info")
        driver.get("https://p.dfe.mastersaf.com.br/mvc/login")

        campo_user = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="nomeusuario"]')))
        campo_user.send_keys(usuario)

        campo_pwd = driver.find_element(By.XPATH, '//*[@id="senha"]')
        campo_pwd.send_keys(senha)
        campo_pwd.send_keys(Keys.ENTER)

        cb_progresso(0, num_loops, 0, "Login realizado. Aguardando redirecionamento...", "info")
        time.sleep(5)

        # ── 2. Navega para Receptor CTEs ──────────────────────────────────
        cb_progresso(0, num_loops, 0, "Navegando para Receptor CTEs...", "info")
        receptor = wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a'))
        )
        _force_click(driver, receptor)
        time.sleep(5)

        # ── 3. Aplica filtro de datas via JavaScript ───────────────────────
        # Usar JS é mais confiável que send_keys para campos com máscaras de data
        cb_progresso(0, num_loops, 0, f"Aplicando filtro: {dt_ini_str[:2]}/{dt_ini_str[2:4]}/{dt_ini_str[4:]} → {dt_fim_str[:2]}/{dt_fim_str[2:4]}/{dt_fim_str[4:]}", "info")

        campo_ini = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="consultaDataInicial"]')))
        driver.execute_script(f"arguments[0].value = '{dt_ini_str}';", campo_ini)

        campo_fim = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
        driver.execute_script(f"arguments[0].value = '{dt_fim_str}';", campo_fim)
        campo_fim.send_keys(Keys.ENTER)
        time.sleep(4)

        # ── 4. Configura itens por página ─────────────────────────────────
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
            cb_progresso(pag_atual, num_loops, 0,
                         f"[{pag_atual}/{num_loops}] Selecionando itens da página...", "info")

            # Seleciona todos os registros da página atual
            checkbox_all = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input'))
            )
            _scroll_to(driver, checkbox_all)
            _force_click(driver, checkbox_all)
            time.sleep(3)

            # Conta quantos XMLs foram selecionados nesta página
            qtd_nesta_pag = _contar_checkboxes_linha(driver)
            cb_progresso(pag_atual, num_loops, qtd_nesta_pag,
                         f"[{pag_atual}/{num_loops}] {qtd_nesta_pag} XML(s) selecionado(s). Baixando...", "info")

            # Dispara o download dos XMLs selecionados
            btn_xml = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="xml_multiplos"]/h3'))
            )
            _scroll_to(driver, btn_xml)
            _force_click(driver, btn_xml)
            time.sleep(5)

            # Aguarda o Chrome terminar os downloads antes de avançar
            _aguardar_downloads(pasta_temp, timeout=90)

            # Desmarca seleção para não causar conflito na próxima página
            _force_click(driver, checkbox_all)
            time.sleep(2)

            cb_progresso(pag_atual, num_loops, 0,
                         f"[{pag_atual}/{num_loops}] Página concluída ✓", "ok")

            # Avança para a próxima página
            try:
                next_btn = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="next_plistagem"]/span'))
                )
                _scroll_to(driver, next_btn)

                # Verifica se o botão está desabilitado (última página)
                classes = next_btn.get_attribute("class") or ""
                if "ui-state-disabled" in classes:
                    cb_progresso(pag_atual, num_loops, 0,
                                 "Última página atingida. Encerrando loop.", "ok")
                    break

                _force_click(driver, next_btn)
                time.sleep(4)

            except Exception:
                # Botão "Próximo" não encontrado — provavelmente última página
                cb_progresso(pag_atual, num_loops, 0,
                             "Botão 'Próximo' não encontrado. Fim da listagem.", "ok")
                break

        # ── 6. Compacta todos os arquivos baixados em um ZIP ───────────────
        cb_progresso(num_loops, num_loops, 0, "Compactando arquivos em ZIP...", "info")

        # Garante que todos os downloads estejam completos antes de compactar
        _aguardar_downloads(pasta_temp, timeout=30)

        arquivo_zip_base = tempfile.mktemp(prefix="mastersaf_")
        caminho_zip = shutil.make_archive(
            base_name=arquivo_zip_base,
            format="zip",
            root_dir=pasta_temp,
        )

        # Lê o ZIP em memória para repassar ao Streamlit via callback
        # (evita problemas de caminho entre a thread e o processo principal)
        with open(caminho_zip, "rb") as f:
            zip_bytes = f.read()

        cb_progresso(num_loops, num_loops, 0,
                     f"ZIP gerado com {st.session_state.get('total_xmls', 0)} XML(s).", "ok")
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

        # Remove a pasta temporária de downloads
        shutil.rmtree(pasta_temp, ignore_errors=True)

        # Remove o ZIP temporário do disco (já foi lido em memória)
        try:
            os.remove(caminho_zip)
        except Exception:
            pass