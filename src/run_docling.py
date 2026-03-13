import os
from pathlib import Path

# Tentará importar a biblioteca (pode falhar se não instalada ou se houver erro ao importar localmente)
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    print("⚠️ Biblioteca 'docling' não encontrada. Verifique se ativou o venv e executou 'pip install docling'.")
    DocumentConverter = None

def run_docling(input_pdf: str, output_dir: str):
    """
    Executa o Docling nativamente via Python para converter um PDF em Markdown.
    
    Args:
        input_pdf (str): Caminho para o arquivo PDF de entrada.
        output_dir (str): Caminho para a pasta onde os resultados serão salvos.
    """
    if DocumentConverter is None:
        return
        
    pdf_path = Path(input_pdf)
    print(f"🔄 Iniciando a extração do '{pdf_path.name}' usando Docling...")
    
    try:
        # Inicializa o conversor (o Docling cuida do OCR, detecção de Layout, Tabelas etc)
        converter = DocumentConverter()
        
        # Converte o PDF e já obtém o texto gerado
        result = converter.convert(str(pdf_path))
        
        # Extrai como Markdown
        md_text = result.document.export_to_markdown()
        
        # O Docling não cria subpastas automaticamente como o Marker, então precisamos salvar o arquivo manual
        output_folder = Path(output_dir) / pdf_path.stem
        output_folder.mkdir(parents=True, exist_ok=True)
        
        output_file_path = output_folder / f"{pdf_path.stem}.md"
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(md_text)
            
        print(f"✅ Sucesso com Docling! Salvo em: {output_file_path}")
            
    except Exception as e:
        print(f"❌ Erro ao rodar Docling em '{pdf_path.name}':\n{e}")

if __name__ == "__main__":
    # Teste rápido se o script for rodado diretamente
    input_folder = Path("input")
    output_folder = Path("docs/results/docling")
    
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Pega o primeiro PDF que achar para testar
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_docling(str(pdfs[0]), str(output_folder))
    else:
        print("Nenhum PDF encontrado na pasta de input para testar.")
