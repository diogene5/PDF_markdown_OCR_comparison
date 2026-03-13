import shutil
import subprocess
from pathlib import Path

from src.output_helpers import combine_surya_results
from src.run_result import RunResult


def run_surya(input_pdf: str, output_dir: str) -> RunResult:
    """
    Executa o Surya OCR diretamente no PDF.

    O Surya fica num meio-termo entre OCR puro e OCR com alguma estrutura:
    ele tenta reconhecer o texto por pagina, mas nao e uma ferramenta de
    markdown estruturado como Marker ou MinerU.
    """
    pdf_path = Path(input_pdf)
    surya_command = shutil.which("surya_ocr")
    if surya_command is None:
        message = "CLI ausente: surya_ocr."
        print(f"⏭️ {message}")
        return RunResult("Surya", "skipped", message)

    final_out_dir = Path(output_dir) / pdf_path.stem
    final_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔄 Iniciando OCR do '{pdf_path.name}' usando Surya...")

    try:
        result = subprocess.run(
            [surya_command, str(pdf_path), "--output_dir", str(final_out_dir)],
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        print(f"⚠️ Excecao ao tentar rodar Surya: {exc}")
        return RunResult("Surya", "failed", f"Excecao ao executar surya_ocr: {exc}")

    if result.returncode != 0:
        stderr = result.stderr.strip() or "processo terminou sem stderr"
        print(f"❌ Erro ao rodar Surya em '{pdf_path.name}':\n{stderr}")
        return RunResult("Surya", "failed", f"CLI retornou codigo {result.returncode}: {stderr}")

    results_json = next(final_out_dir.rglob("results.json"), None)
    if results_json is None:
        print(f"⚠️ Surya concluiu para '{pdf_path.name}', mas nao gerou results.json.")
        return RunResult(
            "Surya",
            "partial",
            f"Concluiu para '{pdf_path.name}', mas sem results.json para consolidar.",
            str(final_out_dir),
        )

    combined = combine_surya_results(results_json)
    if combined is None:
        print(f"⚠️ Surya concluiu para '{pdf_path.name}', mas nao foi possivel consolidar.")
        return RunResult(
            "Surya",
            "partial",
            f"Concluiu para '{pdf_path.name}', mas sem document.md consolidado.",
            str(final_out_dir),
        )

    print(f"✅ Sucesso com Surya para '{pdf_path.name}'!")
    return RunResult(
        "Surya",
        "success",
        f"OCR concluido para '{pdf_path.name}' e consolidado em '{combined.name}'.",
        str(final_out_dir),
    )


if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/ocr_engines")
    output_folder.mkdir(parents=True, exist_ok=True)

    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_surya(str(pdfs[0]), str(output_folder / "surya_only"))
    else:
        print("Nenhum PDF encontrado na pasta de input para testar.")
