#!/usr/bin/env python3
"""
run_book.py — Processa um livro PDF completo com marker ou mineru.

Divide o PDF em capítulos (opcional), converte cada um e concatena
os markdowns em um único document_final.md.

Uso:
    # Marker com split automático
    python scripts/run_book.py --input livro.pdf --output output/ --tool marker

    # MinerU sem split (arquivo inteiro)
    python scripts/run_book.py --input livro.pdf --output output/ --tool mineru --split none

    # Split por links de sumário (páginas 15-22 no visualizador)
    python scripts/run_book.py --input livro.pdf --output output/ --tool marker \\
        --split links --toc-pages 15-22

    # Split por blocos de 80 páginas
    python scripts/run_book.py --input livro.pdf --output output/ --tool mineru \\
        --split pages --chunk-size 80
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.book_splitter import smart_split, split_by_outlines, split_by_toc_links, split_by_pages
from src.run_marker import run_marker
from src.run_mineru import run_mineru
from src.run_result import RunResult, combine_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_toc_pages(spec: str) -> list[int]:
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a) - 1, int(b)))
        else:
            pages.append(int(part) - 1)
    return sorted(set(pages))


def _find_markdown(out_dir: Path) -> Path | None:
    """Encontra o markdown principal gerado por marker ou mineru."""
    # Marker cria: out_dir/<pdf_stem>/<pdf_stem>.md
    # MinerU cria: out_dir/<pdf_stem>/auto/<pdf_stem>.md (ou similar)
    for pattern in ["**/*.md", "**/*.txt"]:
        matches = sorted(out_dir.rglob(pattern.replace("**/", "")))
        if not matches:
            matches = sorted(out_dir.rglob(pattern))
        if matches:
            # prefere arquivos maiores (documento completo vs sumário)
            return max(matches, key=lambda p: p.stat().st_size)
    return None


def _run_tool(tool: str, pdf_path: str, chunk_out: Path) -> RunResult:
    chunk_out.mkdir(parents=True, exist_ok=True)
    if tool == "marker":
        return run_marker(pdf_path, str(chunk_out))
    elif tool == "mineru":
        return run_mineru(pdf_path, str(chunk_out))
    else:
        return RunResult(tool, "failed", f"Ferramenta desconhecida: {tool}")


def _chapter_title_from_path(pdf_path: Path) -> str:
    """Extrai título legível do nome do arquivo de capítulo: '003 - Titulo' → 'Titulo'."""
    name = pdf_path.stem
    # Remove prefixo numérico: '003 - Titulo do Capitulo' → 'Titulo do Capitulo'
    name = name.lstrip("0123456789 -.")
    return name.strip() or pdf_path.stem


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run_book(
    input_pdf: str,
    output_dir: str,
    tool: str,
    split_method: str = "auto",
    toc_pages: list[int] | None = None,
    chunk_size: int = 100,
    min_pages: int = 5,
) -> tuple[list[RunResult], Path | None]:
    """
    Processa um livro completo.

    Retorna (lista de RunResult por chunk, Path do document_final.md ou None).
    """
    pdf = Path(input_pdf).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    # -------------------------
    # 1. Split
    # -------------------------
    if split_method == "none":
        chunk_pdfs = [str(pdf)]
        strategy = "none"
        print(f"\n📖 Processando arquivo completo: {pdf.name}")
    else:
        split_dir = out / "_chunks"
        split_dir.mkdir(parents=True, exist_ok=True)

        if split_method == "auto":
            strategy, chunk_pdfs = smart_split(
                str(pdf), str(split_dir),
                toc_pages=toc_pages, chunk_size=chunk_size, min_pages=min_pages,
            )
        elif split_method == "outlines":
            chunk_pdfs = split_by_outlines(str(pdf), str(split_dir), min_pages=min_pages)
            strategy = "outlines"
        elif split_method == "links":
            if not toc_pages:
                print("Erro: --toc-pages necessário para split=links", file=sys.stderr)
                sys.exit(1)
            chunk_pdfs = split_by_toc_links(str(pdf), str(split_dir), toc_pages)
            strategy = "toc_links"
        elif split_method == "pages":
            chunk_pdfs = split_by_pages(str(pdf), str(split_dir), chunk_size=chunk_size)
            strategy = "pages"
        else:
            print(f"Método de split desconhecido: {split_method}", file=sys.stderr)
            sys.exit(1)

        if not chunk_pdfs:
            print("⚠️  Split falhou, processando arquivo completo como fallback...")
            chunk_pdfs = [str(pdf)]
            strategy = "none_fallback"

    # -------------------------
    # 2. Processar cada chunk
    # -------------------------
    results: list[RunResult] = []
    markdowns: list[tuple[str, Path]] = []  # (título, path_md)
    total = len(chunk_pdfs)

    print(f"\n🔄 [{tool.upper()}] Processando {total} chunk(s)...\n")

    for i, chunk_pdf in enumerate(chunk_pdfs, start=1):
        chunk_path = Path(chunk_pdf)
        title = _chapter_title_from_path(chunk_path) if split_method != "none" else pdf.stem
        chunk_out = out / f"chunk_{i:03d}"

        print(f"  [{i}/{total}] {chunk_path.name}")
        result = _run_tool(tool, chunk_pdf, chunk_out)
        results.append(result)

        if result.status in ("success", "partial"):
            md = _find_markdown(chunk_out)
            if md:
                markdowns.append((title, md))
                print(f"    → {md.relative_to(out)}")
            else:
                print(f"    ⚠️  Markdown não encontrado em {chunk_out.relative_to(out)}")
        else:
            print(f"    ❌ {result.message}")

    # -------------------------
    # 3. Concatenar markdowns
    # -------------------------
    final_md: Path | None = None
    if markdowns:
        final_md = out / "document_final.md"
        sections: list[str] = [
            f"# {pdf.stem}\n",
            f"> Gerado por: **{tool}** | Split: **{strategy}** | Chunks: **{len(chunk_pdfs)}**\n",
        ]

        for title, md_path in markdowns:
            content = md_path.read_text(encoding="utf-8", errors="replace").strip()
            if split_method != "none":
                sections.append(f"\n---\n\n## {title}\n")
            sections.append(f"\n{content}\n")

        final_md.write_text("\n".join(sections), encoding="utf-8")
        size_kb = final_md.stat().st_size / 1024
        print(f"\n✅ document_final.md gerado: {size_kb:.1f} KB")

    # -------------------------
    # 4. Resumo
    # -------------------------
    elapsed = time.perf_counter() - t0
    ok = sum(1 for r in results if r.status == "success")
    fail = sum(1 for r in results if r.status == "failed")
    skip = sum(1 for r in results if r.status == "skipped")
    overall = combine_status(ok, fail, skip)

    print(f"\n{'='*50}")
    print(f"  Ferramenta : {tool}")
    print(f"  Split      : {strategy}")
    print(f"  Chunks     : {total} (✅ {ok}  ❌ {fail}  ⏭️ {skip})")
    print(f"  Status     : {overall}")
    print(f"  Tempo      : {elapsed:.1f}s")
    if final_md:
        print(f"  Saída      : {final_md}")
    print(f"{'='*50}\n")

    return results, final_md


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Processa um livro PDF completo com marker ou mineru.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", "-i", required=True, help="PDF de entrada")
    parser.add_argument("--output", "-o", required=True, help="Pasta de saída")
    parser.add_argument(
        "--tool", "-t",
        choices=["marker", "mineru"],
        required=True,
        help="Ferramenta de conversão",
    )
    parser.add_argument(
        "--split", "-s",
        choices=["auto", "outlines", "links", "pages", "none"],
        default="auto",
        help="Estratégia de split (padrão: auto)",
    )
    parser.add_argument(
        "--toc-pages",
        help="Páginas do sumário para split=links, ex: '15-22' (1-based, como no visualizador)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Páginas por bloco para split=pages (padrão: 100)",
    )
    parser.add_argument(
        "--min-pages",
        type=int,
        default=5,
        help="Capítulos menores serão agrupados (padrão: 5)",
    )
    args = parser.parse_args()

    toc_pages = None
    if args.toc_pages:
        toc_pages = []
        for part in args.toc_pages.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                toc_pages.extend(range(int(a) - 1, int(b)))
            else:
                toc_pages.append(int(part) - 1)
        toc_pages = sorted(set(toc_pages))

    run_book(
        input_pdf=args.input,
        output_dir=args.output,
        tool=args.tool,
        split_method=args.split,
        toc_pages=toc_pages,
        chunk_size=args.chunk_size,
        min_pages=args.min_pages,
    )


if __name__ == "__main__":
    main()
