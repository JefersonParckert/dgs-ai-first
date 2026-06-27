# Evidência de Execução — Health Check de MCP (saída real)

> Estas saídas foram **geradas executando o script de verdade** contra os MCP servers locais, na máquina do Tech Lead.
> Ambiente: Windows 11 · Node v22.23.1 · npm 10.9.8 · `uvx`/Python ausentes (ver nota de seleção de server no [arquitetura-mcp.md](arquitetura-mcp.md)).
> Reproduzir: `cd sandbox && node scripts/mcp-health-check.mjs`

O `sandbox/` é um mini-repo `novatech-assistant` autocontido, semeado com documentos do **Anexo A** (`docs/novatech/`) e chunks do **Anexo B** com metadados de vigência da **ADR-0003** (`data/retrieval-corpus/`), e com `git init` + 2 commits + 2 branches — para que o teste rode contra dados e histórico reais.

---

## Rodada 1 — NOMINAL (todos os servers ativos)

Comando: `node scripts/mcp-health-check.mjs`

```
============================================================
 MCP HEALTH CHECK — NovaTech Assistant
 config : ...\exercicio-1-2\sandbox\.mcp\mcp.json
 root   : ...\exercicio-1-2\sandbox
 quando : 2026-06-27T15:42:39.485Z
 servers: 5 (filesystem-workspace, filesystem-knowledge, git, memory, everything)
============================================================

→ probing filesystem-workspace ... UP (6678ms) | tools:14 resources:0
→ probing filesystem-knowledge ... UP (6541ms) | tools:14 resources:0
→ probing git ... UP (6701ms) | tools:28 resources:1
→ probing memory ... UP (6643ms) | tools:9 resources:0
→ probing everything ... UP (7018ms) | tools:13 resources:7

------------------------- DETALHE -------------------------

[UP] filesystem-workspace
  cmd      : npx -y @modelcontextprotocol/server-filesystem ./src ./specs ./skills
  server   : secure-filesystem-server v0.2.0
  latência : 6678ms
  tools    : 14 → read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, …
  resources: 0
  enxerga  : ...\sandbox\src | ...\sandbox\specs | ...\sandbox\skills
  listou   : 1 entradas em ...\sandbox\src

[UP] filesystem-knowledge
  cmd      : npx -y @modelcontextprotocol/server-filesystem ./docs/novatech ./data/retrieval-corpus
  server   : secure-filesystem-server v0.2.0
  latência : 6541ms
  tools    : 14 → read_file, read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, …
  resources: 0
  enxerga  : ...\sandbox\docs\novatech | ...\sandbox\data\retrieval-corpus
  listou   : 2 entradas em ...\sandbox\docs\novatech
  leu chunk: POL-001-A.json → "{ "chunk_id": "POL-001-A", "id_procedimento": "POL-001", "documento": "POL-001 — Política de Devolução", "secao": "3.1 Prazo geral", "dominio": "devol…"

[UP] git
  cmd      : npx -y @cyanheads/git-mcp-server
  server   : @cyanheads/git-mcp-server v2.15.1
  latência : 6701ms
  tools    : 28 → git_add, git_blame, git_branch, git_changelog_analyze, git_checkout, git_cherry_pick, git_clean, git_clear_working_dir, …
  resources: 1 → git://working-directory

[UP] memory
  cmd      : npx -y @modelcontextprotocol/server-memory
  server   : memory-server v0.6.3
  latência : 6643ms
  tools    : 9 → create_entities, create_relations, add_observations, delete_entities, delete_observations, delete_relations, read_graph, search_nodes, …
  resources: 0

[UP] everything
  cmd      : npx -y @modelcontextprotocol/server-everything
  server   : mcp-servers/everything v2.0.0
  latência : 7018ms
  tools    : 13 → echo, get-annotated-message, get-env, get-resource-links, get-resource-reference, get-structured-content, get-sum, get-tiny-image, …
  resources: 7 → demo://resource/static/document/architecture.md, demo://resource/static/document/extension.md, …

============================================================
 RESUMO: 5 UP / 0 DOWN  (de 5 servers)
============================================================
```
**Exit code: 0**

