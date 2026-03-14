#!/usr/bin/env python3
"""
compare_book_strategies.py — Compara estratégias de split + ferramenta para livros PDF.

Roda cada combinação (split × ferramenta), mede métricas automáticas e gera
um relatório Markdown e um JSON com os dados brutos.

Estratégias disponíveis:
    direct-marker    — arquivo completo → marker
    direct-mineru    — arquivo completo → mineru
    outlines-marker  — split por bookmarks → marker em cada → concat
    outlines-mineru  — split por bookmarks → mineru em cada → concat
    pages-marker     — split em blocos → marker em cada → concat
    pages-mineru     — split em blocos → mineru em cada → concat
    links-marker     — split por links TOC → marker  (requer --toc-pages)
    links-mineru     — split por links TOC → mineru  (requer --toc-pages)

Uso:
    # Compara as 6 estratégias principais
    python scripts/compare_book_strategies.py --input livro.pdf --output comparison/

    # Apenas marker com dois splits
    python scripts/compare_book_strategies.py --input livro.pdf --output comparison/ \\
        --strategies direct-marker,outlines-marker,pages-marker

    # Com TOC links habilitado (adiciona 2 estratégias)
    python scripts/compare_book_strategies.py --input livro.pdf --output comparison/ \\
        --toc-pages 15-22
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_book import run_book
from src.run_result import combine_status


# ---------------------------------------------------------------------------
# Estratégias disponíveis
# ---------------------------------------------------------------------------

ALL_STRATEGIES = [
    "direct-marker",
    "direct-mineru",
    "outlines-marker",
    "outlines-mineru",
    "pages-marker",
    "pages-mineru",
]

LINK_STRATEGIES = [
    "links-marker",
    "links-mineru",
]

STRATEGY_PARAMS: dict[str, dict] = {
    "direct-marker":   {"tool": "marker",  "split_method": "none"},
    "direct-mineru":   {"tool": "mineru",  "split_method": "none"},
    "outlines-marker": {"tool": "marker",  "split_method": "outlines"},
    "outlines-mineru": {"tool": "mineru",  "split_method": "outlines"},
    "pages-marker":    {"tool": "marker",  "split_method": "pages"},
    "pages-mineru":    {"tool": "mineru",  "split_method": "pages"},
    "links-marker":    {"tool": "marker",  "split_method": "links"},
    "links-mineru":    {"tool": "mineru",  "split_method": "links"},
}


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def _measure_markdown(md_path: Path | None) -> dict:
    if md_path is None or not md_path.exists():
        return {"chars": 0, "words": 0, "headers": 0, "tables": 0, "images": 0}

    text = md_path.read_text(encoding="utf-8", errors="replace")
    return {
        "chars":   len(text),
        "words":   len(text.split()),
        "headers": len(re.findall(r"^#{1,3} ", text, re.M)),
        "tables":  len(re.findall(r"\|---", text)),
        "images":  len(re.findall(r"!\[", text)),
    }


# ---------------------------------------------------------------------------
# Runner de uma estratégia
# ---------------------------------------------------------------------------

def run_strategy(
    strategy_id: str,
    input_pdf: str,
    base_output: Path,
    toc_pages: list[int] | None,
    chunk_size: int,
    min_pages: int,
) -> dict:
    """Executa uma estratégia e retorna dicionário com métricas."""
    params = STRATEGY_PARAMS[strategy_id]
    out_dir = base_output / strategy_id

    print(f"\n{'='*60}")
    print(f"  Estratégia: {strategy_id}")
    print(f"{'='*60}")

    t0 = time.perf_counter()
    try:
        results, final_md = run_book(
            input_pdf=input_pdf,
            output_dir=str(out_dir),
            tool=params["tool"],
            split_method=params["split_method"],
            toc_pages=toc_pages if params["split_method"] == "links" else None,
            chunk_size=chunk_size,
            min_pages=min_pages,
        )
        elapsed = time.perf_counter() - t0

        ok    = sum(1 for r in results if r.status == "success")
        fail  = sum(1 for r in results if r.status == "failed")
        skip  = sum(1 for r in results if r.status == "skipped")
        overall = combine_status(ok, fail, skip)

        metrics = _measure_markdown(final_md)
        return {
            "strategy":    strategy_id,
            "tool":        params["tool"],
            "split":       params["split_method"],
            "status":      overall,
            "time_s":      round(elapsed, 1),
            "chunks_ok":   ok,
            "chunks_fail": fail,
            "chunks_skip": skip,
            "output_path": str(final_md) if final_md else None,
            **metrics,
        }

    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"  ❌ Exceção: {e}")
        return {
            "strategy":    strategy_id,
            "tool":        params["tool"],
            "split":       params["split_method"],
            "status":      "failed",
            "time_s":      round(elapsed, 1),
            "chunks_ok":   0,
            "chunks_fail": 1,
            "chunks_skip": 0,
            "output_path": None,
            "chars": 0, "words": 0, "headers": 0, "tables": 0, "images": 0,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

_STATUS_EMOJI = {"success": "✅", "partial": "⚠️", "failed": "❌", "skipped": "⏭️"}

def _fmt(value, fmt=None) -> str:
    if value is None:
        return "—"
    if fmt:
        return format(value, fmt)
    return str(value)


def generate_report(rows: list[dict], pdf_name: str) -> str:
    lines = [
        f"# Comparação de Estratégias — {pdf_name}",
        "",
        "Métricas coletadas automaticamente. "
        "Qualidade real deve ser avaliada lendo `document_final.md` de cada estratégia.",
        "",
        "## Tabela de Resultados",
        "",
        "| Estratégia | Status | Tempo (s) | Chars | Palavras | Cabeçalhos | Tabelas | Imagens | Chunks OK/Fail |",
        "|------------|--------|----------:|------:|---------:|-----------:|--------:|--------:|---------------|",
    ]

    for r in rows:
        emoji = _STATUS_EMOJI.get(r["status"], "•")
        chunks = f"{r['chunks_ok']}/{r['chunks_fail']}"
        lines.append(
            f"| `{r['strategy']}` "
            f"| {emoji} {r['status']} "
            f"| {_fmt(r['time_s'])} "
            f"| {_fmt(r.get('chars', 0), ',')} "
            f"| {_fmt(r.get('words', 0), ',')} "
            f"| {_fmt(r.get('headers', 0))} "
            f"| {_fmt(r.get('tables', 0))} "
            f"| {_fmt(r.get('images', 0))} "
            f"| {chunks} |"
        )

    # Ranking por conteúdo gerado (chars)
    successful = [r for r in rows if r["status"] in ("success", "partial") and r.get("chars", 0) > 0]

    lines += ["", "## Ranking por Conteúdo Gerado", ""]
    if successful:
        ranked = sorted(successful, key=lambda r: r.get("chars", 0), reverse=True)
        for i, r in enumerate(ranked, 1):
            lines.append(f"{i}. `{r['strategy']}` — {r.get('chars', 0):,} chars, {r.get('words', 0):,} palavras")
    else:
        lines.append("Nenhuma estratégia produziu output com sucesso.")

    # Ranking por velocidade
    lines += ["", "## Ranking por Velocidade", ""]
    if successful:
        fastest = sorted(successful, key=lambda r: r["time_s"])
        for i, r in enumerate(fastest, 1):
            lines.append(f"{i}. `{r['strategy']}` — {r['time_s']}s")

    # Outputs
    lines += ["", "## Arquivos Gerados", ""]
    for r in rows:
        if r.get("output_path"):
            lines.append(f"- `{r['strategy']}`: `{r['output_path']}`")

    lines += [
        "",
        "---",
        "_Gerado por `scripts/compare_book_strategies.py`_",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
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


def main():
    parser = argparse.ArgumentParser(
        description="Compara estratégias de split + ferramenta para conversão de livros PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", "-i", required=True, help="PDF de entrada")
    parser.add_argument("--output", "-o", required=True, help="Pasta base de saída")
    parser.add_argument(
        "--strategies",
        help="Lista de estratégias separada por vírgula (padrão: todas as 6 principais). "
             "Ex: 'direct-marker,outlines-marker,pages-marker'",
    )
    parser.add_argument(
        "--toc-pages",
        help="Páginas do sumário para estratégias 'links-*', ex: '15-22' (1-based). "
             "Quando informado, adiciona links-marker e links-mineru automaticamente.",
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
        help="Mínimo de páginas por capítulo para split=outlines (padrão: 5)",
    )
    args = parser.parse_args()

    pdf = Path(args.input).expanduser().resolve()
    if not pdf.exists():
        print(f"Erro: arquivo não encontrado: {pdf}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Seleciona estratégias
    if args.strategies:
        strategies = [s.strip() for s in args.strategies.split(",")]
    else:
        strategies = list(ALL_STRATEGIES)

    toc_pages = None
    if args.toc_pages:
        toc_pages = _parse_toc_pages(args.toc_pages)
        # Adiciona links-* se não estiverem já na lista
        for s in LINK_STRATEGIES:
            if s not in strategies:
                strategies.append(s)
        print(f"  Páginas de sumário (0-based): {toc_pages}")

    # Valida estratégias
    unknown = [s for s in strategies if s not in STRATEGY_PARAMS]
    if unknown:
        print(f"Estratégias desconhecidas: {unknown}", file=sys.stderr)
        print(f"Disponíveis: {list(STRATEGY_PARAMS.keys())}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Comparação de Estratégias")
    print(f"  PDF: {pdf.name}")
    print(f"  Estratégias: {', '.join(strategies)}")
    print(f"{'='*60}")

    # Roda cada estratégia
    rows: list[dict] = []
    total_t0 = time.perf_counter()

    for strategy_id in strategies:
        row = run_strategy(
            strategy_id=strategy_id,
            input_pdf=str(pdf),
            base_output=out,
            toc_pages=toc_pages,
            chunk_size=args.chunk_size,
            min_pages=args.min_pages,
        )
        rows.append(row)

    total_elapsed = time.perf_counter() - total_t0

    # Salva JSON
    data_file = out / "comparison_data.json"
    data_file.write_text(
        json.dumps({"pdf": pdf.name, "strategies": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Gera relatório Markdown
    report = generate_report(rows, pdf.name)
    report_file = out / "comparison_report.md"
    report_file.write_text(report, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  Comparação concluída em {total_elapsed:.1f}s")
    print(f"  Relatório : {report_file}")
    print(f"  Dados JSON: {data_file}")
    print(f"{'='*60}\n")

    # Imprime tabela resumida
    print(report)


if __name__ == "__main__":
    main()
