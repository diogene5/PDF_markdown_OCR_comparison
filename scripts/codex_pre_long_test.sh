#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CHECKPOINT_FILE="docs/codex_checkpoint.md"
DESCRIPTION="${*:-teste longo sem descricao}"
STAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"
BRANCH="$(git branch --show-current)"
COMMIT="$(git rev-parse --short HEAD)"
STATUS="$(git status --short --branch)"

if [ ! -f "$CHECKPOINT_FILE" ]; then
    echo "Arquivo nao encontrado: $CHECKPOINT_FILE" >&2
    exit 1
fi

printf -- "- \`%s\` - antes de teste longo: %s | branch \`%s\` | commit \`%s\`\n" \
    "$STAMP" "$DESCRIPTION" "$BRANCH" "$COMMIT" >> "$CHECKPOINT_FILE"

echo "Checkpoint registrado em $CHECKPOINT_FILE"
echo
echo "Resumo salvo:"
echo "- descricao: $DESCRIPTION"
echo "- branch: $BRANCH"
echo "- commit: $COMMIT"
echo
echo "Git status atual:"
echo "$STATUS"
echo
echo "Ao terminar o teste, volte em docs/codex_checkpoint.md e registre o resultado em 2 a 5 linhas."
