import os
import shutil
from pathlib import Path

try:
    from pdf2image import convert_from_path, pdfinfo_from_path
except ImportError:
    print("⚠️ Biblioteca 'pdf2image' não encontrada. Execute 'pip install pdf2image'.")
    convert_from_path = None
    pdfinfo_from_path = None

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

from src.run_result import RunResult, combine_status
from src.output_helpers import combine_page_outputs
from src.run_surya import run_surya


def iter_pdf_pages(pdf_path: Path):
    if convert_from_path is None or pdfinfo_from_path is None:
        raise RuntimeError("pdf2image indisponível")

    page_count = int(pdfinfo_from_path(str(pdf_path))["Pages"])
    for page_number in range(1, page_count + 1):
        images = convert_from_path(
            str(pdf_path),
            first_page=page_number,
            last_page=page_number,
            thread_count=1,
        )
        if not images:
            raise RuntimeError(f"Nenhuma imagem foi gerada para a página {page_number}.")

        image = images[0]
        try:
            yield page_number - 1, page_count, image
        finally:
            image.close()
            for extra_image in images[1:]:
                extra_image.close()


def run_tesseract(image, output_path: Path) -> tuple[bool, str | None]:
    if pytesseract is None:
        return False, "pytesseract ausente"
    try:
        text = pytesseract.image_to_string(image, lang='por')
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        return True, None
    except Exception as e:
        return False, str(e)

def run_easyocr(image_path: str, output_path: Path) -> tuple[bool, str | None]:
    if reader is None:
        return False, "easyocr ausente"
    try:
        result = reader.readtext(image_path, detail=0) # retorna apenas o texto
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(result))
        return True, None
    except Exception as e:
        return False, str(e)

def run_ocr_engines(input_pdf: str, output_dir: str) -> RunResult:
    """
    Roda Tesseract, EasyOCR e Surya (via CLI) em cada página do PDF convertido em imagem.
    Esses motores focam no texto puro, sem manter tabelas estruturadas (exceto o Surya que tem suporte nativo para PDF).
    """
    pdf_path = Path(input_pdf)
    results_dir = Path(output_dir) / pdf_path.stem
    results_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    failure_count = 0
    skipped_count = 0
    messages: list[str] = []
    print(f"🔄 Extração Pure OCR: Convertendo PDF '{pdf_path.name}' para imagens...")

    # 1. Surya OCR - roda direto no PDF se o CLI estiver disponível.
    surya_result = run_surya(str(pdf_path), str(results_dir / "surya"))
    messages.append(surya_result.message)
    if surya_result.status == "success":
        success_count += 1
    elif surya_result.status == "skipped":
        skipped_count += 1
    else:
        failure_count += 1

    # 2. Converte PDF para imagens para Tesseract e EasyOCR.
    if convert_from_path is None or pdfinfo_from_path is None:
        skipped_count += 1
        skipped_count += 1
        messages.append("Tesseract e EasyOCR pulados: falta a dependência Python 'pdf2image'.")
    else:
        try:
            page_count = int(pdfinfo_from_path(str(pdf_path))["Pages"])
        except Exception as e:
            failure_count += 1
            failure_count += 1
            messages.append(f"Conversão do PDF para imagem falhou: {e}")
            page_count = 0

        if page_count:
            tess_dir = results_dir / "tesseract"
            easy_dir = results_dir / "easyocr"
            tess_dir.mkdir(exist_ok=True)
            easy_dir.mkdir(exist_ok=True)

            tesseract_failures = 0
            easyocr_failures = 0
            page_iteration_failed = False

            try:
                for i, total_pages, img in iter_pdf_pages(pdf_path):
                    print(f"  -> Página {i + 1}/{total_pages}")
                    temp_img_path = results_dir / f"temp_page_{i}.png"
                    try:
                        img.save(temp_img_path, "PNG")

                        if pytesseract is not None:
                            ok, error = run_tesseract(img, tess_dir / f"page_{i}.txt")
                            if not ok:
                                tesseract_failures += 1
                                print(f"⚠️ Tesseract falhou na página {i} de '{pdf_path.name}': {error}")

                        if reader is not None:
                            ok, error = run_easyocr(str(temp_img_path), easy_dir / f"page_{i}.txt")
                            if not ok:
                                easyocr_failures += 1
                                print(f"⚠️ EasyOCR falhou na página {i} de '{pdf_path.name}': {error}")
                    finally:
                        if temp_img_path.exists():
                            os.remove(temp_img_path)
            except Exception as e:
                page_iteration_failed = True
                failure_count += 1
                failure_count += 1
                messages.append(f"Conversão página-a-página falhou: {e}")

            if pytesseract is None:
                skipped_count += 1
                messages.append("Tesseract pulado: pacote `pytesseract` indisponível.")
            elif tesseract_failures or page_iteration_failed:
                failure_count += 1
                messages.append(f"Tesseract falhou em {tesseract_failures} página(s).")
            else:
                success_count += 1
                messages.append(f"Tesseract concluído em {page_count} página(s).")
            combined = combine_page_outputs(tess_dir, title=f"{pdf_path.stem} · Tesseract")
            if combined is not None:
                messages.append(f"Tesseract consolidado em {combined.name}.")

            if reader is None:
                skipped_count += 1
                messages.append("EasyOCR pulado: pacote/modelo indisponível.")
            elif easyocr_failures or page_iteration_failed:
                failure_count += 1
                messages.append(f"EasyOCR falhou em {easyocr_failures} página(s).")
            else:
                success_count += 1
                messages.append(f"EasyOCR concluído em {page_count} página(s).")
            combined = combine_page_outputs(easy_dir, title=f"{pdf_path.stem} · EasyOCR")
            if combined is not None:
                messages.append(f"EasyOCR consolidado em {combined.name}.")

    status = combine_status(success_count, failure_count, skipped_count)
    if status == "failed":
        print(f"❌ Erro em Pure OCR Engines para '{pdf_path.name}'.")
    else:
        print(f"✅ OCR Engines finalizado para '{pdf_path.name}' com status: {status}.")

    return RunResult("OCR Engines", status, " ".join(messages), str(results_dir))

if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/ocr_engines")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_ocr_engines(str(pdfs[0]), str(output_folder))
