document.addEventListener("DOMContentLoaded", () => {
    const pdfSelector = document.getElementById("pdfSelector");
    const toolLeft = document.getElementById("toolLeft");
    const toolRight = document.getElementById("toolRight");
    const refreshButton = document.getElementById("refreshButton");
    const manifestStamp = document.getElementById("manifestStamp");
    const statusGrid = document.getElementById("statusGrid");
    const leftTitle = document.getElementById("leftTitle");
    const rightTitle = document.getElementById("rightTitle");
    const leftMeta = document.getElementById("leftMeta");
    const rightMeta = document.getElementById("rightMeta");
    const contentLeft = document.getElementById("contentLeft");
    const contentRight = document.getElementById("contentRight");

    let manifest = null;

    marked.setOptions({
        breaks: true,
        gfm: true,
    });

    async function loadManifest() {
        const response = await fetch(`results/manifest.json?ts=${Date.now()}`);
        if (!response.ok) {
            throw new Error("Manifesto ainda nao encontrado. Rode ./run.sh primeiro.");
        }
        manifest = await response.json();
        renderSelectors();
        renderSelectedPdf();
    }

    function renderSelectors() {
        if (!manifest) {
            return;
        }

        const currentPdf = pdfSelector.value;
        const currentLeft = toolLeft.value;
        const currentRight = toolRight.value;

        pdfSelector.innerHTML = "";
        for (const pdf of manifest.pdfs) {
            const option = document.createElement("option");
            option.value = pdf.name;
            option.textContent = `${pdf.name} (${pdf.available_tools}/${manifest.tools.length})`;
            pdfSelector.appendChild(option);
        }

        toolLeft.innerHTML = "";
        toolRight.innerHTML = "";
        for (const tool of manifest.tools) {
            const leftOption = document.createElement("option");
            leftOption.value = tool.id;
            leftOption.textContent = `${tool.label} · ${tool.family}`;
            toolLeft.appendChild(leftOption);

            const rightOption = document.createElement("option");
            rightOption.value = tool.id;
            rightOption.textContent = `${tool.label} · ${tool.family}`;
            toolRight.appendChild(rightOption);
        }

        pdfSelector.value = currentPdf || manifest.pdfs[0]?.name || "";
        toolLeft.value = currentLeft || toolLeft.dataset.defaultTool;
        toolRight.value = currentRight || toolRight.dataset.defaultTool;
    }

    function getSelectedPdf() {
        if (!manifest) {
            return null;
        }
        return manifest.pdfs.find((pdf) => pdf.name === pdfSelector.value) || null;
    }

    function formatStamp(value) {
        try {
            return new Date(value).toLocaleString("pt-BR");
        } catch {
            return value;
        }
    }

    function renderStatusCards(pdf) {
        statusGrid.innerHTML = "";
        for (const tool of manifest.tools) {
            const artifact = pdf.outputs[tool.id];
            const card = document.createElement("article");
            card.className = `status-card ${artifact.available ? "is-available" : "is-missing"}`;
            const pages = artifact.page_count ? ` · ${artifact.page_count} paginas` : "";
            card.innerHTML = `
                <h3>${tool.label}</h3>
                <p>${artifact.available ? "Disponivel" : "Sem arquivo gerado"}${pages}</p>
                <code>${artifact.path || "sem caminho"}</code>
            `;
            statusGrid.appendChild(card);
        }
    }

    function renderUnavailable(target, titleNode, metaNode, toolId) {
        const tool = manifest.tools.find((item) => item.id === toolId);
        titleNode.textContent = tool ? tool.label : toolId;
        metaNode.textContent = "Sem arquivo consolidado para este PDF.";
        target.innerHTML = `
            <div class="empty-state">
                <strong>Sem resultado disponível.</strong>
                <p>Rode novamente a ferramenta ou escolha outra comparação.</p>
            </div>
        `;
    }

    function isRelativePath(value) {
        return value && !/^(?:[a-z]+:|\/|#)/i.test(value);
    }

    function rewriteMarkdownRelativePaths(rawText, artifactPath) {
        const parts = artifactPath.split("/");
        parts.pop();
        const baseDir = parts.join("/");
        return rawText.replace(/(!?\[[^\]]*\]\()([^)]+)(\))/g, (match, prefix, target, suffix) => {
            return isRelativePath(target) ? `${prefix}${encodeURI(`${baseDir}/${target}`)}${suffix}` : match;
        });
    }

    async function renderPane(toolId, titleNode, metaNode, contentNode) {
        const pdf = getSelectedPdf();
        if (!pdf) {
            return;
        }
        const tool = manifest.tools.find((item) => item.id === toolId);
        const artifact = pdf.outputs[toolId];
        if (!artifact || !artifact.available || !artifact.path) {
            renderUnavailable(contentNode, titleNode, metaNode, toolId);
            return;
        }

        titleNode.textContent = tool.label;
        metaNode.textContent = `${artifact.path}${artifact.page_count ? ` · ${artifact.page_count} paginas` : ""}`;
        contentNode.innerHTML = "<div class='loading'>Carregando...</div>";

        try {
            const response = await fetch(`${artifact.path}?ts=${Date.now()}`);
            if (!response.ok) {
                throw new Error("Falha ao carregar arquivo.");
            }
            const rawText = await response.text();
            if (artifact.format === "json") {
                contentNode.innerHTML = `<pre><code>${escapeHtml(rawText)}</code></pre>`;
            } else if (artifact.format === "md") {
                const rewrittenText = rewriteMarkdownRelativePaths(rawText, artifact.path);
                contentNode.innerHTML = marked.parse(rewrittenText);
            } else {
                contentNode.innerHTML = `<pre>${escapeHtml(rawText)}</pre>`;
            }
        } catch (error) {
            contentNode.innerHTML = `
                <div class="empty-state">
                    <strong>Falha ao abrir o resultado.</strong>
                    <p>${escapeHtml(String(error.message || error))}</p>
                </div>
            `;
        }
    }

    function escapeHtml(value) {
        return value
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;");
    }

    async function renderSelectedPdf() {
        if (!manifest || !manifest.pdfs.length) {
            return;
        }
        const pdf = getSelectedPdf();
        if (!pdf) {
            return;
        }
        manifestStamp.textContent = `Manifesto atualizado em ${formatStamp(manifest.generated_at)}`;
        renderStatusCards(pdf);
        await Promise.all([
            renderPane(toolLeft.value, leftTitle, leftMeta, contentLeft),
            renderPane(toolRight.value, rightTitle, rightMeta, contentRight),
        ]);
    }

    async function refreshAll() {
        try {
            manifestStamp.textContent = "Atualizando manifesto...";
            await loadManifest();
        } catch (error) {
            manifestStamp.textContent = "Manifesto indisponivel.";
            statusGrid.innerHTML = `
                <div class="empty-state wide">
                    <strong>Manifesto ainda nao encontrado.</strong>
                    <p>${escapeHtml(String(error.message || error))}</p>
                    <p>Rode <code>./run.sh</code> e depois abra a pasta docs com um servidor local.</p>
                </div>
            `;
            contentLeft.innerHTML = "";
            contentRight.innerHTML = "";
        }
    }

    pdfSelector.addEventListener("change", renderSelectedPdf);
    toolLeft.addEventListener("change", renderSelectedPdf);
    toolRight.addEventListener("change", renderSelectedPdf);
    refreshButton.addEventListener("click", refreshAll);

    refreshAll();
});
