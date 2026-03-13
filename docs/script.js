document.addEventListener('DOMContentLoaded', () => {
    const pdfSelector = document.getElementById('pdfSelector');
    const btnCompare = document.getElementById('btnCompare');
    
    const toolLeft = document.getElementById('toolLeft');
    const contentLeft = document.getElementById('contentLeft');
    
    const toolRight = document.getElementById('toolRight');
    const contentRight = document.getElementById('contentRight');

    // Configurando o Marked.js para interpretar quebras de linha como paragrafos e outras configs
    marked.setOptions({
        breaks: true,
        gfm: true,
    });

    async function fetchResult(pdfName, toolPath) {
        // As ferramentas salvam na pasta de results: docs/results/{toolPath}/{pdfName}/{pdfName}.md
        // Exemplo: docs/results/marker/005 - Parada/005 - Parada.md
        // Exceções: Motores de OCR linha pura (Tesseract, EasyOCR) e VLM geram pages (page_0.txt, page_0.md)
        // Para simplificar a didática deste MVP, vamos tentar pegar o primeiro arquivo válido retornado.
        
        let urlPath = "";
        
        // Regras de caminho baseadas nos scripts python gerados:
        const baseFolder = `results/${toolPath}/${pdfName}`;
        
        // Lista de possíveis nomes de arquivo que nossos scripts geram para uma página/documento
        const possibleFiles = [
            `${pdfName}.md`,          // Marker, Docling, MarkItDown, MinerU
            `page_0.md`,              // Gemini, OpenAI
            `surya/results.json`,     // Surya CLI text dump
            `tesseract/page_0.txt`,   // Tesseract
            `easyocr/page_0.txt`,     // EasyOCR
            `auto/${pdfName}.md`      // Variantes de output (MinerU as vezes gera dentro de /auto)
        ];

        for(let file of possibleFiles) {
            try {
                const response = await fetch(`${baseFolder}/${file}`);
                if (response.ok) {
                    const text = await response.text();
                    return { text, format: file.endsWith('.json') ? 'json' : file.endsWith('.txt') ? 'txt' : 'md' };
                }
            } catch (e) {
                console.log(`Tentativa falhou para ${file}`);
            }
        }
        
        return { text: "⚠️ Arquivo de resultado não encontrado. Você rodou main_runner.py para este PDF/ferramenta?", format: 'txt' };
    }

    async function loadComparisons() {
        const pdfName = pdfSelector.value;
        const leftTool = toolLeft.value;
        const rightTool = toolRight.value;

        contentLeft.innerHTML = "<div style='text-align: center; color: #8b949e;'>Carregando...</div>";
        contentRight.innerHTML = "<div style='text-align: center; color: #8b949e;'>Carregando...</div>";

        // Fetching Side-by-Side
        const [leftRes, rightRes] = await Promise.all([
            fetchResult(pdfName, leftTool),
            fetchResult(pdfName, rightTool)
        ]);

        // Render Left
        contentLeft.innerHTML = renderContent(leftRes.text, leftRes.format);
        
        // Render Right
        contentRight.innerHTML = renderContent(rightRes.text, rightRes.format);
    }

    function renderContent(rawText, format) {
        if (rawText.startsWith('⚠️')) {
            return `<div style="color: #ff7b72; padding: 20px; text-align: center;">${rawText}</div>`;
        }

        if (format === 'md') {
            return marked.parse(rawText);
        } else if (format === 'json') {
            return `<pre><code>${rawText}</code></pre>`;
        } else {
            // Text puro
            return `<pre style="white-space: pre-wrap;">${rawText}</pre>`;
        }
    }

    btnCompare.addEventListener('click', loadComparisons);
    
    // Auto load first test if possible
    // loadComparisons();
});
