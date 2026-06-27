# Arquitetura de MCP do Projeto — NovaTech Assistant

> **Autor:** Tech Lead · **Status:** v1 (vigente) · **Escopo:** servers MCP **locais e gratuitos** da fase de estruturação.
> **Princípio-guia:** MCP servers são **infraestrutura gerenciada** — versionados, com escopo/permissões mínimas e observáveis — não configuração ad-hoc na máquina de cada dev.

Este documento define quais servers locais são autorizados, com quais escopos, como são aprovados, monitorados e versionados, e como o time é avisado de mudanças. Complementa o `.mcp/mcp.json` (config executável) e o `scripts/mcp-health-check.mjs` (observabilidade executável).

---

## 1. Servers autorizados e mapa de conexões

Quatro tipos de *reference server* do protocolo (o `filesystem` aparece **duas vezes**, com escopos distintos, por least privilege — ver §3).

### Diagrama (quem consome o quê, com qual escopo/permissão)

```
            ┌─────────────────────────────────────────────────────────────┐
            │                         AGENTES                              │
            │   Claude Code (TL, devs)        GitHub Copilot (devs, TL)    │
            └───────┬─────────────┬─────────────┬───────────┬─────────────┘
                    │             │             │           │
        ┌───────────▼──┐ ┌────────▼────────┐ ┌──▼───────┐ ┌─▼──────────┐ ┌──────────────┐
        │ filesystem-  │ │ filesystem-     │ │   git    │ │  memory    │ │  everything  │
        │ workspace    │ │ knowledge       │ │          │ │            │ │  (sandbox)   │
        │ ───────────  │ │ ─────────────   │ │ ──────── │ │ ────────── │ │ ──────────── │
        │ RW           │ │ READ-ONLY*      │ │ RW(repo) │ │ RW(grafo)  │ │ RW(efêmero)  │
        │ ./src        │ │ ./docs/novatech │ │ histórico│ │ decisões + │ │ aprendizado  │
        │ ./specs      │ │ ./data/         │ │ diff     │ │ linguagem  │ │ de primitivas│
        │ ./skills     │ │  retrieval-     │ │ branches │ │ ubíqua     │ │ MCP          │
        │              │ │  corpus         │ │          │ │            │ │              │
        └──────────────┘ └─────────────────┘ └──────────┘ └────────────┘ └──────────────┘
            código/        documentação de      governança    memória        treinamento
            specs/skills   negócio + chunks      do repo       persistente    do time
            (gerar/editar) (RAG grounding)       (contexto)    entre sessões  (NÃO-prod)

  * read-only não é flag nativa do server filesystem → enforcement por server separado + SO (§3).
```

### Tabela de consumo (necessidade do projeto → server → escopo → permissão → consumidor)

| Necessidade (cenário) | Server | Escopo (aponta para) | Permissão | Consumido por | Tools/Resources reais* |
|---|---|---|---|---|---|
| Ler/editar código, specs, skills | `filesystem-workspace` | `./src ./specs ./skills` | **Read-Write** | Claude Code, Copilot (devs, TL) | 14 tools (read/write/edit/list/search) |
| Ler doc de negócio (era Confluence) + "recuperar" chunks (era Azure AI Search) | `filesystem-knowledge` | `./docs/novatech ./data/retrieval-corpus` | **Read-Only** | Agentes (grounding/RAG) | 14 tools — só leitura é usada |
| Histórico, diff e branches do repo (era GitHub) | `git` | repositório local (`.`) | RW sobre metadados do repo | Agentes (contexto, descrição de PR) | 28 tools + resource `git://working-directory` |
| Glossário/linguagem ubíqua e decisões persistentes (ADR-0002/0003) | `memory` | grafo em `./.mcp/memory-graph.json` | RW (grafo) | Todos os agentes, entre sessões | 9 tools (entities/relations/observations) |
| Explorar primitivas de MCP | `everything` | — (efêmero) | RW efêmero | Devs (aprendizado) — **fora de fluxos de produção** | 13 tools + 7 resources demo |

\* Contagens **medidas** pelo health check (ver [evidencia-execucao-health-check.md](evidencia-execucao-health-check.md)), não estimadas.

