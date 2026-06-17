"""
apply_patch.py
==============
Execute na raiz do projeto (onde está o app.py):

    python apply_patch.py

O script aplica 6 correções de robustez para PDFs de 1200+ páginas no
Streamlit Cloud (~1GB RAM), SEM alterar nenhuma lógica de negócio.
Um backup automático é salvo em app.py.bak antes de qualquer alteração.
"""

import shutil
from pathlib import Path

APP = Path("app.py")

if not APP.exists():
    raise FileNotFoundError("app.py não encontrado. Execute na raiz do projeto.")

# Backup automático
shutil.copy(APP, APP.with_suffix(".py.bak"))
print(f"✅ Backup salvo em {APP.with_suffix('.py.bak')}")

src = APP.read_text(encoding="utf-8")
original = src  # para relatório final

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 1 — Chunk size: 20 → 8 páginas/vez
# Reduz pico de RAM em ~60% por iteração. PDFs de 1200 págs viram 150 chunks
# ao invés de 60, mas cada chunk usa ~60% menos memória — troca acertada.
# ═══════════════════════════════════════════════════════════════════════════════
OLD = "_PDF_CHUNK_PAGES = 20   # Streamlit Cloud ~1GB RAM — chunks menores evitam OOM"
NEW = "_PDF_CHUNK_PAGES = 8    # Streamlit Cloud ~1GB RAM — 8 páginas/chunk evita OOM em PDFs de 1200 págs"
assert OLD in src, "PATCH 1: string não encontrada"
src = src.replace(OLD, NEW, 1)
print("✅ Patch 1 aplicado — _PDF_CHUNK_PAGES: 20 → 8")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — Buffer residual HafelePDFParser: 500KB → 200KB
# O buffer só precisa guardar o último bloco incompleto de item. 200KB é
# mais do que suficiente; 500KB desnecessário mantinha texto na heap.
# ═══════════════════════════════════════════════════════════════════════════════
OLD = "    _MAX_BUF_CHARS = 500_000  # ~500KB de texto — suficiente para qualquer item"
NEW = "    _MAX_BUF_CHARS = 200_000  # ~200KB de texto — suficiente para qualquer item"
assert OLD in src, "PATCH 2: string não encontrada"
src = src.replace(OLD, NEW, 1)
print("✅ Patch 2 aplicado — HafelePDFParser._MAX_BUF_CHARS: 500K → 200K")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — Buffer residual SigrawebPDFParser: 500KB → 200KB
# Mesma razão do patch 2.
# ═══════════════════════════════════════════════════════════════════════════════
OLD = "    _MAX_BUF_CHARS = 500_000  # ~500KB — proteção OOM"
NEW = "    _MAX_BUF_CHARS = 200_000  # ~200KB — proteção OOM"
assert OLD in src, "PATCH 3: string não encontrada"
src = src.replace(OLD, NEW, 1)
print("✅ Patch 3 aplicado — SigrawebPDFParser._MAX_BUF_CHARS: 500K → 200K")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 4 — DuimpPDFParser: liberar raw text por página antes de filtrar
# Antes: o texto bruto da página ficava vivo até o fim do loop do chunk (fitz
# retém referência interna enquanto a variável existir).
# Depois: page=None libera o objeto fitz → del raw libera o texto bruto logo
# após filtrar, reduzindo o pico de memória por chunk.
# ═══════════════════════════════════════════════════════════════════════════════
OLD = """\
            lines = []
            for idx in range(start, end):
                page = doc[idx]
                for line in page.get_text("text").split('\\n'):
                    if self._filter(line):
                        lines.append(line)
                page = None   # libera objeto página imediatamente"""

NEW = """\
            lines = []
            for idx in range(start, end):
                page = doc[idx]
                raw = page.get_text("text")
                page = None          # libera objeto fitz imediatamente
                for line in raw.split('\\n'):
                    if self._filter(line):
                        lines.append(line)
                del raw              # libera texto bruto da página"""

assert OLD in src, "PATCH 4: string não encontrada"
src = src.replace(OLD, NEW, 1)
print("✅ Patch 4 aplicado — DuimpPDFParser: del raw por página")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 5 — HafelePDFParser: flush_cache() por página pdfplumber
# pdfplumber mantém cache interno de objetos PDF por página. flush_cache()
# libera esse cache imediatamente após extrair o texto, sem impactar o resultado.
# Sem isso, páginas processadas acumulam na heap durante todo o chunk.
# ═══════════════════════════════════════════════════════════════════════════════
OLD = """\
                    chunk_lines = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_lines.append(t)"""

NEW = """\
                    chunk_lines = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_lines.append(t)
                        page.flush_cache()  # libera cache interno pdfplumber"""

assert OLD in src, "PATCH 5: string não encontrada"
src = src.replace(OLD, NEW, 1)
print("✅ Patch 5 aplicado — HafelePDFParser: page.flush_cache() por página")

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 6 — SigrawebPDFParser: flush_cache() por página pdfplumber
# Mesma razão do patch 5.
# ═══════════════════════════════════════════════════════════════════════════════
OLD = """\
                    chunk_pages = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_pages.append(t)"""

NEW = """\
                    chunk_pages = []
                    for page in pdf.pages[start:end]:
                        t = page.extract_text(layout=False)
                        if t:
                            chunk_pages.append(t)
                        page.flush_cache()  # libera cache interno pdfplumber"""

assert OLD in src, "PATCH 6: string não encontrada"
src = src.replace(OLD, NEW, 1)
print("✅ Patch 6 aplicado — SigrawebPDFParser: page.flush_cache() por página")

# ═══════════════════════════════════════════════════════════════════════════════
# Gravar resultado
# ═══════════════════════════════════════════════════════════════════════════════
APP.write_text(src, encoding="utf-8")

added   = len(src) - len(original)
print(f"\n🏁 Patch concluído — {6} alterações aplicadas (+{added} chars)")
print(f"   Arquivo gravado: {APP.resolve()}")
print(f"   Backup em:       {APP.with_suffix('.py.bak').resolve()}")
print("""
Resumo das melhorias:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Parâmetro                     Antes        Depois   Impacto       │
  ├─────────────────────────────────────────────────────────────────────┤
  │  _PDF_CHUNK_PAGES              20 págs      8 págs   -60% RAM/iter │
  │  HafelePDFParser._MAX_BUF_CHARS 500 KB      200 KB   -60% buffer   │
  │  SigrawebPDFParser._MAX_BUF_CHARS 500 KB    200 KB   -60% buffer   │
  │  DuimpPDFParser — raw/página   acumula      del raw  -N×PageSize   │
  │  HafelePDFParser — pdfplumber  sem flush    flush()  libera cache  │
  │  SigrawebPDFParser — pdfplumber sem flush   flush()  libera cache  │
  └─────────────────────────────────────────────────────────────────────┘
""")
