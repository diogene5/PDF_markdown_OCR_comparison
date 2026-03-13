from pathlib import Path

from src.environment_diagnostics import build_environment_report, format_environment_report
from src.results_manifest import write_results_manifest
from src.run_result import RunResult
from src.run_marker import run_marker
from src.run_mineru import run_mineru
from src.run_docling import run_docling
from src.run_markitdown import run_markitdown
from src.run_ocr_engines import run_ocr_engines
from src.run_cloud_apis import run_cloud_apis


def print_pdf_summary(pdf_name: str, results: list[RunResult]) -> None:
    print(f"\n📊 Resumo para '{pdf_name}':")
    for result in results:
        print(f"  {result.summary_line()}")


def print_final_summary(pdf_results: dict[str, list[RunResult]]) -> None:
    totals = {"success": 0, "partial": 0, "skipped": 0, "failed": 0}

    for results in pdf_results.values():
        for result in results:
            totals[result.status] = totals.get(result.status, 0) + 1

    print("\n🧾 Resumo consolidado:")
    print(f"  ✅ Sucessos: {totals['success']}")
    print(f"  ⚠️ Parciais: {totals['partial']}")
    print(f"  ⏭️ Pulados: {totals['skipped']}")
    print(f"  ❌ Falhas: {totals['failed']}")

def main():
    input_folder = Path("input")
    results_base = Path("docs/results")
    
    # Criar pastas base se não existirem
    input_folder.mkdir(exist_ok=True)
    results_base.mkdir(parents=True, exist_ok=True)
    write_results_manifest(results_base)

    pdfs = list(input_folder.glob("*.pdf"))
    
    if not pdfs:
        print("📁 A pasta 'input/' está vazia. Adicione PDFs lá para testar.")
        return

    env_report = build_environment_report(Path(__file__).resolve().parent)
    print(format_environment_report(env_report))
    print("")
        
    print(f"🚀 Iniciando a Mega Comparação! Encontrados {len(pdfs)} arquivos PDF.")
    all_results: dict[str, list[RunResult]] = {}
    
    for pdf in pdfs:
        print(f"\n{'='*50}")
        print(f"📄 Processando: {pdf.name}")
        print(f"{'='*50}\n")
        
        pdf_str = str(pdf)
        results: list[RunResult] = []
        
        # O objetivo é disparar todos (em um ambiente real fariamos paralelo/async)
        # 1. Estruturais Locais
        results.append(run_marker(pdf_str, str(results_base / "marker")))
        results.append(run_mineru(pdf_str, str(results_base / "mineru")))
        results.append(run_docling(pdf_str, str(results_base / "docling")))
        results.append(run_markitdown(pdf_str, str(results_base / "markitdown")))
        
        # 2. OCR Engines Lineares
        results.append(run_ocr_engines(pdf_str, str(results_base / "ocr_engines")))
        
        # 3. VLMs de Nuvem
        results.append(run_cloud_apis(pdf_str, str(results_base / "cloud_apis")))

        all_results[pdf.name] = results
        write_results_manifest(results_base)
        print_pdf_summary(pdf.name, results)
        
        print(f"\n✅ Concluído processo para: {pdf.name}\n")
        
    print_final_summary(all_results)
    manifest_path = write_results_manifest(results_base)
    print(f"\n🎉 Todos os {len(pdfs)} PDFs foram processados!")
    print(f"📄 Manifesto atualizado em: {manifest_path}")
    print("🌐 Para comparar visualmente, sirva a pasta docs/ com: python3 -m http.server 8000 -d docs")

if __name__ == "__main__":
    main()
