"""
apply_patch_v3.py
=================
Execute na raiz do projeto (onde está o app.py):

    python apply_patch_v3.py

CORREÇÃO DO PATCH v2:
  O patch v2 introduziu um SyntaxError: substituía apenas a abertura do
  método parse_pdf, deixando o bloco `try` externo sem seu `except` final.
  O app passava a morrer em idle, sem nenhum upload.

  Este patch v3 substitui o método parse_pdf COMPLETO (do `def` até o
  `except Exception` final), garantindo estrutura try/except válida.

ESTRATÉGIA:
  - Substitui o método parse_pdf INTEIRO em cada parser
  - Troca pdfplumber por fitz (PyMuPDF) apenas na camada de I/O
  - Toda lógica de negócio, regex, chunking, buffer e except são mantidos
"""

import shutil
from pathlib import Path

APP = Path("app.py")

if not APP.exists():
    raise FileNotFoundError("app.py não encontrado. Execute na raiz do projeto.")

shutil.copy(APP, APP.with_suffix(".py.bak3"))
print(f"✅ Backup salvo em {APP.with_suffix('.py.bak3')}")

src = APP.read_text(encoding="utf-8")
original_len = len(src)

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 1 — HafelePDFParser.parse_pdf — método COMPLETO
# Substitui pdfplumber por fitz. Mantém toda lógica (regex, chunks, buffer,
# pós-processamento, except) inalterada.
# ═══════════════════════════════════════════════════════════════════════════════

OLD_HAFELE = '''\
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
                        page.flush_cache()  # libera cache interno pdfplumber

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
            return self.documento'''

NEW_HAFELE = '''\
    def parse_pdf(self, pdf_path: str) -> Dict:
        # fitz (PyMuPDF): abertura lazy ~30MB vs pdfplumber/pdfminer ~600MB
        # para PDFs de 1200 págs — elimina OOM antes mesmo do 1º chunk.
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

                    # Proteção OOM: buffer residual não pode crescer infinitamente
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
            return self.documento'''

assert OLD_HAFELE in src, (
    "PATCH 1 (HafelePDFParser): método não encontrado.\n"
    "Verifique se os patches v1 e v2 foram aplicados corretamente,\n"
    "ou restaure o backup (app.py.bak) e aplique apenas este patch v3."
)
src = src.replace(OLD_HAFELE, NEW_HAFELE, 1)
print("✅ Patch 1 aplicado — HafelePDFParser.parse_pdf: pdfplumber → fitz (método completo)")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — SigrawebPDFParser.parse_pdf — método COMPLETO
# ═══════════════════════════════════════════════════════════════════════════════

OLD_SIGRAWEB = '''\
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
                        page.flush_cache()  # libera cache interno pdfplumber

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
            return self.documento'''

NEW_SIGRAWEB = '''\
    def parse_pdf(self, pdf_path: str) -> Dict:
        # fitz (PyMuPDF): mesma razão do HafelePDFParser —
        # abertura lazy elimina OOM em PDFs de 1200+ páginas.
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

                    # Proteção OOM: buffer residual não pode crescer infinitamente
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
            return self.documento'''

assert OLD_SIGRAWEB in src, (
    "PATCH 2 (SigrawebPDFParser): método não encontrado.\n"
    "Verifique o estado atual do app.py."
)
src = src.replace(OLD_SIGRAWEB, NEW_SIGRAWEB, 1)
print("✅ Patch 2 aplicado — SigrawebPDFParser.parse_pdf: pdfplumber → fitz (método completo)")

# ═══════════════════════════════════════════════════════════════════════════════
# Validação de sintaxe antes de gravar
# ═══════════════════════════════════════════════════════════════════════════════
import ast
try:
    ast.parse(src)
    print("✅ Validação de sintaxe Python: OK")
except SyntaxError as e:
    print(f"❌ ERRO DE SINTAXE: {e}")
    print("   Arquivo NÃO gravado. Corrija o erro antes de continuar.")
    raise SystemExit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# Gravar resultado
# ═══════════════════════════════════════════════════════════════════════════════
APP.write_text(src, encoding="utf-8")

print(f"\n🏁 Patch v3 concluído — 2 substituições aplicadas")
print(f"   Arquivo gravado: {APP.resolve()}")
print(f"   Backup em:       {APP.with_suffix('.py.bak3').resolve()}")
print("""
Resumo das correções acumuladas (v1 + v3):
  ┌────────────────────────────────────────────────────────────────────────┐
  │  Patch  Onde                        O que mudou                       │
  ├────────────────────────────────────────────────────────────────────────┤
  │  v1-1   Global                      _PDF_CHUNK_PAGES: 20 → 8         │
  │  v1-2   HafelePDFParser             _MAX_BUF_CHARS: 500K → 200K      │
  │  v1-3   SigrawebPDFParser           _MAX_BUF_CHARS: 500K → 200K      │
  │  v1-4   DuimpPDFParser              del raw por página (fitz)         │
  │  v3-1   HafelePDFParser.parse_pdf   pdfplumber → fitz (método todo)  │
  │  v3-2   SigrawebPDFParser.parse_pdf pdfplumber → fitz (método todo)  │
  └────────────────────────────────────────────────────────────────────────┘

Nota: o patch v2 foi substituído pelo v3 (v2 tinha bug de SyntaxError).
Se você aplicou o v2, restaure app.py.bak2 e aplique v1 + v3 em sequência.
""")
