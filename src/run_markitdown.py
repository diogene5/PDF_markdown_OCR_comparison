import os
from pathlib import Path

try:
    from markitdown import MarkItDown
except ImportError:
    print("⚠️ Biblioteca 'markitdown' não encontrada. Execute 'pip install markitdown'.")
    MarkItDown = None

def run_markitdown(input_pdf: str, output_dir: str):
    """
    Executa a biblioteca MarkItDown (da Microsoft) para converter de forma rápida (mas mais simples).
    
    Args:
        input_pdf (str): Caminho para o arquivo PDF de entrada.
        output_dir (str): Caminho para a pasta onde os resultados serão salvos.
    """
    if MarkItDown is None:
        return
        
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
            
    except Exception as e:
        print(f"❌ Erro ao rodar MarkItDown em '{pdf_path.name}':\n{e}")

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