### Conexão com as decisões do cenário 1
- **ADR-0004 (Buy: Azure AI Search):** em produção, o plano de dados de conhecimento é o Azure AI Search. Nesta fase local, o `filesystem-knowledge` (read-only) **simula esse plano** sobre `data/retrieval-corpus/`. Tratá-lo como read-only espelha o fato de que o corpus é *fonte*, não destino de escrita do agente.
- **ADR-0003 (vigência):** os chunks em `data/retrieval-corpus/` carregam `status` (ATIVO/SUPERSEDIDO) e `data_vigencia`. O `memory` server guarda a decisão de vigência e a linguagem ubíqua para os agentes não reabrirem a discussão a cada sessão.
- **ADR-0002 (context budget):** o `memory` evita recarregar contexto de decisões a cada turno; o `filesystem-knowledge` entrega só os chunks pedidos, sem despejar a base inteira no contexto.

---

## 2. Política de aprovação de novos servers

Adicionar um server ao `.mcp/mcp.json` é uma **mudança de infraestrutura** e segue gate leve (equilíbrio agilidade × segurança — não burocratiza, não libera tudo):

| Etapa | Quem | O que verifica |
|---|---|---|
| 1. Proposta | Qualquer dev | Abre PR alterando `.mcp/mcp.json` + 1 parágrafo em ADR (`docs/adr/NNNN-mcp-<server>.md`): necessidade, escopo mínimo, permissão (RO/RW), consumidores. |
| 2. Revisão de escopo | **Tech Lead** (obrigatório) | (a) escopo é o **mínimo suficiente**? (b) fontes de negócio estão **read-only**? (c) o escopo **não inclui** segredos (`.env`, `infra/parameters/*`, chaves)? (d) é *reference server* local e gratuito? |
| 3. Revisão de segurança | TL + Dev Sênior | Server é de fonte confiável/oficial? Comando/args sem caminho amplo demais (ex.: nunca `/` ou `~`)? `env` não vaza segredos? |
| 4. Validação executável | Autor | Roda `mcp-health-check.mjs` provando que o server sobe, expõe as tools esperadas e **só** enxerga o escopo aprovado. Saída anexada ao PR. |
| 5. Merge | Tech Lead | Aprova o PR (Gate 3 do AGENTS.md). Server passa a ser oficial. |

**Regra dura:** nenhum server entra sem (a) ADR de escopo, (b) revisão do TL e (c) saída do health check anexada. Configuração ad-hoc na máquina do dev (fora do `.mcp/mcp.json` versionado) é proibida.

### Seleção de server é decisão de governança (caso real deste projeto)
O server `git` **oficial** é `uvx mcp-server-git` (Python). As máquinas do time **não têm `uvx`/Python** padronizados (constatado no ambiente — ver evidência). Em vez de impor uma nova dependência de toolchain a todos, o projeto **padronizou no server `git` baseado em Node** (`@cyanheads/git-mcp-server`), que roda no toolchain já existente (Node 22). Isso materializa a nota do Anexo C: *"os nomes de pacote e comandos evoluem — confirme no README oficial antes de configurar"*. A decisão fica registrada como ADR de MCP.

---

## 3. Least Privilege (escopo e permissões mínimas)

| Server | Por que o escopo é o mínimo suficiente | Como a permissão é garantida |
|---|---|---|
| `filesystem-workspace` | Só `src/`, `specs/`, `skills/` — onde o agente legitimamente cria/edita. **Não** recebe `infra/`, `.git/`, `.env`, raiz do repo. | Read-Write (necessário p/ codegen) |
| `filesystem-knowledge` | Só `docs/novatech/` e `data/retrieval-corpus/` — fontes de leitura. Documento de negócio nunca deve ser reescrito pelo agente. | **Read-Only** — ver nota abaixo |
| `git` | Repositório local apenas (`.`). Sem remoto, sem credenciais. | Operações de leitura de histórico/diff/branch; escrita só via fluxo de commit revisado |
| `memory` | Arquivo de grafo dedicado (`./.mcp/memory-graph.json`). Não acessa o filesystem do projeto. | RW restrito ao próprio arquivo |
| `everything` | Sem escopo de dados do projeto; apenas primitivas de demonstração. | Marcado **não-produtivo** — não entra em fluxos de geração |

### Como o read-only é realmente enforçado (constatação empírica)
O `@modelcontextprotocol/server-filesystem` **concede read+write a todas as pastas que recebe** (expõe `write_file`, `edit_file`, `move_file` — confirmado pelo health check). Não há flag `--read-only` por diretório. Portanto, o read-only do `filesystem-knowledge` é garantido por **duas camadas**:
1. **Isolamento por server:** as fontes de leitura ficam num server **separado** do workspace de escrita. Mesmo que um agente chame `write_file` no knowledge server, o efeito fica contido ao escopo de conhecimento — e é detectável.
2. **Enforcement no SO:** as pastas `docs/novatech/` e `data/retrieval-corpus/` recebem permissão **somente-leitura** no sistema de arquivos (no Windows: `icacls <pasta> /deny "<user>:(W)"`; em Linux/CI: `chmod -R a-w`). Assim a escrita falha no nível do SO, independentemente do que o server exponha.

