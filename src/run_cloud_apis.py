import os
import base64
from pathlib import Path
import google.generativeai as genai
from openai import OpenAI
from pdf2image import convert_from_path

# Configura APIs pegando do ambiente (lembre-se de rodar 'source ~/.secrets' antes)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

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

def run_gemini(image_path: str, output_path: Path):
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            return
            
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Faz upload da img pro gemini
        sample_file = genai.upload_file(image_path)
        
        response = model.generate_content([PROMPT, sample_file])
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)
    except Exception as e:
        print(f"Erro no Gemini: {e}")

def run_openai(image_path: str, output_path: Path):
    try:
        if not os.environ.get("OPENAI_API_KEY"):
            return
            
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
            max_tokens=2048
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.choices[0].message.content)
    except Exception as e:
        print(f"Erro no OpenAI: {e}")

def run_cloud_apis(input_pdf: str, output_dir: str):
    pdf_path = Path(input_pdf)
    results_dir = Path(output_dir) / pdf_path.stem
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Extração VLMs (Nuvem): Usando Gemini e GPT-4o para PDF '{pdf_path.name}'...")
    
    try:
        # Modelos VLM de API geralmente comem imagens.
        # Poderíamos enviar o PDF via File API, mas para consistência e suporte multi-página granular, converteremos pra imagem.
        images = convert_from_path(str(pdf_path))
        
        gemini_dir = results_dir / "gemini"
        gemini_dir.mkdir(exist_ok=True)
        openai_dir = results_dir / "openai"
        openai_dir.mkdir(exist_ok=True)
        
        for i, img in enumerate(images):
            temp_img_path = results_dir / f"vlm_temp_{i}.jpg"
            # Converte pra JPG pq é mais eficiente e mais compatível que PNG
            img.convert('RGB').save(temp_img_path, "JPEG")
            
            # Gemini
            run_gemini(str(temp_img_path), gemini_dir / f"page_{i}.md")
            # OpenAI
            run_openai(str(temp_img_path), openai_dir / f"page_{i}.md")
            
            os.remove(temp_img_path)
            
        print(f"✅ Extração VLM Cloud Concluída para '{pdf_path.name}'.")
        
    except Exception as e:
        print(f"❌ Erro nas APIs Nuvem para '{pdf_path.name}':\n{e}")

if __name__ == "__main__":
    input_folder = Path("input")
    output_folder = Path("docs/results/cloud_apis")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(input_folder.glob("*.pdf"))
    if pdfs:
        run_cloud_apis(str(pdfs[0]), str(output_folder))
