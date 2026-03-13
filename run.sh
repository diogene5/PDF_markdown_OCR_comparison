#!/bin/bash
# Script prático para ativar o ambiente e rodar as extrações!

# Garantir que as senhas estão no ambiente
if [ -f ~/.secrets ]; then
    source ~/.secrets
fi

# Ativar virtual env
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️ Ambiente virtual não encontrado! Por favor, aguarde o pip install terminar."
    exit 1
fi

echo "🚀 Iniciando as extrações de PDF → Markdown & OCR..."
echo "🐍 Python ativo: $(which python3)"
python3 main_runner.py

echo "✅ Pronto! Para abrir o observatório visual, rode: python3 -m http.server 8000 -d docs"
