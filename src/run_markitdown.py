from pathlib import Path

from src.run_result import RunResult

try:
    from markitdown import MarkItDown
except ImportError:
    print("⚠️ Biblioteca 'markitdown' não encontrada. Execute 'pip install markitdown'.")
    MarkItDown = None

def run_markitdown(input_pdf: str, output_dir: str) -> RunResult:
    """
    Executa a biblioteca MarkItDown (da Microsoft) para converter de forma rápida (mas mais simples).
    
    Args:
        input_pdf (str): Caminho para o arquivo PDF de entrada.
        output_dir (str): Caminho para a pasta onde os resultados serão salvos.
    """
    if MarkItDown is None:
        message = "Biblioteca Python ausente: markitdown."
        print(f"⏭️ {message}")
        return RunResult("MarkItDown", "skipped", message)
        
    pdf_path = Path(input_pdf)
    print(f"🔄 Iniciando a extração do '{pdf_path.name}' usando MarkItDown...")
    
    try:
        # Inicializa a ferramenta leve
        md = MarkItDown()
        
        # Converte (MarkItDown é bem simples, se o PDF for escaneado sem texto embutido, pode não funcionar tão bem)
        result = md.convert(str(pdf_path))
        md_text = result.text_content
        
        # Salvando num arquivo md na pasta correspondente
        output_folder = Path(output_dir) / pdf_path.stem
        output_folder.mkdir(parents=True, exist_ok=True)
        
        output_file_path = output_folder / f"{pdf_path.stem}.md"
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(md_text)
            
        print(f"✅ Sucesso com MarkItDown! Salvo em: {output_file_path}")
        return RunResult("MarkItDown", "success", f"Markdown salvo para '{pdf_path.name}'.", str(output_file_path))
            
    except Exception as e:
        error_text = str(e)
        if "dependencies needed to read .pdf files have not been installed" in error_text:
            error_text = (
                "O pacote `markitdown` foi instalado sem suporte a PDF. "
                "Reinstale com `pip install 'markitdown[pdf]==0.1.5'`."
            )
        print(f"❌ Erro ao rodar MarkItDown em '{pdf_path.name}':\n{error_text}")
        return RunResult("MarkItDown", "failed", f"Falha ao converter '{pdf_path.name}': {error_text}")

if __name__ == "__main__":
    # Teste rápido se o script for rodado diretamente
    input_folder = Path("input")
    output_folder = Path("docs/results/markitdown")
    
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Pega o primeiro PDF que achar para testar
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_markitdown(str(pdfs[0]), str(output_folder))
    else:
        print("Nenhum PDF encontrado na pasta de input para testar.")
