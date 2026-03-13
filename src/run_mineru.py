import subprocess
import shutil
from pathlib import Path

from src.run_result import RunResult

def run_mineru(input_pdf: str, output_dir: str) -> RunResult:
    """
    Executa o MinerU localmente via linha de comando para converter um PDF em Markdown.
    Atenção: Requer a instalação prévia do CLI `mineru` (ou o legado `magic-pdf`).
    
    Args:
        input_pdf (str): Caminho para o arquivo PDF de entrada.
        output_dir (str): Caminho para a pasta onde os resultados serão salvos.
    """
    pdf_path = Path(input_pdf)
    mineru_command = shutil.which("mineru") or shutil.which("magic-pdf")
    if mineru_command is None:
        message = "CLI ausente: mineru (ou legado magic-pdf)."
        print(f"⏭️ {message}")
        return RunResult("MinerU", "skipped", message)
    
    # Criaremos uma subpasta específica
    final_out_dir = Path(output_dir) / pdf_path.stem
    final_out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Iniciando a extração do '{pdf_path.name}' usando MinerU...")
    
    try:
        # Compatível com o CLI atual (`mineru`) e com o legado (`magic-pdf`).
        command = [
            mineru_command,
            "-p", str(pdf_path),
            "-o", str(final_out_dir),
            "-m", "auto" # Modo auto detecta se tem texto ou se precisa full OCR
        ]
        
        # Executando o subprocesso (pode demorar caso inicialize modelos)
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Sucesso com MinerU para '{pdf_path.name}'!")
            return RunResult("MinerU", "success", f"Conversão concluída para '{pdf_path.name}'.", str(final_out_dir))
        else:
            print(f"❌ Erro ao rodar MinerU em '{pdf_path.name}':\n{result.stderr}")
            stderr = result.stderr.strip() or "processo terminou sem stderr"
            return RunResult("MinerU", "failed", f"CLI retornou código {result.returncode}: {stderr}")
            
    except Exception as e:
        print(f"⚠️ Exceção ao tentar rodar MinerU: {e}")
        return RunResult("MinerU", "failed", f"Exceção ao executar '{Path(mineru_command).name}': {e}")

if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/mineru")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_mineru(str(pdfs[0]), str(output_folder))
    else:
        print("Nenhum PDF encontrado na pasta de input para testar.")