### O que esta rodada comprova (mapeado ao critério de avaliação)
- ✅ **Lê o `.mcp/mcp.json`** e proba **cada** server configurado (5/5).
- ✅ **Lista as tools/resources expostas** de cada server (com contagem e nomes reais — ex.: git expõe 28 tools, everything expõe 7 resources).
- ✅ **Confirma que o `filesystem` enxerga `docs/novatech`** — o deep-check do `filesystem-knowledge` chamou `list_allowed_directories` (vê `docs/novatech` e `data/retrieval-corpus`), `list_directory` (2 entradas em `docs/novatech`) e **leu um chunk real** (`POL-001-A.json`) via `read_text_file`. Isso prova acesso de leitura efetivo, não só que o processo subiu.

---

## Rodada 2 — FAULT INJECTION (pasta de docs ausente)

Para provar que o health check **detecta falha** (e não só imprime verde), apontei o `filesystem-knowledge` para uma pasta inexistente — o cenário exato do critério: *"filesystem sem a pasta de docs"*.

Comando: `node scripts/mcp-health-check.mjs --config ./.mcp/mcp.fault.json --only filesystem-knowledge`

```
============================================================
 MCP HEALTH CHECK — NovaTech Assistant
 config : ...\sandbox\.mcp\mcp.fault.json
 servers: 1 (filesystem-knowledge)
============================================================

→ probing filesystem-knowledge ... DOWN | processo encerrou (exit 1) antes de responder | stderr:   path: '...\sandbox\docs\PASTA-INEXISTENTE' / }

------------------------- DETALHE -------------------------

[DOWN] filesystem-knowledge
  cmd      : npx -y @modelcontextprotocol/server-filesystem ./docs/PASTA-INEXISTENTE ./data/retrieval-corpus
  erro     : processo encerrou (exit 1) antes de responder | stderr:   path: '...\sandbox\docs\PASTA-INEXISTENTE' / }

============================================================
 RESUMO: 0 UP / 1 DOWN  (de 1 servers)
============================================================
```
**Exit code: 1** (detecção tempo: ~8s, fail-fast por evento de `exit` do processo)

### O que esta rodada comprova
- ✅ O health check **identifica o server indisponível**, aponta a **causa exata** (a pasta que faltou, vinda do stderr do server) e **retorna exit code 1** — pronto para falhar um passo de CI ou disparar alerta.
- ✅ É a entrada do **[plano-contingencia.md](plano-contingencia.md)**: server de conhecimento DOWN → o agente deve **degradar com aviso**, nunca inventar.

---

## Observações técnicas reais colhidas na execução

1. **O `@modelcontextprotocol/server-filesystem` concede read+write a TODAS as pastas listadas** (expõe `write_file`, `edit_file`, `move_file`, `create_directory`). **Não há flag de read-only por diretório.** Por isso o least-privilege "read-only" para `docs/novatech` e `data/retrieval-corpus` é implementado com um **server separado** (`filesystem-knowledge`) + **enforcement no SO** (ver [arquitetura-mcp.md](arquitetura-mcp.md) §Least Privilege). Esta foi uma constatação empírica do health check, não suposição.
2. **`uvx`/Python ausentes** nesta máquina → o server `git` oficial (`uvx mcp-server-git`) não rodaria. O projeto padronizou no server `git` baseado em Node (`@cyanheads/git-mcp-server`), que roda no toolchain real do time — decisão de governança documentada na arquitetura. O health check validou que ele responde (28 tools + resource `git://working-directory`).
3. **Latência de cold start ~6–9s/server** (download via `npx` no 1º run; depois cacheado). Relevante para o timeout do monitoramento (o script usa 120s para `initialize`).
