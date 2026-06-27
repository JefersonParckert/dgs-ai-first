# Cenário 2 — Exercício 2.2 (TECH LEAD): Arquitetura de MCP do projeto (servers locais)

**Papel:** Tech Lead · **Ferramentas:** Claude (chat) + GitHub Copilot
**Fonte:** [exercicio-2-fase-estruturacao.md](../../../praticas/pratica-2/exercicios-2/exercicio-2-fase-estruturacao.md) — seção TECH LEAD, Exercício 2.2

---

## O que o exercício pedia

1. **Documento de arquitetura de MCP** cobrindo: diagrama servers↔agentes (quem consome o quê, com qual escopo), política de aprovação de novos servers, monitoramento, e versionamento.
2. **Script de health check** (gerado com Copilot) que lê o `.mcp/mcp.json`, **sobe/consulta cada server local** e verifica que responde — **com saída de execução real**.
3. **Plano de contingência** para quando um server fica indisponível (agente degrada com aviso, não inventa).

---

## Entregáveis (arquivos desta pasta)

| Arquivo | Conteúdo |
|---------|----------|
| [arquitetura-mcp.md](arquitetura-mcp.md) | Documento de arquitetura: diagrama, tabela de consumo, política de aprovação, least privilege, monitoramento, versionamento. |
| [plano-contingencia.md](plano-contingencia.md) | Matriz de contingência por server, níveis de degradação avisada, runbook. |
| [evidencia-execucao-health-check.md](evidencia-execucao-health-check.md) | **Saída real** de 2 execuções: nominal (5/5 UP) + fault injection (1 DOWN). |
| [sandbox/.mcp/mcp.json](sandbox/.mcp/mcp.json) | Config dos 5 servers (least privilege; filesystem dividido em workspace-RW e knowledge-RO). |
| [sandbox/scripts/mcp-health-check.mjs](sandbox/scripts/mcp-health-check.mjs) | Script de health check (Node, sem deps; handshake MCP via stdio + deep-check). |
| `sandbox/` | Mini-repo `novatech-assistant` executável: `docs/novatech/` (Anexo A), `data/retrieval-corpus/` (Anexo B + metadados ADR-0003), `src/specs/skills/`, e `git init` + 2 commits + 2 branches. |

---

## Como reproduzir o teste real

```bash
cd sandbox
node scripts/mcp-health-check.mjs                                  # nominal → 5 UP / 0 DOWN, exit 0
node scripts/mcp-health-check.mjs --config ./.mcp/mcp.fault.json --only filesystem-knowledge   # fault → 1 DOWN, exit 1
```

Ambiente validado: **Windows 11 · Node v22.23.1 · npm 10.9.8**. Os servers `filesystem`, `memory`, `everything` e `git` (Node) rodam via `npx`; `uvx`/Python ausentes (motivou a escolha do server git em Node — ver arquitetura §2).

---

## Resultado do teste real (resumo)

| Rodada | Comando | Resultado | Exit |
|---|---|---|:--:|
| Nominal | `mcp-health-check.mjs` | **5 UP / 0 DOWN** — todos com tools/resources reais; `filesystem-knowledge` listou `docs/novatech` e **leu um chunk** (`POL-001-A.json`) | 0 |
| Fault injection | `--config mcp.fault.json` (pasta de docs ausente) | **1 DOWN** — causa exata reportada (pasta inexistente) | 1 |

Prova que o health check é **funcional e executado**: lista as primitivas de cada server, confirma que o filesystem enxerga `docs/novatech`, e **detecta falha** (não só imprime verde).

---

## Rastreabilidade às decisões do cenário 1

| Elemento da arquitetura | Origem |
|---|---|
| `filesystem-knowledge` (RO) simula o plano de dados do Azure AI Search | [ADR-0004](../../cenario-1/exercicio-1-1/ADR-0004-build-vs-buy-pipeline-rag.md) |
| Chunks do corpus com `status`/`data_vigencia`; `memory` guarda decisão de vigência | [ADR-0003](../../cenario-1/exercicio-1-1/ADR-0003-documentos-contraditorios.md) |
| `memory` evita recarregar contexto a cada turno (disciplina de budget) | [ADR-0002](../../cenario-1/exercicio-1-1/ADR-0002-gerenciamento-contexto.md) |
| Estrutura de pastas (`src/specs/skills/docs/data`) e exemplo de `.mcp/mcp.json` | [Anexo C](../../../praticas/pratica-2/exercicios-2/anexo-c-estrutura-repositorio.md) |

---

## Atendimento aos critérios de avaliação (skill TL 2.2)

- **MCP como infraestrutura** → versionamento (SemVer de intenção + baseline + pinagem), monitoramento executável, política de aprovação com gate do TL. (arquitetura §2, §4, §5)
- **Diagrama de conexões** → diagrama ASCII + tabela de consumo com escopo e permissão por server. (arquitetura §1)
- **Health check executado** → script lê o `.mcp/mcp.json`, sobe/consulta cada server, lista tools/resources, confirma filesystem vendo `docs/novatech`; **saída real** de 2 rodadas. (evidência)
- **Plano de contingência realista** → níveis de degradação avisada (capacidade reduzida > parada total); knowledge DOWN bloqueia resposta de domínio para não alucinar. (contingência)
- **Política de aprovação equilibrada** → gate leve (ADR + revisão TL + health check), sem burocracia nem liberação total. (arquitetura §2)

## Evidência de uso das ferramentas

- **Claude (chat):** redigiu o documento de arquitetura, o plano de contingência, a política de aprovação e o desenho de least privilege; cruzou ADRs/Anexos.
- **GitHub Copilot / agente de codegen:** apoiou a geração do `mcp-health-check.mjs` (cliente MCP stdio + deep-check). O script foi **executado de verdade** — a evidência não é o código, é a **saída real** das execuções.

> **Nota de transparência:** o GitHub Copilot não é conectável neste ambiente CLI; a geração do script teve apoio de agente de codegen e o Tech Lead revisou. O diferencial exigido pela rubrica — **execução real dos servers locais** — está plenamente atendido: os 5 servers foram efetivamente subidos via `npx` e responderam ao handshake MCP, com saída anexada.
