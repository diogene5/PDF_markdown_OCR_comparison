import json
from datetime import datetime, timezone
from pathlib import Path

from src.output_helpers import first_match


TOOLS = [
    {"id": "marker", "label": "Marker", "family": "Estrutural"},
    {"id": "mineru", "label": "MinerU", "family": "Estrutural"},
    {"id": "docling", "label": "Docling", "family": "Estrutural"},
    {"id": "markitdown", "label": "MarkItDown", "family": "Estrutural"},
    {"id": "cloud_apis/openai", "label": "OpenAI", "family": "Nuvem"},
    {"id": "cloud_apis/gemini", "label": "Gemini", "family": "Nuvem"},
    {"id": "ocr_engines/surya", "label": "Surya", "family": "OCR"},
    {"id": "ocr_engines/tesseract", "label": "Tesseract", "family": "OCR"},
    {"id": "ocr_engines/easyocr", "label": "EasyOCR", "family": "OCR"},
]


def _relative(path: Path, docs_dir: Path) -> str:
    return path.relative_to(docs_dir).as_posix()


def _artifact(base_dir: Path, docs_dir: Path, patterns: list[str], page_pattern: str | None = None) -> dict:
    file_path = first_match(base_dir, patterns)
    page_files = sorted(base_dir.glob(page_pattern)) if page_pattern else []

    artifact = {
        "available": file_path is not None,
        "path": _relative(file_path, docs_dir) if file_path else None,
        "page_count": len(page_files),
    }
    if file_path:
        artifact["format"] = file_path.suffix.lstrip(".") or "txt"
        artifact["name"] = file_path.name
    return artifact


def build_results_manifest(results_base: Path) -> dict:
    docs_dir = results_base.parent
    pdf_names = set()

    for family_dir in results_base.iterdir():
        if not family_dir.is_dir():
            continue
        for pdf_dir in family_dir.iterdir():
            if pdf_dir.is_dir():
                pdf_names.add(pdf_dir.name)

    pdfs: list[dict] = []
    for pdf_name in sorted(pdf_names):
        outputs = {
            "marker": _artifact(
                results_base / "marker" / pdf_name,
                docs_dir,
                [f"{pdf_name}.md"],
            ),
            "mineru": _artifact(
                results_base / "mineru" / pdf_name,
                docs_dir,
                [
                    f"{pdf_name}/hybrid_auto/{pdf_name}.md",
                    f"{pdf_name}/auto/{pdf_name}.md",
                    f"**/{pdf_name}.md",
                ],
            ),
            "docling": _artifact(
                results_base / "docling" / pdf_name,
                docs_dir,
                [f"{pdf_name}.md"],
            ),
            "markitdown": _artifact(
                results_base / "markitdown" / pdf_name,
                docs_dir,
                [f"{pdf_name}.md"],
            ),
            "cloud_apis/openai": _artifact(
                results_base / "cloud_apis" / pdf_name / "openai",
                docs_dir,
                ["document.md", "page_0.md"],
                "page_*.md",
            ),
            "cloud_apis/gemini": _artifact(
                results_base / "cloud_apis" / pdf_name / "gemini",
                docs_dir,
                ["document.md", "page_0.md"],
                "page_*.md",
            ),
            "ocr_engines/surya": _artifact(
                results_base / "ocr_engines" / pdf_name / "surya",
                docs_dir,
                ["document.md", "**/results.json"],
            ),
            "ocr_engines/tesseract": _artifact(
                results_base / "ocr_engines" / pdf_name / "tesseract",
                docs_dir,
                ["document.md", "page_0.txt"],
                "page_*.txt",
            ),
            "ocr_engines/easyocr": _artifact(
                results_base / "ocr_engines" / pdf_name / "easyocr",
                docs_dir,
                ["document.md", "page_0.txt"],
                "page_*.txt",
            ),
        }
        available_count = sum(1 for artifact in outputs.values() if artifact["available"])
        pdfs.append(
            {
                "name": pdf_name,
                "available_tools": available_count,
                "outputs": outputs,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tools": TOOLS,
        "pdfs": pdfs,
    }


def write_results_manifest(results_base: Path, output_path: Path | None = None) -> Path:
    manifest = build_results_manifest(results_base)
    target = output_path or (results_base / "manifest.json")
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
