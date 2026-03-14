#!/usr/bin/env python3
"""
split_chapters.py — Divide um PDF de livro em capítulos/chunks.

Uso:
    python scripts/split_chapters.py --input livro.pdf --output capitulos/
    python scripts/split_chapters.py --input livro.pdf --output caps/ --method links --toc-pages 14-21
    python scripts/split_chapters.py --input livro.pdf --output caps/ --method pages --chunk-size 80

Métodos:
    auto     — detecta automaticamente (padrão)
    outlines — usa bookmarks/outline do PDF
    links    — usa links clicáveis do sumário (--toc-pages obrigatório)
    pages    — divide em blocos fixos de páginas
"""

import argparse
import sys
from pathlib import Path

# Garante que src/ seja importável quando rodado da raiz do projeto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.book_splitter import (
    smart_split,
    split_by_outlines,
    split_by_toc_links,
    split_by_pages,
)


def parse_toc_pages(spec: str) -> list[int]:
    """
    Converte '14-21' → [14, 15, ..., 21]  (0-based)
    ou '15,16,17' → [15, 16, 17]
    Aceita input 1-based do visualizador: subtrai 1 internamente.
    """
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a) - 1, int(b)))  # converte para 0-based
        else:
            pages.append(int(part) - 1)
    return sorted(set(pages))


def main():
    parser = argparse.ArgumentParser(
        description="Divide um PDF em capítulos para processamento com marker/mineru.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", "-i", required=True, help="Caminho do PDF de entrada")
    parser.add_argument("--output", "-o", required=True, help="Pasta de saída para os capítulos")
    parser.add_argument(
        "--method", "-m",
        choices=["auto", "outlines", "links", "pages"],
        default="auto",
        help="Estratégia de divisão (padrão: auto)",
    )
    parser.add_argument(
        "--toc-pages",
        help="Páginas do sumário para método 'links', ex: '15-22' ou '15,16,17' (numeração do visualizador, 1-based)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Páginas por bloco para método 'pages' (padrão: 100)",
    )
    parser.add_argument(
        "--min-pages",
        type=int,
        default=5,
        help="Capítulos menores que isso são agrupados no anterior (padrão: 5)",
    )
    args = parser.parse_args()

    pdf = Path(args.input).expanduser().resolve()
    if not pdf.exists():
        print(f"Erro: arquivo não encontrado: {pdf}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output).expanduser().resolve()

    toc_pages: list[int] | None = None
    if args.toc_pages:
        toc_pages = parse_toc_pages(args.toc_pages)
        print(f"  Páginas de sumário (0-based): {toc_pages}")

    print(f"\n{'='*60}")
    print(f"  PDF:    {pdf.name}")
    print(f"  Saída:  {out}")
    print(f"  Método: {args.method}")
    print(f"{'='*60}")

    if args.method == "auto":
        strategy, paths = smart_split(
            str(pdf),
            str(out),
            toc_pages=toc_pages,
            chunk_size=args.chunk_size,
            min_pages=args.min_pages,
        )
        print(f"\n✅ Estratégia usada: {strategy}")
    elif args.method == "outlines":
        paths = split_by_outlines(str(pdf), str(out), min_pages=args.min_pages)
    elif args.method == "links":
        if not toc_pages:
            print("Erro: --toc-pages é obrigatório para método 'links'", file=sys.stderr)
            sys.exit(1)
        paths = split_by_toc_links(str(pdf), str(out), toc_pages)
    else:  # pages
        paths = split_by_pages(str(pdf), str(out), chunk_size=args.chunk_size)

    print(f"\n✅ {len(paths)} arquivo(s) gerado(s) em: {out}")


if __name__ == "__main__":
    main()
