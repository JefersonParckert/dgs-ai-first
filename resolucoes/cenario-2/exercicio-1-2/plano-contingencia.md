# Plano de Contingência — Indisponibilidade de MCP Server

> **Princípio:** um **agente degradado com aviso** é melhor que um **agente que alucina**. Quando um server cai ou perde acesso a uma pasta, o agente deve **reduzir capacidade e avisar explicitamente** — nunca preencher a lacuna inventando.
> Esta é a aplicação direta do guardrail central do projeto (ADR-0003 e requisitos do Product Specialist): *nunca inventar; sempre dizer quando não tem a informação.*

---

## 1. Detecção

A queda é detectada pelo `scripts/mcp-health-check.mjs` (ver [evidencia-execucao-health-check.md](evidencia-execucao-health-check.md)):
- Pré-sessão (dev roda manualmente) e no CI (passo que falha com exit code 1 se server crítico DOWN).
- A rodada de **fault injection** já comprovou a detecção: `filesystem-knowledge` apontado para pasta inexistente → **DOWN**, com a causa (pasta ausente) e exit code 1, em ~8s.

---

## 2. Matriz de contingência por server

| Server | Criticidade | Sintoma | Comportamento esperado do agente (degradação avisada) | Ação de recuperação |
|---|:--:|---|---|---|
| `filesystem-knowledge` | **Alta** | Sem acesso a `docs/novatech` ou `data/retrieval-corpus` | **PARAR de responder com base em conhecimento.** Emitir aviso: *"Base de conhecimento indisponível — não posso responder com fonte; escale ao supervisor."* **NÃO** responder de memória nem inventar chunk/fonte. | Verificar pasta/permissão; re-rodar health check; só então retomar |
| `filesystem-workspace` | **Alta** | Sem acesso a `src/specs/skills` | Suspender geração/edição de código. Avisar: *"Workspace indisponível — não vou gerar arquivos às cegas."* Não escrever fora do escopo. | Restaurar escopo no `.mcp/mcp.json`; health check |
| `git` | Média | Sem histórico/diff/branches | Operar **sem contexto de histórico**, declarando: *"Sem acesso ao histórico do repo; descrição de PR pode estar incompleta."* Continuar tarefas que não dependem de git. | Verificar repo/Node; reinstalar server |
| `memory` | Média | Sem grafo de decisões/linguagem ubíqua | Operar **sem memória de longo prazo**; pedir ao humano os termos/decisões necessários em vez de assumir. Avisar que decisões anteriores não estão carregadas. | Restaurar `./.mcp/memory-graph.json` (versionado/backup) |
| `everything` | Nula (não-prod) | Indisponível | **Ignorar.** Não participa de fluxos de produção. | Sem ação urgente |

**Regra transversal:** a indisponibilidade do `filesystem-knowledge` **bloqueia respostas de domínio** — é exatamente o caso que mais geraria alucinação se o agente "improvisasse". Preferir falha visível a resposta confiante e errada.

---

## 3. Modos de degradação (capacidade reduzida, não parada total)

Em vez de "se cair, para tudo", o sistema tem **níveis**:

| Nível | Servers ativos | O que o agente AINDA faz | O que NÃO faz |
|---|---|---|---|
| **Pleno** | todos | tudo | — |
| **Degradado-conhecimento** | tudo menos `filesystem-knowledge` | refatorar código, ler histórico, usar memória | responder perguntas de negócio com fonte |
| **Degradado-workspace** | tudo menos `filesystem-workspace` | responder perguntas de conhecimento, analisar histórico | gerar/editar arquivos |
| **Degradado-contexto** | tudo menos `git`/`memory` | gerar código e responder com fonte, com aviso de contexto reduzido | garantir descrição de PR completa / lembrar decisões antigas |
| **Mínimo seguro** | nenhum crítico | apenas conversa; recusa tarefas que exigem dados ausentes, com aviso | qualquer ação que dependa de server DOWN |

Cada degradação é **anunciada ao usuário** no início da resposta.

---

## 4. Procedimento operacional (runbook curto)

1. **Health check acusou DOWN** → identificar server e causa na saída (a causa vem do stderr do server, ex.: pasta ausente).
2. **Classificar** criticidade pela matriz (§2) e entrar no nível de degradação correspondente (§3).
3. **Avisar o time** (canal do projeto) se for server crítico; registrar em `docs/runbooks/mcp-incidents.md`.
4. **Corrigir a causa** (pasta/permissão/versão de pacote/toolchain).
5. **Re-rodar o health check** — só retomar nível Pleno com `RESUMO: N UP / 0 DOWN` (exit code 0).
6. **Postmortem leve** se recorrente: a causa deveria ser pega por versionamento (§5 da arquitetura)?

---

## 5. Por que isso é melhor que "parar tudo"

- **Disponibilidade parcial > indisponibilidade total:** se só o `git` caiu, o dev ainda gera código — não fica bloqueado.
- **Segurança preservada:** o único caso em que o agente realmente recusa responder é quando responder significaria **inventar** (knowledge DOWN). Aí parar é a decisão correta.
- **Transparência:** todo modo degradado é avisado, então o humano sabe que está operando com capacidade reduzida e calibra a confiança na resposta.
