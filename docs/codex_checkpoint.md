# Codex Checkpoint

- Atualizado em: `2026-03-13 18:22:11 -03`
- Projeto: `PDF_markdown_OCR_comparison`
- Branch ativa: `codex-runner-hardening-diagnostics`
- Ultimo commit local: `a10e7b6` - `Add a durable Codex checkpoint and resume workflow`
- PR ativa: `#1` - `Harden runners and document environment diagnostics`
- URL da PR: `https://github.com/diogene5/PDF_markdown_OCR_comparison/pull/1`

## Estado atual do projeto

- `run_cloud_apis.py` e `run_ocr_engines.py` agora processam pagina por pagina para reduzir uso de memoria.
- O runner do Gemini foi atualizado para usar um modelo atual e o smoke test curto passou.
- `surya` foi alinhado ao CLI instalado e `markitdown` passou a depender explicitamente do extra de PDF.
- O projeto ganhou manifesto real de resultados, arquivos consolidados `document.md` e um observatorio visual em `docs/`.
- Os dois ultimos blocos funcionais ja estao commitados localmente, e a branch agora esta `ahead 2` do remoto.
- `docs/results/` continua como saida local gerada e nao deve entrar nos commits.

## Bloco atual

- Nome: `Retomada segura e checkpoint operacional`
- Status: concluido localmente
- Objetivo: deixar o projeto resistente a perda de contexto, com um ponto unico de retomada e uma rotina curta antes de execucoes longas.

## Proximos passos provaveis

1. Rodar `./scripts/codex_resume.sh` quando retomar o projeto.
2. Fazer `git push` para publicar os commits locais `6716d72` e `a10e7b6` e atualizar a PR `#1`.
3. Antes de qualquer teste longo, rodar `./scripts/codex_pre_long_test.sh "descricao do teste"`.
4. Depois do teste, atualizar este arquivo com resultado curto e decidir se fecha outro bloco de commit.

## Como estamos trabalhando neste projeto

- Fechar blocos curtos com resultado observavel: diagnostico, correcao, validacao.
- Fazer commit quando um bloco funcional termina, sem misturar artefatos de `docs/results/`.
- Deixar um checkpoint antes de processos demorados, autenticacao externa ou servidor local.
- Responder sempre com o estado real do ambiente, nao com suposicoes.
- Preferir comandos praticos e reaproveitaveis para voce rodar depois sem depender da memoria da conversa.

## Comando padrao de retomada

```bash
./scripts/codex_resume.sh
```

Esse comando mostra:

- estado do git
- commits recentes
- PR da branch atual, se houver `gh`
- sessoes recentes do projeto, se houver `agent-history`
- este checkpoint

## Mini-rotina antes de testes longos

1. Rodar `./scripts/codex_pre_long_test.sh "o que vai rodar"`.
2. Confirmar branch, commit e status antes de iniciar.
3. Rodar o teste longo.
4. Ao terminar, voltar neste arquivo e registrar em 2 a 5 linhas:
   - o comando executado
   - o que aconteceu
   - se abriu novo bug
   - se virou commit ou ficou pendente

## O que "blocos menores e commits frequentes" significa aqui

Exemplo ruim:

- mudar runner de OCR
- mudar runner de cloud
- mexer em visualizacao HTML
- instalar dependencia
- publicar no GitHub
- abrir PR
- testar tudo no fim

Isso mistura causa, efeito e validacao. Se a conversa cair no meio, fica dificil dizer o que realmente fechou.

Exemplo bom:

1. Bloco `memoria`: processar PDFs pagina por pagina, validar com smoke test, commit.
2. Bloco `gemini`: corrigir modelo da API, validar 1 pagina, commit.
3. Bloco `surya + markitdown`: corrigir comandos/dependencias, validar isoladamente, commit.
4. Bloco `UX de resultados`: manifesto + `document.md` + `docs/index.html`, validar no navegador, commit.
5. Bloco `publicacao`: push, PR, comentario final.

Cada bloco deve responder tres perguntas:

- o que foi mudado
- como foi validado
- qual e o proximo passo

## Log de checkpoints

- `2026-03-13 18:19:16 -03` - checkpoint inicial criado com estado atual da branch, PR e rotina de retomada.
- `2026-03-13 18:20:51 -03` - antes de teste longo: smoke test da rotina de checkpoint | branch `codex-runner-hardening-diagnostics` | commit `6716d72`
- `2026-03-13 18:21:00 -03` - `./scripts/codex_resume.sh` e `./scripts/codex_pre_long_test.sh` executados com sucesso.
- `2026-03-13 18:22:11 -03` - commit `a10e7b6` criado para fechar o bloco de retomada segura.
