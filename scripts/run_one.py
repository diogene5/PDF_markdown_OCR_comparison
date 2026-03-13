#!/usr/bin/env python3
import argparse
import importlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RUNNERS = {
    "marker": ("src.run_marker", "run_marker"),
    "mineru": ("src.run_mineru", "run_mineru"),
    "docling": ("src.run_docling", "run_docling"),
    "markitdown": ("src.run_markitdown", "run_markitdown"),
    "ocr": ("src.run_ocr_engines", "run_ocr_engines"),
    "cloud": ("src.run_cloud_apis", "run_cloud_apis"),
}


def expand_tools(requested: list[str]) -> list[str]:
    expanded: list[str] = []
    for tool in requested:
        if tool == "all-local":
            expanded.extend(["marker", "mineru", "docling", "markitdown", "ocr"])
        elif tool == "all":
            expanded.extend(["marker", "mineru", "docling", "markitdown", "ocr", "cloud"])
        else:
            expanded.append(tool)
    seen: list[str] = []
    for tool in expanded:
        if tool not in seen:
            seen.append(tool)
    return seen


def get_runner(tool: str):
    module_name, function_name = RUNNERS[tool]
    module = importlib.import_module(module_name)
    return getattr(module, function_name)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Roda uma ou mais ferramentas do projeto em um PDF qualquer."
    )
    parser.add_argument("--input", required=True, help="Caminho do PDF que sera testado.")
    parser.add_argument(
        "--output",
        required=True,
        help="Pasta base onde os resultados serao salvos.",
    )
    parser.add_argument(
        "--tool",
        action="append",
        required=True,
        choices=["marker", "mineru", "docling", "markitdown", "ocr", "cloud", "all-local", "all"],
        help="Ferramenta a rodar. Pode repetir --tool varias vezes.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.input).expanduser().resolve()
    output_base = Path(args.output).expanduser().resolve()

    if not pdf_path.exists():
        print(f"PDF nao encontrado: {pdf_path}")
        return 2

    output_base.mkdir(parents=True, exist_ok=True)
    tools = expand_tools(args.tool)
    exit_code = 0

    for tool in tools:
        runner = get_runner(tool)
        tool_output_dir = output_base / tool
        tool_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {tool.upper()} ===")
        result = runner(str(pdf_path), str(tool_output_dir))
        print(result.summary_line())
        if result.status in {"failed", "partial"}:
            exit_code = 1

    print(f"\nResultados em: {output_base}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
