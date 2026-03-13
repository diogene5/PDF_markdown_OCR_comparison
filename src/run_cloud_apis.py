import os
import base64
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("⚠️ Biblioteca 'google-generativeai' não encontrada. Execute 'pip install google-generativeai'.")
    genai = None

try:
    from openai import OpenAI
except ImportError:
    print("⚠️ Biblioteca 'openai' não encontrada. Execute 'pip install openai'.")
    OpenAI = None

try:
    from pdf2image import convert_from_path, pdfinfo_from_path
except ImportError:
    print("⚠️ Biblioteca 'pdf2image' não encontrada. Execute 'pip install pdf2image'.")
    convert_from_path = None
    pdfinfo_from_path = None

_openai_client = None

from src.run_result import RunResult, combine_status
from src.output_helpers import combine_page_outputs

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "models/gemini-2.5-flash")
API_TIMEOUT_SECONDS = int(os.environ.get("API_TIMEOUT_SECONDS", "180"))

# Prompt universal focado na sua didática de comparação
PROMPT = """
Você é um avançado motor de Visão Robótica.
Por favor, olhe para esta imagem (que é uma página de um documento em PDF) e converta EXATAMENTE o que estiver escrito para o formato Markdown.

Requisitos Rigorosos:
1. Mantenha os Títulos com os níveis corretos (#, ##).
2. Se houver uma tabela na imagem, desenhe essa mesma tabela usando a formatação de tabela do Markdown.
3. Não resuma. Não adicione textos avisando que você converteu. Apenas reproduza o conteúdo fielmente.
"""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

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

def get_openai_client():
    global _openai_client

    if OpenAI is None:
        return None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    if _openai_client is None:
        _openai_client = OpenAI(api_key=api_key)

    return _openai_client

def run_gemini(image_path: str, output_path: Path):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if genai is None or not api_key:
            return False, "Gemini indisponível"

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        # Faz upload da img pro gemini
        sample_file = genai.upload_file(image_path)
        
        response = model.generate_content(
            [PROMPT, sample_file],
            request_options={"timeout": API_TIMEOUT_SECONDS},
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        return True, None
    except Exception as e:
        print(f"Erro no Gemini: {e}")
        return False, str(e)

def run_openai(image_path: str, output_path: Path):
    try:
        openai_client = get_openai_client()
        if openai_client is None:
            return False, "OpenAI indisponível"

        base64_img = encode_image(image_path)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048,
            timeout=API_TIMEOUT_SECONDS,
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.choices[0].message.content)
        return True, None
    except Exception as e:
        print(f"Erro no OpenAI: {e}")
        return False, str(e)

def run_cloud_apis(input_pdf: str, output_dir: str) -> RunResult:
    success_count = 0
    failure_count = 0
    skipped_count = 0
    messages: list[str] = []

    if convert_from_path is None or pdfinfo_from_path is None:
        message = "Gemini e OpenAI pulados: falta a dependência Python 'pdf2image'."
        print(f"⏭️ {message}")
        return RunResult("Cloud APIs", "skipped", message)

    gemini_enabled = genai is not None and bool(os.environ.get("GEMINI_API_KEY"))
    openai_enabled = get_openai_client() is not None
    if not gemini_enabled and not openai_enabled:
        message = "Nenhuma credencial/API disponível para Gemini ou OpenAI."
        print(f"⏭️ {message}")
        return RunResult("Cloud APIs", "skipped", message)

    pdf_path = Path(input_pdf)
    results_dir = Path(output_dir) / pdf_path.stem
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Extração VLMs (Nuvem): Usando Gemini e GPT-4o para PDF '{pdf_path.name}'...")
    
    try:
        gemini_dir = results_dir / "gemini"
        openai_dir = results_dir / "openai"
        if gemini_enabled:
            gemini_dir.mkdir(exist_ok=True)
        else:
            skipped_count += 1
            messages.append("Gemini pulado: variável `GEMINI_API_KEY` ausente ou biblioteca indisponível.")
        if openai_enabled:
            openai_dir.mkdir(exist_ok=True)
        else:
            skipped_count += 1
            messages.append("OpenAI pulado: `OPENAI_API_KEY` ausente ou biblioteca indisponível.")

        gemini_failures = 0
        openai_failures = 0
        total_pages = 0
        
        # Processa uma página por vez para evitar manter o PDF inteiro em memória.
        for i, total_pages, img in iter_pdf_pages(pdf_path):
            print(f"  -> Página {i + 1}/{total_pages}")
            temp_img_path = results_dir / f"vlm_temp_{i}.jpg"
            page_image = img.convert("RGB")

            try:
                # Converte pra JPG pq é mais eficiente e mais compatível que PNG
                page_image.save(temp_img_path, "JPEG")

                if gemini_enabled:
                    ok, error = run_gemini(str(temp_img_path), gemini_dir / f"page_{i}.md")
                    if not ok:
                        gemini_failures += 1
                        print(f"⚠️ Gemini falhou na página {i} de '{pdf_path.name}': {error}")

                if openai_enabled:
                    ok, error = run_openai(str(temp_img_path), openai_dir / f"page_{i}.md")
                    if not ok:
                        openai_failures += 1
                        print(f"⚠️ OpenAI falhou na página {i} de '{pdf_path.name}': {error}")
            finally:
                page_image.close()
                if temp_img_path.exists():
                    os.remove(temp_img_path)

        if gemini_enabled:
            if gemini_failures:
                failure_count += 1
                messages.append(f"Gemini falhou em {gemini_failures} página(s).")
            else:
                success_count += 1
                messages.append(f"Gemini concluído em {total_pages} página(s).")
            combined = combine_page_outputs(gemini_dir, title=f"{pdf_path.stem} · Gemini")
            if combined is not None:
                messages.append(f"Gemini consolidado em {combined.name}.")

        if openai_enabled:
            if openai_failures:
                failure_count += 1
                messages.append(f"OpenAI falhou em {openai_failures} página(s).")
            else:
                success_count += 1
                messages.append(f"OpenAI concluído em {total_pages} página(s).")
            combined = combine_page_outputs(openai_dir, title=f"{pdf_path.stem} · OpenAI")
            if combined is not None:
                messages.append(f"OpenAI consolidado em {combined.name}.")
            
        print(f"✅ Extração VLM Cloud Concluída para '{pdf_path.name}'.")
        
    except Exception as e:
        print(f"❌ Erro nas APIs Nuvem para '{pdf_path.name}':\n{e}")
        return RunResult("Cloud APIs", "failed", f"Falha ao processar '{pdf_path.name}': {e}", str(results_dir))

    status = combine_status(success_count, failure_count, skipped_count)
    return RunResult("Cloud APIs", status, " ".join(messages), str(results_dir))

if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/cloud_apis")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_cloud_apis(str(pdfs[0]), str(output_folder))
