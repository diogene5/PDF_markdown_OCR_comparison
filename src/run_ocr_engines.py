import os
import subprocess
from pathlib import Path
from pdf2image import convert_from_path

try:
    import pytesseract
except ImportError:
    print("⚠️ pytesseract não instalado.")
    pytesseract = None

try:
    import easyocr
    reader = easyocr.Reader(['en', 'pt']) # Carrega os idiomas
except Exception as e:
    print(f"⚠️ Erro ao carregar easyocr: {e}")
    reader = None

def run_tesseract(image, output_path: Path):
    if pytesseract is None:
        return
    text = pytesseract.image_to_string(image, lang='por')
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

def run_easyocr(image_path: str, output_path: Path):
    if reader is None:
        return
    result = reader.readtext(image_path, detail=0) # retorna apenas o texto
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(result))

def run_ocr_engines(input_pdf: str, output_dir: str):
    """
    Roda Tesseract, EasyOCR e Surya (via CLI) em cada página do PDF convertido em imagem.
    Esses motores focam no texto puro, sem manter tabelas estruturadas (exceto o Surya que tem suporte nativo para PDF).
    """
    pdf_path = Path(input_pdf)
    results_dir = Path(output_dir) / pdf_path.stem
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Extração Pure OCR: Convertendo PDF '{pdf_path.name}' para imagens...")
    
    try:
        # 1. Surya OCR - melhor lidar direto com o PDF via tool dele mesmo
        print(f"  -> Rodando Surya CLI...")
        # Usa o comando CLI básico de OCR do Surya (supondo surya_ocr instalado)
        surya_out = results_dir / "surya"
        surya_out.mkdir(exist_ok=True)
        subprocess.run(["surya_ocr", str(pdf_path), "--results_dir", str(surya_out), "--langs", "pt"], capture_output=True)
        
        # 2. Converte PDF para Imagens (para o Tesseract e EasyOCR)
        # Requer poppler instalado no mac (brew install poppler)
        images = convert_from_path(str(pdf_path))
        
        tess_dir = results_dir / "tesseract"
        tess_dir.mkdir(exist_ok=True)
        easy_dir = results_dir / "easyocr"
        easy_dir.mkdir(exist_ok=True)
        
        for i, img in enumerate(images):
            temp_img_path = results_dir / f"temp_page_{i}.png"
            img.save(temp_img_path, "PNG")
            
            # Tesseract
            run_tesseract(img, tess_dir / f"page_{i}.txt")
            
            # EasyOCR
            run_easyocr(str(temp_img_path), easy_dir / f"page_{i}.txt")
            
            os.remove(temp_img_path) # Limpa img temp
            
        print(f"✅ OCR Engines Concluído para '{pdf_path.name}'.")
        
    except Exception as e:
        print(f"❌ Erro em Pure OCR Engines para '{pdf_path.name}':\n{e}")

if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/ocr_engines")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_ocr_engines(str(pdfs[0]), str(output_folder))
