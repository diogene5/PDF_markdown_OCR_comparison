import json
import re
from pathlib import Path


PAGE_FILE_RE = re.compile(r"page_(\d+)\.(md|txt)$")


def _page_sort_key(path: Path) -> tuple[int, str]:
    match = PAGE_FILE_RE.match(path.name)
    if not match:
        return (10**9, path.name)
    return (int(match.group(1)), path.name)


def combine_page_outputs(
    source_dir: Path,
    output_name: str = "document.md",
    title: str | None = None,
) -> Path | None:
    page_files = sorted(
        [
            path
            for path in source_dir.iterdir()
            if path.is_file() and PAGE_FILE_RE.match(path.name)
        ],
        key=_page_sort_key,
    )
    if not page_files:
        return None

    sections: list[str] = []
    if title:
        sections.append(f"# {title}")

    written_pages = 0
    for page_path in page_files:
        page_number = _page_sort_key(page_path)[0] + 1
        text = page_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        if title and written_pages == 0:
            sections.append("")
        elif written_pages > 0:
            sections.append("")
            sections.append("---")
            sections.append("")
        sections.append(f"## Página {page_number}")
        sections.append("")
        sections.append(text)
        written_pages += 1

    if not sections:
        return None

    output_path = source_dir / output_name
    output_path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return output_path


def combine_surya_results(results_json_path: Path, output_name: str = "document.md") -> Path | None:
    data = json.loads(results_json_path.read_text(encoding="utf-8"))
    pages = []
    if isinstance(data, dict):
        first_value = next(iter(data.values()), None)
        if isinstance(first_value, list):
            pages = first_value

    if not pages:
        return None

    sections: list[str] = ["# Surya OCR"]
    written_pages = 0
    for page_index, page in enumerate(pages, start=1):
        text_lines = page.get("text_lines", []) if isinstance(page, dict) else []
        lines = []
        for line in text_lines:
            if not isinstance(line, dict):
                continue
            text = (line.get("text") or "").strip()
            if text:
                lines.append(text)
        if not lines:
            continue
        if written_pages == 0:
            sections.append("")
        else:
            sections.append("")
            sections.append("---")
            sections.append("")
        sections.append(f"## Página {page_index}")
        sections.append("")
        sections.append("\n".join(lines))
        written_pages += 1

    if written_pages == 0:
        return None

    output_path = results_json_path.parent / output_name
    output_path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return output_path


def first_match(base_dir: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(base_dir.glob(pattern))
        if matches:
            return matches[0]
    return None
