import os
import subprocess
from pathlib import Path

def run_mineru(input_pdf: str, output_dir: str):
    """
    Executa o MinerU localmente via linha de comando (`magic-pdf`) para converter um PDF em Markdown.
    Atenção: Requer a instalação prévia via `pip install mineru[all]`.
    
    Args:
        input_pdf (str): Caminho para o arquivo PDF de entrada.
        output_dir (str): Caminho para a pasta onde os resultados serão salvos.
    """
    pdf_path = Path(input_pdf)
    
    # Criaremos uma subpasta específica
    final_out_dir = Path(output_dir) / pdf_path.stem
    final_out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Iniciando a extração do '{pdf_path.name}' usando MinerU (magic-pdf)...")
    
    try:
        # Comando básico baseado na documentação atual do MinerU
        # magic-pdf -p base.pdf -o saida/
        command = [
            "magic-pdf",
            "-p", str(pdf_path),
            "-o", str(final_out_dir),
            "-m", "auto" # Modo auto detecta se tem texto ou se precisa full OCR
        ]
        
        # Executando o subprocesso (pode demorar caso inicialize modelos)
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Sucesso com MinerU para '{pdf_path.name}'!")
        else:
            print(f"❌ Erro ao rodar MinerU em '{pdf_path.name}':\n{result.stderr}")
            
    except Exception as e:
        print(f"⚠️ Exceção ao tentar rodar MinerU (magic-pdf): {e}")

if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/mineru")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_mineru(str(pdfs[0]), str(output_folder))
    else:
        print("Nenhum PDF encontrado na pasta de input para testar.")