> **Recomendação de evolução:** acompanhar o release do `server-filesystem` que suporta *roots* read-only nativos via protocolo; quando estável, migrar o enforcement do SO para o próprio server e simplificar para um único server filesystem com roots tipadas.

---

## 4. Monitoramento (observabilidade executável)

O monitoramento **não é conceitual** — é o script `scripts/mcp-health-check.mjs`, que roda de verdade contra os servers locais.

**O que ele responde:**
- *Um server parou de responder?* → faz o handshake MCP (`initialize`) em cada server; se o processo morre ou estoura timeout, reporta **DOWN** com a causa e **exit code 1**.
- *Um server perdeu acesso a uma pasta?* → deep-check nos `filesystem-*`: chama `list_allowed_directories` + `list_directory` e (no knowledge) **lê um chunk real**. Se a pasta sumiu, o server nem sobe — detectado na rodada de fault injection.
- *Quais primitivas cada server expõe hoje?* → lista tools/resources (base para o versionamento — §5).

**Quando rodar:**
- **Local:** antes de iniciar uma sessão de codegen com agentes (`node scripts/mcp-health-check.mjs`).
- **CI:** passo no `ci.yml` que falha o build se algum server crítico (`filesystem-workspace`, `filesystem-knowledge`, `git`) estiver DOWN (exit code 1).
- **Pós-mudança:** obrigatório após qualquer alteração no `.mcp/mcp.json` (Gate da §2).

**Evidência de execução real (nominal 5/5 UP + fault 1 DOWN):** ver [evidencia-execucao-health-check.md](evidencia-execucao-health-check.md).

---

## 5. Versionamento (mudar escopo sem quebrar fluxos)

O `.mcp/mcp.json` é **versionado no Git** e tratado como contrato. Para evitar que mudar o escopo de um server quebre fluxos existentes:

1. **Config no repositório, não na máquina:** todos usam o mesmo `.mcp/mcp.json` versionado. Mudança = PR (nunca edição local silenciosa).
2. **Baseline de capacidades:** o health check exporta (`--json`) o conjunto de tools/resources de cada server. Esse snapshot é commitado como `baseline` (ex.: `.mcp/health-baseline.json`). Um PR que **remove** uma tool/resource ou **reduz** um escopo é sinalizado no diff → exige justificativa, porque pode quebrar um agente que dependia daquilo.
3. **SemVer de intenção no `.mcp/`:** mudanças classificadas como:
   - **PATCH** — corrige comando/versão de pacote sem alterar escopo nem tools (ex.: bump de versão do server). Baixo risco.
   - **MINOR** — adiciona server ou amplia tools mantendo os escopos existentes. Retrocompatível.
   - **MAJOR** — **reduz** escopo, troca RW→RO, remove server ou renomeia. **Quebra potencial** → exige aviso ao time + checagem de quais fluxos/skills referenciam aquele server.
4. **Pinagem de versão de server:** evitar `@latest` implícito. Quando um server estabilizar, fixar a versão no `args` (ex.: `@modelcontextprotocol/server-filesystem@2026.1.14`) para builds reproduzíveis; bump vira PATCH revisável.
5. **Aviso ao time:** toda mudança MAJOR/MINOR é anunciada no canal do projeto + nota no `docs/runbooks/mcp-changelog.md`, com data, autor, o que mudou e impacto esperado.

---

## 6. Resumo das garantias

| Atributo de infraestrutura | Como é atendido |
|---|---|
| **Versionado** | `.mcp/mcp.json` no Git; SemVer de intenção; baseline de capacidades; versões pinadas |
| **Escopo/permissão mínimos** | 2 filesystem servers (RW workspace / RO knowledge); sem segredos no escopo; everything marcado não-prod |
| **Observável** | `mcp-health-check.mjs` executável (handshake + deep-check + exit code), rodado em CI e pré-sessão |
| **Governado** | Política de aprovação com gate do TL, ADR de escopo e health check anexado ao PR |
| **Resiliente** | Plano de contingência com degradação avisada (ver [plano-contingencia.md](plano-contingencia.md)) |
