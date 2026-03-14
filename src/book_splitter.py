"""
book_splitter.py — Divide PDFs de livros em capítulos/chunks para processamento.

Estratégias disponíveis (em ordem de preferência no modo automático):
  A) outlines  — usa bookmarks/outline do PDF (metadados)
  B) links     — lê links /Annots das páginas de sumário (TOC clicável)
  C) pages     — divide em blocos de N páginas (fallback garantido)

Uso básico:
    from src.book_splitter import smart_split
    strategy, paths = smart_split("livro.pdf", "output/chapters/")

Baseado nos scripts do usuário para "Walls Airway Management" e "HC Emergência".
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------

class ChapterInfo(NamedTuple):
    number: int | None   # número do capítulo (None para chunks por página)
    title: str
    start_page: int      # 0-based
    end_page: int        # 0-based, inclusive


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[\/\\:\*\?\"<>\|]+", " - ", s)
    s = re.sub(r"\s+", " ", s)
    return s[:180].strip() or "Untitled"


def _try_import_pypdf():
    try:
        from pypdf import PdfReader, PdfWriter
        return PdfReader, PdfWriter
    except ImportError:
        print(
            "Erro: pypdf não instalado. Execute: pip install pypdf>=4.0",
            file=sys.stderr,
        )
        sys.exit(1)


def _write_chapters(pdf_path: str, chapters: list[ChapterInfo], output_dir: str) -> list[str]:
    """Escreve cada ChapterInfo como um PDF separado. Retorna lista de caminhos."""
    PdfReader, PdfWriter = _try_import_pypdf()
    reader = PdfReader(pdf_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for idx, ch in enumerate(chapters, start=1):
        writer = PdfWriter()
        for p in range(ch.start_page, ch.end_page + 1):
            if 0 <= p < len(reader.pages):
                writer.add_page(reader.pages[p])

        prefix = f"{idx:03d}"
        safe_title = sanitize_filename(ch.title)
        fname = f"{prefix} - {safe_title}.pdf"
        fpath = out / fname
        with open(fpath, "wb") as f:
            writer.write(f)

        pages_label = f"p.{ch.start_page + 1}-{ch.end_page + 1}"
        print(f"  [OK] {fname}  ({pages_label})")
        paths.append(str(fpath))

    return paths


# ---------------------------------------------------------------------------
# Estratégia A: outline / bookmarks
# ---------------------------------------------------------------------------

def _flatten_outlines(reader) -> list[tuple[int, str, int]]:
    """Retorna [(level, title, page_0based), ...] em ordem de página."""
    out: list[tuple[int, str, int]] = []
    outlines = getattr(reader, "outlines", None) or getattr(reader, "outline", None)
    if not outlines:
        return out

    def walk(items, level):
        for it in items:
            if isinstance(it, list):
                walk(it, level + 1)
            else:
                try:
                    title = (getattr(it, "title", None) or str(it)).strip()
                    page = reader.get_destination_page_number(it)
                    out.append((level, title, page))
                except Exception:
                    pass

    try:
        walk(outlines, level=0)
    except Exception:
        return []

    out.sort(key=lambda x: x[2])
    return out


def _is_chapter_entry(title: str) -> bool:
    """Aceita '1. Título' ou '12. Título' — rejeita '1.1 ...'."""
    return bool(re.match(r"^\d{1,2}\.\s+\S", (title or "").strip()))


def split_by_outlines(
    pdf_path: str,
    output_dir: str,
    min_pages: int = 5,
) -> list[str]:
    """
    Divide o PDF usando bookmarks/outline (metadados).
    Capítulos menores que min_pages são agrupados no anterior.
    Retorna lista de caminhos dos PDFs gerados.
    """
    PdfReader, _ = _try_import_pypdf()
    reader = PdfReader(pdf_path)
    n = len(reader.pages)
    outline = _flatten_outlines(reader)

    if not outline:
        print("  [!] Nenhum outline encontrado.")
        return []

    # Filtra apenas entradas de capítulo nível-1
    chap_candidates = [(lvl, t, p) for lvl, t, p in outline if _is_chapter_entry(t)]
    if not chap_candidates:
        # fallback: usa o nível mais raso do outline inteiro
        level_counts = Counter(lvl for lvl, _, _ in outline)
        top_level = level_counts.most_common(1)[0][0]
        chap_candidates = [(lvl, t, p) for lvl, t, p in outline if lvl <= top_level]

    if not chap_candidates:
        print("  [!] Outline encontrado mas sem entradas de capítulo identificáveis.")
        return []

    # Determina o nível de capítulo mais comum
    level_counts = Counter(lvl for lvl, _, _ in chap_candidates)
    chapter_level = level_counts.most_common(1)[0][0]
    filtered = sorted(
        {p: t for lvl, t, p in chap_candidates if lvl <= chapter_level}.items()
    )  # {page: title} dedup por página

    # Monta ChapterInfo
    raw: list[tuple[str, int]] = [(t, p) for p, t in filtered if 0 <= p < n]
    chapters: list[ChapterInfo] = []
    for idx, (title, start) in enumerate(raw):
        end = raw[idx + 1][1] - 1 if idx + 1 < len(raw) else n - 1
        if end < start:
            continue
        if chapters and (end - start + 1) < min_pages:
            # agrupa no anterior
            prev = chapters[-1]
            chapters[-1] = ChapterInfo(prev.number, prev.title, prev.start_page, end)
            continue
        chapters.append(ChapterInfo(idx + 1, title, start, end))

    print(f"  Estratégia: outlines — {len(chapters)} capítulos detectados")
    return _write_chapters(pdf_path, chapters, output_dir)


# ---------------------------------------------------------------------------
# Estratégia B: links /Annots no sumário
# ---------------------------------------------------------------------------

def _get_link_annots_sorted(page) -> list[tuple[float, object]]:
    """Retorna [(y_top, annot)] de links na página, ordenados top→bottom."""
    out: list[tuple[float, object]] = []
    try:
        from pypdf.generic import IndirectObject
        annots = page.get("/Annots")
        if not annots:
            return out
        for a in annots:
            try:
                if isinstance(a, IndirectObject):
                    a = a.get_object()
                if str(a.get("/Subtype")) != "/Link":
                    continue
                rect = a.get("/Rect")
                if not rect or len(rect) != 4:
                    continue
                y_top = float(max(rect[1], rect[3]))
                out.append((y_top, a))
            except Exception:
                pass
    except Exception:
        pass
    out.sort(key=lambda t: -t[0])
    return out


def _dest_to_page_index(reader, annot) -> int | None:
    """Resolve destino de link interno para índice 0-based da página."""
    try:
        from pypdf.generic import (
            IndirectObject, NumberObject, NameObject,
            ByteStringObject, TextStringObject,
        )

        action = annot.get("/A")
        if action and str(action.get("/S")) == "/URI":
            return None

        dest = annot.get("/Dest")
        if dest is None and action and str(action.get("/S")) == "/GoTo":
            dest = action.get("/D")
        if dest is None:
            return None

        if isinstance(dest, IndirectObject):
            dest = dest.get_object()

        # Array: [pageRef, /Fit ...]
        if isinstance(dest, list) and dest:
            page_ref = dest[0]
            if isinstance(page_ref, (int, float, NumberObject)):
                idx = int(page_ref)
                if 0 <= idx < len(reader.pages):
                    return idx
            # Referência indireta
            if isinstance(page_ref, IndirectObject):
                for i, p in enumerate(reader.pages):
                    if getattr(p, "indirect_reference", None) == page_ref:
                        return i
            try:
                return reader.get_page_number(page_ref)
            except Exception:
                pass

        # Named destination
        if isinstance(dest, (TextStringObject, NameObject)):
            sd = str(dest)
        elif isinstance(dest, (ByteStringObject, bytes)):
            try:
                sd = bytes(dest).decode("utf-8")
            except Exception:
                sd = bytes(dest).decode("latin-1", errors="ignore")
        else:
            sd = str(dest)

        named = getattr(reader, "named_destinations", None) or {}
        for key in (sd, sd.lstrip("/"), "/" + sd.lstrip("/")):
            if key in named:
                try:
                    return reader.get_destination_page_number(named[key])
                except Exception:
                    pass

        try:
            return reader.get_destination_page_number(dest)
        except Exception:
            return None

    except Exception:
        return None


def _extract_heading_from_page(reader, page_idx: int) -> tuple[int | None, str | None]:
    """Extrai (número, título) do heading de um capítulo numa página."""
    try:
        text = reader.pages[page_idx].extract_text() or ""
    except Exception:
        return (None, None)
    if not text.strip():
        return (None, None)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    filtered = [
        ln for ln in lines[:40]
        if not ln.lower().startswith(("consulta rápida", "pontos importantes", "seção"))
        and ln.count(",") < 2
    ]

    # Caso inline: "N Título" ou "N. Título"
    pat_inline = re.compile(r"^(\d{1,4})\s*\.?\s+(.+?)\s*$")
    for ln in filtered[:20]:
        m = pat_inline.match(ln)
        if m:
            num, title = int(m.group(1)), m.group(2).strip()
            if 3 <= len(title) <= 120 and title[0].isalpha():
                return (num, title)

    # Caso: número sozinho + título na linha seguinte
    pat_num = re.compile(r"^(\d{1,4})\s*$")
    for i, ln in enumerate(filtered[:20]):
        m = pat_num.match(ln)
        if m and i + 1 < len(filtered):
            nxt = filtered[i + 1]
            if 3 <= len(nxt) <= 120 and nxt[0].isalpha() and nxt.count(".") <= 2:
                return (int(m.group(1)), nxt)

    return (None, None)


def _find_heading_near_start(
    reader, start: int, max_lookahead: int = 3
) -> tuple[int | None, str | None, int]:
    """Procura heading nas próximas páginas (pula páginas de seção). Retorna (num, title, page_0based)."""
    n = len(reader.pages)
    for off in range(max_lookahead + 1):
        p = start + off
        if p >= n:
            break
        num, title = _extract_heading_from_page(reader, p)
        if num is not None:
            return (num, title, p)
    return (None, None, start)


def split_by_toc_links(
    pdf_path: str,
    output_dir: str,
    toc_pages: list[int],
    max_lookahead: int = 3,
) -> list[str]:
    """
    Divide usando links /Annots nas páginas de sumário (0-based).
    Nomeia capítulos pelo heading real da página do capítulo.
    Retorna lista de caminhos dos PDFs gerados.
    """
    PdfReader, _ = _try_import_pypdf()
    reader = PdfReader(pdf_path)
    n = len(reader.pages)

    # Coleta destinos dos links
    dest_pages: list[int] = []
    for toc_p in toc_pages:
        if not (0 <= toc_p < n):
            continue
        for _, annot in _get_link_annots_sorted(reader.pages[toc_p]):
            p = _dest_to_page_index(reader, annot)
            if p is not None and 0 <= p < n:
                dest_pages.append(p)

    if not dest_pages:
        print("  [!] split_by_toc_links: nenhum destino de link resolvido.")
        return []

    starts = sorted(set(dest_pages))

    # Mapeia número do capítulo → (título, página_heading)
    chapters_by_num: dict[int, tuple[str, int]] = {}
    unnamed: list[tuple[str, int]] = []

    for start in starts:
        num, title, heading_p = _find_heading_near_start(reader, start, max_lookahead)
        if num is None or title is None:
            unnamed.append((f"Seção p.{start + 1}", heading_p))
            continue
        if num not in chapters_by_num or heading_p < chapters_by_num[num][1]:
            chapters_by_num[num] = (title, heading_p)

    ordered: list[tuple[int | None, str, int]] = [
        (num, t, p) for num, (t, p) in chapters_by_num.items()
    ] + [(None, t, p) for t, p in unnamed]
    ordered.sort(key=lambda x: x[2])

    if not ordered:
        print("  [!] split_by_toc_links: nenhum capítulo válido após resolução.")
        return []

    chapters: list[ChapterInfo] = []
    for idx, (num, title, start) in enumerate(ordered):
        end = ordered[idx + 1][2] - 1 if idx + 1 < len(ordered) else n - 1
        if end >= start:
            chapters.append(ChapterInfo(num, title, start, end))

    print(f"  Estratégia: toc_links — {len(chapters)} capítulos detectados")
    return _write_chapters(pdf_path, chapters, output_dir)


# ---------------------------------------------------------------------------
# Estratégia C: blocos fixos de páginas
# ---------------------------------------------------------------------------

def split_by_pages(
    pdf_path: str,
    output_dir: str,
    chunk_size: int = 100,
) -> list[str]:
    """
    Divide em blocos de chunk_size páginas. Fallback garantido.
    Retorna lista de caminhos dos PDFs gerados.
    """
    PdfReader, _ = _try_import_pypdf()
    reader = PdfReader(pdf_path)
    n = len(reader.pages)

    chapters: list[ChapterInfo] = []
    for i, start in enumerate(range(0, n, chunk_size), start=1):
        end = min(start + chunk_size - 1, n - 1)
        chapters.append(ChapterInfo(i, f"Parte {i:03d}", start, end))

    print(f"  Estratégia: pages (chunk={chunk_size}) — {len(chapters)} partes")
    return _write_chapters(pdf_path, chapters, output_dir)


# ---------------------------------------------------------------------------
# Smart split (auto-detect)
# ---------------------------------------------------------------------------

def smart_split(
    pdf_path: str,
    output_dir: str,
    toc_pages: list[int] | None = None,
    chunk_size: int = 100,
    min_pages: int = 5,
    max_lookahead: int = 3,
) -> tuple[str, list[str]]:
    """
    Auto-detecta a melhor estratégia:
      1. outline/bookmarks com >= 3 capítulos  → split_by_outlines
      2. toc_pages informadas                  → split_by_toc_links
      3. fallback                              → split_by_pages

    Retorna (strategy_name, [pdf_paths]).
    """
    PdfReader, _ = _try_import_pypdf()
    reader = PdfReader(pdf_path)
    print(f"\n📖 PDF: {Path(pdf_path).name} ({len(reader.pages)} páginas)")

    # Tenta outline
    outline = _flatten_outlines(reader)
    chap_candidates = [t for _, t, _ in outline if _is_chapter_entry(t)]
    has_good_outline = len(chap_candidates) >= 3

    if has_good_outline:
        print("  Outline detectado — tentando split_by_outlines...")
        paths = split_by_outlines(pdf_path, output_dir, min_pages=min_pages)
        if paths:
            return ("outlines", paths)
        print("  Outline falhou, tentando próxima estratégia...")

    if toc_pages:
        print(f"  toc_pages={toc_pages} — tentando split_by_toc_links...")
        paths = split_by_toc_links(pdf_path, output_dir, toc_pages, max_lookahead)
        if paths:
            return ("toc_links", paths)
        print("  toc_links falhou, usando fallback por páginas...")

    paths = split_by_pages(pdf_path, output_dir, chunk_size)
    return ("pages", paths)
