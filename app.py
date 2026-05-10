import streamlit as st
import os
import shutil
import zipfile
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MasterSAF — Automação XML",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS GLOBAL  (industrial / utilitarian dark)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,300&display=swap');

/* ── Reset & base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #0a0c10 !important;
    color: #d4dbe8 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0e1117 !important;
    border-right: 1px solid #1e2535 !important;
}
[data-testid="stSidebar"] * { color: #c4ccd8 !important; }

/* ── Header hero ── */
.hero {
    padding: 2.5rem 0 1.5rem;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 2rem;
}
.hero-tag {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    color: #00e5a0;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.1rem;
    font-weight: 700;
    color: #eef2ff;
    line-height: 1.15;
    margin: 0;
}
.hero-title span { color: #00e5a0; }
.hero-subtitle {
    font-size: 0.95rem;
    color: #6b7a99;
    margin-top: 0.5rem;
    font-weight: 300;
}

/* ── Metric cards ── */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
}
.metric-card {
    background: #0e1117;
    border: 1px solid #1e2535;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00e5a0, #0070f3);
}
.metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.15em;
    color: #4a5568;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: #eef2ff;
    line-height: 1;
}
.metric-value.green { color: #00e5a0; }
.metric-value.blue  { color: #0070f3; }
.metric-value.amber { color: #f5a623; }

/* ── Log terminal ── */
.log-box {
    background: #070910;
    border: 1px solid #1e2535;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #7dafff;
    max-height: 340px;
    overflow-y: auto;
    line-height: 1.7;
}
.log-box .ts  { color: #2d3a52; }
.log-box .ok  { color: #00e5a0; }
.log-box .err { color: #ff5c5c; }
.log-box .inf { color: #7dafff; }
.log-box .wrn { color: #f5a623; }

/* ── Progress bar override ── */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #00e5a0, #0070f3) !important;
    border-radius: 4px !important;
}
[data-testid="stProgress"] > div {
    background: #1e2535 !important;
    border-radius: 4px !important;
    height: 6px !important;
}

/* ── Sidebar inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #070910 !important;
    border: 1px solid #1e2535 !important;
    border-radius: 6px !important;
    color: #d4dbe8 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.82rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #00e5a0 !important;
    box-shadow: 0 0 0 2px rgba(0,229,160,0.15) !important;
}

/* ── Sidebar labels ── */
[data-testid="stSidebar"] label {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #4a5568 !important;
}

/* ── Button ── */
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #00e5a0, #0070f3) !important;
    color: #020408 !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.08em !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.75rem 1.5rem !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
}
[data-testid="stSidebar"] .stButton button:hover { opacity: 0.85 !important; }

/* ── Download button ── */
.stDownloadButton button {
    background: #0e1117 !important;
    color: #00e5a0 !important;
    border: 1px solid #00e5a0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
    border-radius: 6px !important;
    padding: 0.65rem 1.4rem !important;
    transition: all 0.2s !important;
}
.stDownloadButton button:hover {
    background: #00e5a0 !important;
    color: #020408 !important;
}

/* ── Alert boxes ── */
[data-testid="stAlert"] {
    background: #0e1117 !important;
    border-radius: 8px !important;
    border-left: 3px solid !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8rem !important;
}

/* ── Section label ── */
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    color: #4a5568;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    margin-top: 1.8rem;
    border-bottom: 1px solid #1e2535;
    padding-bottom: 0.4rem;
}

/* ── Sidebar logo ── */
.sidebar-logo {
    font-family: 'Space Mono', monospace;
    font-size: 0.95rem;
    font-weight: 700;
    color: #eef2ff;
    letter-spacing: 0.05em;
    padding: 1.2rem 0 1.5rem;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 1.2rem;
}
.sidebar-logo span { color: #00e5a0; }

/* ── Status badge ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 100px;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-left: 0.8rem;
    vertical-align: middle;
}
.badge-idle    { background: #1e2535; color: #4a5568; }
.badge-running { background: rgba(0,229,160,0.15); color: #00e5a0; }
.badge-done    { background: rgba(0,112,243,0.15); color: #0070f3; }
.badge-error   { background: rgba(255,92,92,0.15); color: #ff5c5c; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────
if "logs"          not in st.session_state: st.session_state.logs          = []
if "pages_done"    not in st.session_state: st.session_state.pages_done    = 0
if "files_dl"      not in st.session_state: st.session_state.files_dl      = 0
if "errors"        not in st.session_state: st.session_state.errors        = 0
if "status"        not in st.session_state: st.session_state.status        = "idle"   # idle | running | done | error
if "zip_ready"     not in st.session_state: st.session_state.zip_ready     = False

def add_log(msg: str, kind: str = "inf"):
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append((ts, kind, msg))

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">MASTER<span>SAF</span> //</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Credenciais</div>', unsafe_allow_html=True)
    usuario   = st.text_input("Usuário", placeholder="login@empresa.com.br")
    senha     = st.text_input("Senha", type="password", placeholder="••••••••")

    st.markdown('<div class="section-label">Período</div>', unsafe_allow_html=True)
    data_ini  = st.text_input("Data Inicial", value="08/05/2026")
    data_fin  = st.text_input("Data Final",   value="08/05/2026")

    st.markdown('<div class="section-label">Parâmetros</div>', unsafe_allow_html=True)
    qtd_loops = st.number_input("Qtd. Páginas (Loops)", min_value=1, max_value=1000, value=5)

    st.markdown("<br>", unsafe_allow_html=True)
    iniciar   = st.button("⚡ Iniciar Automação")

# ─────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────
badge_html = {
    "idle":    '<span class="badge badge-idle">Aguardando</span>',
    "running": '<span class="badge badge-running">● Executando</span>',
    "done":    '<span class="badge badge-done">Concluído</span>',
    "error":   '<span class="badge badge-error">Erro</span>',
}[st.session_state.status]

st.markdown(f"""
<div class="hero">
    <div class="hero-tag">⚡ Sistema de Automação Fiscal</div>
    <h1 class="hero-title">Master<span>SAF</span> Downloads XML {badge_html}</h1>
    <p class="hero-subtitle">Captura automatizada de CT-e em massa — suporte a até 1 000 páginas por sessão</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# METRIC CARDS
# ─────────────────────────────────────────────
elapsed_str = "—"
pct         = 0 if qtd_loops == 0 else round(st.session_state.pages_done / qtd_loops * 100)

st.markdown(f"""
<div class="metrics-row">
    <div class="metric-card">
        <div class="metric-label">Páginas Processadas</div>
        <div class="metric-value green">{st.session_state.pages_done}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Total Programado</div>
        <div class="metric-value">{qtd_loops}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Arquivos Baixados</div>
        <div class="metric-value blue">{st.session_state.files_dl}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Erros Recuperados</div>
        <div class="metric-value amber">{st.session_state.errors}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PROGRESS + LOG
# ─────────────────────────────────────────────
st.markdown('<div class="section-label">Progresso</div>', unsafe_allow_html=True)
progress_bar = st.progress(pct / 100)

st.markdown('<div class="section-label">Log em tempo real</div>', unsafe_allow_html=True)
log_placeholder = st.empty()

def render_log():
    lines = ""
    for ts, kind, msg in st.session_state.logs[-120:]:   # últimas 120 linhas
        lines += f'<span class="ts">[{ts}]</span> <span class="{kind}">{msg}</span><br>'
    log_placeholder.markdown(f'<div class="log-box">{lines or "<span class=ts>// sem eventos ainda</span>"}</div>', unsafe_allow_html=True)

render_log()

# ─────────────────────────────────────────────
# DRIVER  (idêntico ao original, só com wait)
# ─────────────────────────────────────────────
def get_driver(download_path):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


# ─────────────────────────────────────────────
# FUNÇÃO AUXILIAR: aguarda download terminar
# (sem alterar lógica — apenas evita timeout)
# ─────────────────────────────────────────────
def wait_for_downloads(path: str, timeout: int = 120):
    """Bloqueia até que não haja arquivos .crdownload / .tmp na pasta."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pending = [f for f in os.listdir(path)
                   if f.endswith((".crdownload", ".tmp", ".part"))]
        if not pending:
            return True
        time.sleep(1)
    return False  # timeout


# ─────────────────────────────────────────────
# AUTOMAÇÃO PRINCIPAL
# ─────────────────────────────────────────────
if iniciar:
    if not usuario or not senha:
        st.error("Preencha usuário e senha antes de iniciar.")
    else:
        # Reset estado
        st.session_state.logs       = []
        st.session_state.pages_done = 0
        st.session_state.files_dl   = 0
        st.session_state.errors     = 0
        st.session_state.status     = "running"
        st.session_state.zip_ready  = False

        dl_path = "/tmp/downloads"
        if os.path.exists(dl_path):
            shutil.rmtree(dl_path)
        os.makedirs(dl_path)

        add_log("Sessão iniciada — preparando ambiente", "ok")
        render_log()

        driver = None
        try:
            add_log("Inicializando navegador headless...", "inf")
            render_log()
            driver = get_driver(dl_path)
            wait  = WebDriverWait(driver, 30)   # espera explícita global

            # ── Login ────────────────────────────────────────────────────
            add_log("Acessando portal MasterSAF...", "inf")
            render_log()
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="enter"]')
            )
            time.sleep(4)
            add_log("Login efetuado.", "ok")

            # ── Navegação ────────────────────────────────────────────────
            add_log("Acessando listagem de CT-e...", "inf")
            render_log()
            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a')
            )
            time.sleep(3)

            # ── Datas ────────────────────────────────────────────────────
            for xpath, val in [
                ('//*[@id="consultaDataInicial"]', data_ini),
                ('//*[@id="consultaDataFinal"]',   data_fin),
            ]:
                el = driver.find_element(By.XPATH, xpath)
                el.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
                el.send_keys(val)

            driver.execute_script(
                "arguments[0].click();",
                driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]')
            )
            time.sleep(3)

            # ── Visualização ─────────────────────────────────────────────
            driver.find_element(
                By.XPATH,
                '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]'
            ).click()
            time.sleep(3)
            add_log(f"Filtros aplicados. Período: {data_ini} → {data_fin}", "ok")
            render_log()

            # ── Loop de downloads ────────────────────────────────────────
            for i in range(int(qtd_loops)):
                page_num = i + 1
                add_log(f"Processando página {page_num}/{qtd_loops}...", "inf")

                try:
                    # Selecionar todos
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                    )
                    # Abrir painel XML múltiplos
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3')
                    )
                    # Disparar download
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]')
                    )

                    # Aguarda download com timeout generoso (evita queda em 1000 pág)
                    downloaded = wait_for_downloads(dl_path, timeout=120)
                    if not downloaded:
                        add_log(f"Página {page_num}: timeout de download — continuando.", "wrn")
                        st.session_state.errors += 1
                    else:
                        n_files = len([
                            f for f in os.listdir(dl_path)
                            if os.path.isfile(os.path.join(dl_path, f))
                        ])
                        st.session_state.files_dl = n_files
                        add_log(f"Página {page_num} OK — {n_files} arquivo(s) acumulados.", "ok")

                    # Desmarcar e avançar página
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input')
                    )
                    driver.execute_script(
                        "arguments[0].click();",
                        driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span')
                    )
                    time.sleep(4)

                except Exception as page_err:
                    st.session_state.errors += 1
                    add_log(f"Página {page_num} erro: {page_err} — continuando.", "err")
                    # Tenta recuperar: recarrega estado sem derrubar tudo
                    try:
                        driver.execute_script(
                            "arguments[0].click();",
                            driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span')
                        )
                        time.sleep(4)
                    except Exception:
                        pass

                st.session_state.pages_done = page_num
                pct_now = page_num / int(qtd_loops)
                progress_bar.progress(pct_now)
                render_log()

            # ── Compactar ────────────────────────────────────────────────
            add_log("Download concluído. Compactando arquivos ZIP...", "inf")
            render_log()
            zip_filename = "/tmp/resultado.zip"
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(dl_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            total_zipped = len(zipf.namelist()) if hasattr(zipf, 'namelist') else "?"
            add_log(f"ZIP criado: {zip_filename}", "ok")
            add_log(f"Total de páginas: {int(qtd_loops)} | Erros recuperados: {st.session_state.errors}", "ok")
            st.session_state.status    = "done"
            st.session_state.zip_ready = True
            render_log()

            driver.quit()

        except Exception as e:
            st.session_state.status = "error"
            st.session_state.errors += 1
            add_log(f"ERRO CRÍTICO: {e}", "err")
            add_log(traceback.format_exc(), "err")
            render_log()
            if driver:
                try: driver.quit()
                except Exception: pass

# ─────────────────────────────────────────────
# RESULTADO / DOWNLOAD
# ─────────────────────────────────────────────
if st.session_state.zip_ready and os.path.exists("/tmp/resultado.zip"):
    st.markdown('<div class="section-label">Resultado</div>', unsafe_allow_html=True)
    st.success(
        f"✅ Automação finalizada com sucesso! "
        f"{st.session_state.pages_done} página(s) processadas, "
        f"{st.session_state.files_dl} arquivo(s) baixados, "
        f"{st.session_state.errors} erro(s) recuperado(s)."
    )
    with open("/tmp/resultado.zip", "rb") as f:
        st.download_button(
            label="📥 Baixar XMLs (ZIP)",
            data=f,
            file_name="XMLs_MasterSaf.zip",
            mime="application/zip",
        )

if st.session_state.status == "error":
    st.error("A automação encontrou um erro crítico. Verifique o log acima.")
