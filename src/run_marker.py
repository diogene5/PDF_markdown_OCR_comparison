import os
import subprocess
from pathlib import Path

def run_marker(input_pdf: str, output_dir: str):
    """
    Executa o Marker localmente via linha de comando para converter um PDF em Markdown.
    
    Args:
        input_pdf (str): Caminho para o arquivo PDF de entrada.
        output_dir (str): Caminho para a pasta onde os resultados serão salvos.
    """
    pdf_path = Path(input_pdf)
    
    # Marker cria uma subpasta com o mesmo nome do PDF dentro do output_dir
    print(f"🔄 Iniciando a extração do '{pdf_path.name}' usando Marker...")
    
    try:
        # Comando: marker_single arquivo.pdf --output_dir ./saida
        # O Marker é muito bom para tabelas e estrutura visual
        command = [
            "marker_single",
            str(pdf_path),
            "--output_dir",
            str(output_dir)
        ]
        
        # Executando o subprocesso
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Sucesso com Marker para '{pdf_path.name}'!")
        else:
            print(f"❌ Erro ao rodar Marker em '{pdf_path.name}':\n{result.stderr}")
            
    except Exception as e:
        print(f"⚠️ Exceção ao tentar rodar Marker: {e}")

if __name__ == "__main__":
    # Teste rápido se o script for rodado diretamente
    input_folder = Path("input")
    output_folder = Path("docs/results/marker")
    
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Pega o primeiro PDF que achar para testar
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_marker(str(pdfs[0]), str(output_folder))
    else:
        print("Nenhum PDF encontrado na pasta de input para testar.")
