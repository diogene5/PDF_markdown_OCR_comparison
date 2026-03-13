#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

print_section() {
    echo
    echo "== $1 =="
}

print_section "Git status"
git status --short --branch

print_section "Commits recentes"
git --no-pager log --oneline -n 5

current_branch="$(git branch --show-current)"

if command -v gh >/dev/null 2>&1; then
    print_section "PR aberta para a branch atual"
    gh pr list --head "$current_branch" --limit 1 || true
else
    print_section "PR aberta para a branch atual"
    echo "gh nao encontrado"
fi

if command -v agent-history >/dev/null 2>&1; then
    print_section "Sessoes recentes deste projeto"
    agent-history list --here -n 5 || true
else
    print_section "Sessoes recentes deste projeto"
    echo "agent-history nao encontrado"
fi

print_section "Checkpoint"
if [ -f "docs/codex_checkpoint.md" ]; then
    sed -n '1,220p' docs/codex_checkpoint.md
else
    echo "docs/codex_checkpoint.md nao encontrado"
fi

echo
echo "Proximo comando sugerido antes de testes longos:"
echo "./scripts/codex_pre_long_test.sh \"descricao do teste\""
