import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PYTHON_PACKAGES = {
    "docling": "docling",
    "easyocr": "easyocr",
    "google-generativeai": "google.generativeai",
    "markitdown": "markitdown",
    "mineru": "mineru",
    "openai": "openai",
    "pdf2image": "pdf2image",
    "pytesseract": "pytesseract",
}

CLI_TOOLS = (
    "marker_single",
    "mineru",
    "magic-pdf",
    "surya_ocr",
    "tesseract",
    "pdftoppm",
)

ENV_VARS = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
)


@dataclass(frozen=True)
class EnvironmentReport:
    project_root: Path
    interpreter: Path
    expected_venv_python: Path
    running_in_project_venv: bool
    python_packages: dict[str, bool]
    cli_tools: dict[str, str | None]
    env_vars: dict[str, bool]

    @property
    def missing_python_packages(self) -> list[str]:
        return [name for name, available in self.python_packages.items() if not available]

    @property
    def missing_cli_tools(self) -> list[str]:
        return [name for name, path in self.cli_tools.items() if path is None]


def build_environment_report(project_root: str | Path | None = None) -> EnvironmentReport:
    root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
    interpreter = Path(sys.executable)
    expected_venv_python = root / "venv" / "bin" / "python3"

    try:
        running_in_project_venv = interpreter.is_relative_to(root / "venv")
    except AttributeError:
        running_in_project_venv = str(interpreter).startswith(str(root / "venv"))

    python_packages = {
        package_name: importlib.util.find_spec(import_name) is not None
        for package_name, import_name in PYTHON_PACKAGES.items()
    }
    cli_tools = {tool: shutil.which(tool) for tool in CLI_TOOLS}
    env_vars = {name: bool(os.environ.get(name)) for name in ENV_VARS}

    return EnvironmentReport(
        project_root=root,
        interpreter=interpreter,
        expected_venv_python=expected_venv_python,
        running_in_project_venv=running_in_project_venv,
        python_packages=python_packages,
        cli_tools=cli_tools,
        env_vars=env_vars,
    )


def format_environment_report(report: EnvironmentReport) -> str:
    lines = [
        "🔎 Preflight do ambiente",
        f"  Python atual: {report.interpreter}",
        f"  Python esperado do projeto: {report.expected_venv_python}",
        f"  Dentro do venv do projeto: {'sim' if report.running_in_project_venv else 'não'}",
        "",
        "  Pacotes Python:",
    ]

    for package_name, available in report.python_packages.items():
        status = "OK" if available else "MISSING"
        lines.append(f"    - {package_name}: {status}")

    lines.append("")
    lines.append("  Ferramentas de linha de comando:")
    for tool_name, tool_path in report.cli_tools.items():
        status = tool_path or "MISSING"
        lines.append(f"    - {tool_name}: {status}")

    lines.append("")
    lines.append("  Variáveis de ambiente:")
    for env_name, available in report.env_vars.items():
        status = "OK" if available else "MISSING"
        lines.append(f"    - {env_name}: {status}")

    suggestions = build_environment_suggestions(report)
    if suggestions:
        lines.append("")
        lines.append("  Ações sugeridas:")
        for suggestion in suggestions:
            lines.append(f"    - {suggestion}")

    return "\n".join(lines)


def build_environment_suggestions(report: EnvironmentReport) -> list[str]:
    suggestions: list[str] = []

    if report.expected_venv_python.exists() and not report.running_in_project_venv:
        suggestions.append("Ative o ambiente com `source venv/bin/activate` ou rode `./run.sh`.")

    if report.missing_python_packages:
        packages = " ".join(report.missing_python_packages)
        suggestions.append(
            f"Instale os pacotes faltantes no interpretador atual com `python3 -m pip install {packages}` "
            "ou use o Python do `venv`."
        )

    if "magic-pdf" in report.missing_cli_tools and report.cli_tools.get("mineru"):
        suggestions.append("O CLI antigo `magic-pdf` não está disponível; use `mineru`.")

    if not report.env_vars.get("GEMINI_API_KEY"):
        suggestions.append("Se quiser habilitar Gemini, carregue `GEMINI_API_KEY` antes da execução.")

    return suggestions


if __name__ == "__main__":
    print(format_environment_report(build_environment_report()))
