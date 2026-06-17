"""
apply_patch_FINAL.py
====================
PATCH DEFINITIVO — parte do app.py ORIGINAL.
Substitui TODOS os patches anteriores (v1, v2, v3).

Execute na raiz do projeto:
    python apply_patch_FINAL.py

Se você aplicou algum patch anterior e o app está quebrado:
    git checkout app.py        # restaurar pelo git
    python apply_patch_FINAL.py

O script valida a sintaxe com ast.parse() antes de gravar.
Se algum bloco não for encontrado, ele avisa qual e para sem alterar o arquivo.
"""

import ast
import shutil
from pathlib import Path

APP = Path("app.py")

if not APP.exists():
    raise FileNotFoundError("app.py não encontrado. Execute na raiz do projeto.")

shutil.copy(APP, APP.with_suffix(".py.bak_final"))
print(f"✅ Backup salvo em {APP.with_suffix('.py.bak_final')}")

src = APP.read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
def aplicar(nome, old, new, src):
    if old not in src:
        print(f"❌ [{nome}] bloco não encontrado — verifique se o arquivo é o original")
        raise SystemExit(1)
    result = src.replace(old, new, 1)
    print(f"✅ [{nome}] aplicado")
    return result
# ─────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Chunk size: 20 → 8  (reduz RAM por iteração ~60%)
# ═══════════════════════════════════════════════════════════════════════════════
src = aplicar(
    "CHUNK_SIZE",
    "_PDF_CHUNK_PAGES = 20   # Streamlit Cloud ~1GB RAM — chunks menores evitam OOM",
    "_PDF_CHUNK_PAGES = 8    # Streamlit Cloud ~1GB RAM — 8 págs/chunk evita OOM em 1200+ págs",
    src,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Buffer HafelePDFParser: 500KB → 200KB
# ═══════════════════════════════════════════════════════════════════════════════
src = aplicar(
    "BUF_HAFELE",
    "    _MAX_BUF_CHARS = 500_000  # ~500KB de texto — suficiente para qualquer item",
    "    _MAX_BUF_CHARS = 200_000  # ~200KB de texto — suficiente para qualquer item",
    src,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Buffer SigrawebPDFParser: 500KB → 200KB
# ═══════════════════════════════════════════════════════════════════════════════
src = aplicar(
    "BUF_SIGRAWEB",
    "    _MAX_BUF_CHARS = 500_000  # ~500KB — proteção OOM",
    "    _MAX_BUF_CHARS = 200_000  # ~200KB — proteção OOM",
    src,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. DuimpPDFParser.preprocess — liberar raw text por página (já usa fitz)
# ═══════════════════════════════════════════════════════════════════════════════
src = aplicar(
    "DUIMP_RAW_DEL",
    """\
            lines = []
            for idx in range(start, end):
                page = doc[idx]
                for line in page.get_text("text").split('\\n'):
                    if self._filter(line):
                        lines.append(line)
                page = None   # libera objeto página imediatamente""",
    """\
            lines = []
            for idx in range(start, end):
                page = doc[idx]
                raw = page.get_text("text")
                page = None          # libera objeto fitz imediatamente
                for line in raw.split('\\n'):
                    if self._filter(line):
                        lines.append(line)
                del raw              # libera texto bruto da página""",
    src,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. HafelePDFParser.parse_pdf COMPLETO — pdfplumber → fitz
#
# pdfplumber/pdfminer carrega a xref table inteira na abertura:
#   1200 págs × ~500KB estruturas = ~600MB só ao abrir → OOM imediato
# fitz.open() é lazy: carrega apenas header (~30MB, independente do tamanho)
# ═══════════════════════════════════════════════════════════════════════════════
src = aplicar(
    "HAFELE_PARSE_PDF",
    """\
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            prog_txt = st.empty()
            prog_bar = st.progress(0)
            items_found: list = []
            self._buffer = ""

            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                chunk = _PDF_CHUNK_PAGES

                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(
                        f"Processando páginas {start+1}–{end} de {total} "
                        f"(Extrato DUIMP)... {int((end/total)*100)}%"
                    )
                    prog_bar.progress(end / total)

                    chunk_lines = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_lines.append(t)

                    chunk_text = self._buffer + "\\n".join(chunk_lines)
                    del chunk_lines

                    is_last = (end == total)
                    new_items, self._buffer = self._extract_items_from_chunk(
                        chunk_text, is_last=is_last
                    )
                    items_found.extend(new_items)
                    del chunk_text, new_items

                    # Proteção OOM: buffer residual não pode crescer infinitamente
                    if len(self._buffer) > self._MAX_BUF_CHARS:
                        # Mantém apenas os últimos MAX_BUF_CHARS (dados recentes)
                        self._buffer = self._buffer[-self._MAX_BUF_CHARS:]

                    gc.collect()

            prog_txt.empty()
            prog_bar.empty()

            if self._buffer.strip():
                new_items, _ = self._extract_items_from_chunk(self._buffer, is_last=True)
                items_found.extend(new_items)

            self._buffer = ""
            gc.collect()

            if not items_found:
                st.warning("⚠️ Padrão 'ITENS DA DUIMP' não encontrado. Verifique o formato do PDF.")

            self.documento['itens'] = items_found
            self._calculate_totals()
            return self.documento

        except Exception as e:
            logger.error(f"Erro HafelePDFParser: {e}")
            st.error(f"Erro ao ler PDF: {str(e)}")
            return self.documento""",
    """\
    def parse_pdf(self, pdf_path: str) -> Dict:
        # fitz (PyMuPDF): abertura lazy ~30MB vs pdfplumber ~600MB para 1200 págs
        try:
            prog_txt = st.empty()
            prog_bar = st.progress(0)
            items_found: list = []
            self._buffer = ""

            doc = fitz.open(pdf_path)
            total = doc.page_count
            chunk = _PDF_CHUNK_PAGES

            try:
                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(
                        f"Processando páginas {start+1}–{end} de {total} "
                        f"(Extrato DUIMP)... {int((end/total)*100)}%"
                    )
                    prog_bar.progress(end / total)

                    chunk_lines = []
                    for idx in range(start, end):
                        page = doc[idx]
                        t = page.get_text("text")
                        page = None          # libera objeto fitz imediatamente
                        if t:
                            chunk_lines.append(t)
                        del t

                    chunk_text = self._buffer + "\\n".join(chunk_lines)
                    del chunk_lines

                    is_last = (end == total)
                    new_items, self._buffer = self._extract_items_from_chunk(
                        chunk_text, is_last=is_last
                    )
                    items_found.extend(new_items)
                    del chunk_text, new_items

                    if len(self._buffer) > self._MAX_BUF_CHARS:
                        self._buffer = self._buffer[-self._MAX_BUF_CHARS:]

                    gc.collect()
            finally:
                doc.close()

            prog_txt.empty()
            prog_bar.empty()

            if self._buffer.strip():
                new_items, _ = self._extract_items_from_chunk(self._buffer, is_last=True)
                items_found.extend(new_items)

            self._buffer = ""
            gc.collect()

            if not items_found:
                st.warning("⚠️ Padrão 'ITENS DA DUIMP' não encontrado. Verifique o formato do PDF.")

            self.documento['itens'] = items_found
            self._calculate_totals()
            return self.documento

        except Exception as e:
            logger.error(f"Erro HafelePDFParser: {e}")
            st.error(f"Erro ao ler PDF: {str(e)}")
            return self.documento""",
    src,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. SigrawebPDFParser.parse_pdf COMPLETO — pdfplumber → fitz
# ═══════════════════════════════════════════════════════════════════════════════
src = aplicar(
    "SIGRAWEB_PARSE_PDF",
    """\
    def parse_pdf(self, pdf_path: str) -> Dict:
        try:
            prog_txt = st.empty()
            prog_bar = st.progress(0)
            items_found: list = []
            buffer = ""

            with pdfplumber.open(pdf_path) as pdf:
                total = len(pdf.pages)
                chunk = _PDF_CHUNK_PAGES

                p1 = pdf.pages[0].extract_text(layout=False) or "" if total > 0 else ""
                p2 = pdf.pages[1].extract_text(layout=False) or "" if total > 1 else ""
                self._extract_header(p1, p2)
                del p1, p2

                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(
                        f"Processando páginas {start+1}–{end} de {total} "
                        f"(Sigraweb)... {int((end/total)*100)}%"
                    )
                    prog_bar.progress(end / total)

                    chunk_pages = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_pages.append(t)

                    chunk_text = buffer + "\\n".join(chunk_pages)
                    del chunk_pages

                    is_last    = (end == total)
                    new_items, buffer = self._extract_items_from_chunk(
                        chunk_text, is_last=is_last
                    )
                    items_found.extend(new_items)
                    del chunk_text, new_items

                    # Proteção OOM: buffer residual não pode crescer infinitamente
                    if len(buffer) > self._MAX_BUF_CHARS:
                        buffer = buffer[-self._MAX_BUF_CHARS:]

                    gc.collect()

            prog_txt.empty()
            prog_bar.empty()

            if buffer.strip():
                new_items, _ = self._extract_items_from_chunk(buffer, is_last=True)
                items_found.extend(new_items)

            buffer = ""
            gc.collect()

            if not items_found:
                st.warning("⚠️ Nenhuma adição detectada no PDF Sigraweb.")

            self.documento['itens'] = items_found
            self._calculate_totals()
            return self.documento

        except Exception as e:
            logger.error(f"Erro SigrawebPDFParser: {e}")
            st.error(f"Erro ao ler PDF Sigraweb: {str(e)}")
            return self.documento""",
    """\
    def parse_pdf(self, pdf_path: str) -> Dict:
        # fitz (PyMuPDF): mesma razão do HafelePDFParser
        try:
            prog_txt = st.empty()
            prog_bar = st.progress(0)
            items_found: list = []
            buffer = ""

            doc = fitz.open(pdf_path)
            total = doc.page_count
            chunk = _PDF_CHUNK_PAGES

            try:
                p1 = doc[0].get_text("text") if total > 0 else ""
                p2 = doc[1].get_text("text") if total > 1 else ""
                self._extract_header(p1, p2)
                del p1, p2

                for start in range(0, total, chunk):
                    end = min(start + chunk, total)
                    prog_txt.text(
                        f"Processando páginas {start+1}–{end} de {total} "
                        f"(Sigraweb)... {int((end/total)*100)}%"
                    )
                    prog_bar.progress(end / total)

                    chunk_pages = []
                    for idx in range(start, end):
                        page = doc[idx]
                        t = page.get_text("text")
                        page = None          # libera objeto fitz imediatamente
                        if t:
                            chunk_pages.append(t)
                        del t

                    chunk_text = buffer + "\\n".join(chunk_pages)
                    del chunk_pages

                    is_last    = (end == total)
                    new_items, buffer = self._extract_items_from_chunk(
                        chunk_text, is_last=is_last
                    )
                    items_found.extend(new_items)
                    del chunk_text, new_items

                    if len(buffer) > self._MAX_BUF_CHARS:
                        buffer = buffer[-self._MAX_BUF_CHARS:]

                    gc.collect()
            finally:
                doc.close()

            prog_txt.empty()
            prog_bar.empty()

            if buffer.strip():
                new_items, _ = self._extract_items_from_chunk(buffer, is_last=True)
                items_found.extend(new_items)

            buffer = ""
            gc.collect()

            if not items_found:
                st.warning("⚠️ Nenhuma adição detectada no PDF Sigraweb.")

            self.documento['itens'] = items_found
            self._calculate_totals()
            return self.documento

        except Exception as e:
            logger.error(f"Erro SigrawebPDFParser: {e}")
            st.error(f"Erro ao ler PDF Sigraweb: {str(e)}")
            return self.documento""",
    src,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Validação de sintaxe — não grava se houver erro
# ═══════════════════════════════════════════════════════════════════════════════
print("\n🔍 Validando sintaxe Python...")
try:
    ast.parse(src)
    print("✅ Sintaxe OK")
except SyntaxError as e:
    print(f"❌ ERRO DE SINTAXE na linha {e.lineno}: {e.msg}")
    print("   Arquivo NÃO foi gravado. Backup intacto.")
    raise SystemExit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# Verificações adicionais pós-patch
# ═══════════════════════════════════════════════════════════════════════════════
assert "pdfplumber.open" not in src, "❌ pdfplumber.open ainda presente no código!"
assert "_PDF_CHUNK_PAGES = 8" in src, "❌ chunk size não foi atualizado!"
assert "fitz.open(pdf_path)" in src, "❌ fitz.open não encontrado!"
print("✅ Verificações pós-patch: OK (sem pdfplumber.open, chunk=8, fitz presente)")

# ═══════════════════════════════════════════════════════════════════════════════
# Gravar
# ═══════════════════════════════════════════════════════════════════════════════
APP.write_text(src, encoding="utf-8")
print(f"\n🏁 Patch FINAL gravado em {APP.resolve()}")
print(f"   Backup em: {APP.with_suffix('.py.bak_final').resolve()}")
print("""
Resumo de todas as alterações aplicadas:
  ┌────────────────────────────────────────────────────────────────────────────┐
  │  #  Onde                          Mudança                   RAM salva     │
  ├────────────────────────────────────────────────────────────────────────────┤
  │  1  Global                        chunk: 20 → 8 págs        -60%/iter     │
  │  2  HafelePDFParser               buffer: 500K → 200K       -60% buffer   │
  │  3  SigrawebPDFParser             buffer: 500K → 200K       -60% buffer   │
  │  4  DuimpPDFParser.preprocess     del raw por página        -N×PageSize   │
  │  5  HafelePDFParser.parse_pdf     pdfplumber → fitz         -95% abertura │
  │  6  SigrawebPDFParser.parse_pdf   pdfplumber → fitz         -95% abertura │
  ├────────────────────────────────────────────────────────────────────────────┤
  │  Pico total estimado: >1GB (crash) → ~200MB (dentro do limite do Cloud)   │
  └────────────────────────────────────────────────────────────────────────────┘
""")
