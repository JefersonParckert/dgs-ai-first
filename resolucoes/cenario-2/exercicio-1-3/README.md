# Cenário 2 — Exercício 2.3 (TECH LEAD): Criação e teste de skills técnicas

**Papel:** Tech Lead · **Ferramentas:** Claude (chat) + GitHub Copilot
**Fonte:** [exercicio-2-fase-estruturacao.md](../../../praticas/pratica-2/exercicios-2/exercicio-2-fase-estruturacao.md) — seção TECH LEAD, Exercício 2.3

---

## O que o exercício pedia

1. Escrever o **SKILL.md completo** da skill `azure-functions-endpoint` (nível Domain): contexto, regras prescritivas, exemplos DO/DON'T, anti-padrões, dependências.
2. **Testar** com o Copilot: com o SKILL.md no repo, pedir a geração de um endpoint e avaliar a aderência.
3. **Iterar**: reescrever as seções que o agente não seguiu; testar de novo.
4. Definir **critérios de "skill madura"** (quando está pronta para uso pelo time).

**Entregável:** SKILL.md, outputs do Copilot (antes/depois), critérios de maturidade.

---

## Entregáveis (arquivos desta pasta)

| Arquivo | Conteúdo |
|---------|----------|
| [SKILL-v1.md](SKILL-v1.md) | Skill v1 (antes do teste). |
| [teste-rodada-1.md](teste-rodada-1.md) | **Output real** do agente com v1 (endpoint `feedback`). |
| [analise-v1.md](analise-v1.md) | Análise seguido/ignorado — placar 6/10; diagnóstico. |
| [SKILL-v2.md](SKILL-v2.md) | Skill v2 (iterada): snippets canônicos, `authLevel`, shape de erro c/ `requestId`, teste acompanhante, anti-padrões ampliados, checklist. |
| [teste-rodada-2.md](teste-rodada-2.md) | **Output real** com v2 (mesmo alvo `feedback`) + comparação — 10/10. |
| [teste-rodada-3.md](teste-rodada-3.md) | **Output real** com v2 num 2º alvo (`query`, resposta de domínio) — 12/12. |
| [criterios-maturidade.md](criterios-maturidade.md) | Estágios + critérios mensuráveis de maturidade; skill como artefato vivo. |

> A skill final (v2) foi **instalada no repositório**: [`novatech-assistant/skills/domain/azure-functions-endpoint.md`](../../../../novatech-assistant/skills/domain/azure-functions-endpoint.md).

---

## Metodologia do teste (evidência real — leia antes de avaliar D2)

O GitHub Copilot não é conectável neste ambiente CLI. Para obter **evidência de teste real** (geração → avaliação → reescrita), cada rodada foi executada por um **agente de codegen independente** (subagente Claude Code), no papel funcional do Copilot. Controles de validade:

- **Isolamento:** cada agente recebeu **apenas o conteúdo do SKILL.md** (v1 ou v2) + o pedido do dev. Sem acesso à análise, à resposta esperada ou a outros arquivos.
- **Variável controlada:** rodadas 1 e 2 usaram o **mesmo alvo e prompt**, variando só a skill → o ganho é atribuível à iteração. A rodada 3 mudou o alvo para validar generalização.
- **Outputs literais:** o código transcrito é exatamente o gerado pelos agentes.

---

## Resultado (execução real)

| Rodada | Alvo | Skill | Aderência |
|---|---|:--:|:--:|
| 1 | `feedback` | v1 | **6/10** |
| 2 | `feedback` | v2 | **10/10** |
| 3 | `query` (domínio) | v2 | **12/12** |

Os 4 itens que o v1 deixou implícitos — **`authLevel: "function"`**, **shape de erro `{ error: CODE, requestId }`**, **correlation id (`invocationId`)** e **teste de integração acompanhante** — foram **todos corrigidos no v2**. A rodada 3 confirmou a skill no caminho de resposta de domínio (`source_document`, `response-builder.ts`, camada `services`).

**Lição:** um agente capaz cumpre o explícito e raciocina sobre exceções (pulou `source_document` no feedback, corretamente); o valor da skill prescritiva está em **codificar o que o modelo não adivinha** (authLevel, contrato de erro, correlação, teste) e em apontar a **rede determinística** para o que é crítico (lint contra `anonymous`, teste exigindo `requestId`).

---

## Rastreabilidade às decisões do cenário 1

| Elemento da skill | Origem |
|---|---|
| Azure OpenAI GPT-4o, camada `services` para chamada ao modelo | [ADR-0001](../../cenario-1/exercicio-1-1/ADR-0001-escolha-modelo-llm.md) / [ADR-0004](../../cenario-1/exercicio-1-1/ADR-0004-build-vs-buy-pipeline-rag.md) |
| Context budget citado no contexto da skill | [ADR-0002](../../cenario-1/exercicio-1-1/ADR-0002-gerenciamento-contexto.md) |
| `source_document` / vigência como guardrail de rastreabilidade | [ADR-0003](../../cenario-1/exercicio-1-1/ADR-0003-documentos-contraditorios.md) |
| Estrutura `src/functions/<nome>/`, `skills/domain/`, `tests/integration/` | [Anexo C](../../../praticas/pratica-2/exercicios-2/anexo-c-estrutura-repositorio.md) |

---

## Atendimento aos critérios de avaliação (skill TL 2.3)

- **SKILL.md com código real** → DO/DON'T em TypeScript, snippets canônicos de validator/handler, anti-padrões com o porquê. (SKILL-v2)
- **Teste real com Copilot** → 3 gerações reais de agente isolado, com outputs literais e análise seguido/ignorado. (rodadas 1–3)
- **Iteração documentada** → v1→v2 com placar 6/10→10/10→12/12 e diagnóstico por item. (analise-v1, teste-rodada-2)
- **Critérios de maturidade práticos** → estágios + 7 critérios mensuráveis + métricas de acompanhamento contínuo. (criterios-maturidade)
- **Skills são artefatos vivos** → demonstrado: a v1 "parecia pronta" mas o teste real revelou 4 buracos; maturidade vem do loop empírico.

## Evidência de uso das ferramentas

- **Claude (chat):** redigiu a SKILL (v1/v2), a análise, os critérios de maturidade; cruzou ADRs/Anexo C.
- **GitHub Copilot / agente de codegen:** gerou os endpoints e testes das 3 rodadas a partir do SKILL.md. A evidência é a **saída real** dos agentes, não só o arquivo da skill.

> **Nota de transparência:** o GitHub Copilot não é conectável neste ambiente CLI; o agente de codegen ocupa seu papel funcional. O requisito da rubrica — **teste real com geração/avaliação/reescrita** — está plenamente atendido (3 gerações reais, cegas à resposta esperada).
