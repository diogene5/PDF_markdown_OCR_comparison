# Comparador de PDF → Markdown e OCR

Este projeto compara como diferentes ferramentas transformam o mesmo PDF em:

- markdown estruturado
- OCR puro
- interpretação visual por modelos de nuvem

## Visão geral

```mermaid
flowchart TD
    A[PDF de entrada] --> B[Ferramentas locais estruturais]
    A --> C[Motores de OCR]
    A --> D[Modelos de nuvem]
    B --> E[Markdown]
    C --> F[Texto OCR]
    D --> G[Markdown por pagina]
    E --> H[docs/results]
    F --> H
    G --> H
    H --> I[docs/results/manifest.json]
    I --> J[docs/index.html]
```

## Ferramentas comparadas

- `marker`
- `mineru`
- `docling`
- `markitdown`
- `surya`
- `tesseract`
- `easyocr`
- `openai`
- `gemini`

## Qual família usar

- `marker`, `mineru`, `docling`, `markitdown`
  Use quando você quer markdown utilizável, com foco em estrutura, seções, listas, tabelas e leitura final.
- `surya`, `tesseract`, `easyocr`
  Use quando o PDF parece scan ou imagem e seu objetivo principal é extrair texto, não reconstruir layout final.
- `openai`, `gemini`
  Use quando você quer comparar entendimento visual por página e aceita custo de API e mais latência.

Regra prática:

- Quer markdown final para leitura ou comparação: comece por `marker` ou `mineru`.
- Quer OCR bruto de scan: use `surya` ou o grupo `ocr`.
- Quer ver como um modelo multimodal interpreta a página: use `cloud`.

## Como rodar tudo

1. Crie e ative o ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Carregue as chaves:

```bash
source ~/.secrets
```

4. Rode o fluxo completo:

```bash
./run.sh
```

## Como abrir a visualização

```bash
python3 scripts/build_manifest.py
./scripts/serve_docs.sh
```

Depois abra `http://localhost:8000`.

## Retomada segura e testes longos

Quando a sessao ficar longa ou voce for parar e voltar depois, use:

```bash
./scripts/codex_resume.sh
```

Esse comando mostra o estado do git, commits recentes, PR da branch atual, sessoes recentes do projeto e o checkpoint operacional em `docs/codex_checkpoint.md`.

Antes de rodar algo demorado, deixe um checkpoint curto:

```bash
./scripts/codex_pre_long_test.sh "descricao do teste longo"
```

Depois do teste, atualize `docs/codex_checkpoint.md` com o que aconteceu e, se o bloco fechou, faca um commit antes de mudar de assunto.

## Testar um PDF qualquer fora deste projeto

### Marker

```bash
source venv/bin/activate
python3 scripts/run_one.py \
  --tool marker \
  --input ~/Downloads/meu-pdf.pdf \
  --output ~/Desktop/pdf-tests
```

### MinerU

```bash
source venv/bin/activate
python3 scripts/run_one.py \
  --tool mineru \
  --input ~/Downloads/meu-pdf.pdf \
  --output ~/Desktop/pdf-tests
```

### Surya isolado

```bash
source venv/bin/activate
python3 scripts/run_one.py \
  --tool surya \
  --input ~/Downloads/meu-pdf.pdf \
  --output ~/Desktop/pdf-tests
```

### OCR completo

```bash
source venv/bin/activate
python3 scripts/run_one.py \
  --tool ocr \
  --input ~/Downloads/meu-pdf.pdf \
  --output ~/Desktop/pdf-tests
```

## Saídas importantes

- `docs/results/...`: resultados gerados
- `docs/results/manifest.json`: mapa real do que foi gerado
- `docs/index.html`: interface visual
- `document.md`: arquivo consolidado para ferramentas que antes geravam só `page_0`, `page_1`, etc.

## Observações práticas

- `Marker` e `MinerU` costumam ser os melhores para preservar figuras e estrutura.
- `Docling` tende a produzir markdown mais limpo.
- `Cloud APIs` e `OCR Engines` agora processam uma página por vez para reduzir uso de memória.
- `MarkItDown` precisa ser instalado com suporte a PDF: `markitdown[pdf]`.
- `Surya` depende do CLI atual `surya_ocr ... --output_dir ...`.

## Documentação adicional

- Guia prático: `docs/guia_pratico.md`
- Checkpoint operacional: `docs/codex_checkpoint.md`
- Diagnóstico do endurecimento do runner: `docs/diagnostics/2026-03-13-runner-hardening.md`
