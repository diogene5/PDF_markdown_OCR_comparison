import os
from pathlib import Path
import time

# Importa os módulos que criamos
from src.run_marker import run_marker
from src.run_mineru import run_mineru
from src.run_docling import run_docling
from src.run_markitdown import run_markitdown
from src.run_ocr_engines import run_ocr_engines
from src.run_cloud_apis import run_cloud_apis

def main():
    input_folder = Path("input")
    results_base = Path("docs/results")
    
    # Criar pastas base se não existirem
    input_folder.mkdir(exist_ok=True)
    results_base.mkdir(parents=True, exist_ok=True)

    pdfs = list(input_folder.glob("*.pdf"))
    
    if not pdfs:
        print("📁 A pasta 'input/' está vazia. Adicione PDFs lá para testar.")
        return
        
    print(f"🚀 Iniciando a Mega Comparação! Encontrados {len(pdfs)} arquivos PDF.")
    
    for pdf in pdfs:
        print(f"\n{'='*50}")
        print(f"📄 Processando: {pdf.name}")
        print(f"{'='*50}\n")
        
        pdf_str = str(pdf)
        
        # O objetivo é disparar todos (em um ambiente real fariamos paralelo/async)
        # 1. Estruturais Locais
        run_marker(pdf_str, str(results_base / "marker"))
        run_mineru(pdf_str, str(results_base / "mineru"))
        run_docling(pdf_str, str(results_base / "docling"))
        run_markitdown(pdf_str, str(results_base / "markitdown"))
        
        # 2. OCR Engines Lineares
        run_ocr_engines(pdf_str, str(results_base / "ocr_engines"))
        
        # 3. VLMs de Nuvem
        run_cloud_apis(pdf_str, str(results_base / "cloud_apis"))
        
        print(f"\n✅ Concluído processo para: {pdf.name}\n")
        
    print(f"🎉 Todos os {len(pdfs)} PDFs foram processados! Abra o 'docs/index.html' para comparar.")

if __name__ == "__main__":
    main()
