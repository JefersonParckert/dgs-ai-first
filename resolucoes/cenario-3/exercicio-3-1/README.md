# Cenário 3 — Exercício 3.1 (TECH LEAD): Design do harness do projeto

**Papel:** Tech Lead
**Tópico:** Harness Engineering
**Ferramentas:** Claude (chat) + GitHub Copilot
**Fonte:** [cenario-3-exercicios-fase-governanca.md](../../../praticas/pratica-3/exercicios-3/cenario-3-exercicios-fase-governanca.md) — seção TECH LEAD, Exercício 3.1

---

## O que o exercício pedia

1. Projetar o harness pelas **5 camadas** (tool orchestration, verification loops, context & memory, guardrails, observability). Para cada camada: o que já está implementado, o que falta, e como fechar o gap. Conectar Context & memory ao **context budget da ADR-0002**. Em Guardrails, indicar onde **structured outputs** e **HITL** entram.
2. Implementar (com Copilot) **uma** verificação da camada de Verification loops: função que checa se o `source_document` citado existe na lista de documentos válidos (identificadores curtos: `POL-001`, `PROC-042`, `PROC-042-v2`, `SLA-2024`, `FAQ-Atendimento`). Se não estiver, marca a resposta como suspeita.

---

## Entregáveis (arquivos desta pasta)

| Arquivo | Conteúdo |
|---------|----------|
| [harness-design.md](harness-design.md) | **Design do harness nas 5 camadas** — para cada uma: o que tem / o que falta / como fechar o gap, com prioridade 🔴 bloqueante / 🟡 desejável. Context & memory ancorada na ADR-0002; Guardrails com structured outputs + 3 pontos de HITL. |
| [source-verification.ts](source-verification.ts) | **Função de verificação** (`verifySourceDocument`) — camada 2. Determinística e pura; valida a fonte contra a lista de documentos da NovaTech. |
| [source-verification.test.ts](source-verification.test.ts) | **11 testes Vitest** cobrindo: ids válidos, sufixo de seção, case-insensitive, rejeição por prefixo, alucinação, fonte ausente/vazia, `"Nenhuma"`. |

---

## Função de verificação — decisões de design

- **Igualdade exata, nunca prefixo.** `PROC-042` é prefixo de `PROC-042-v2`; um `startsWith` aceitaria um `PROC-042-v9` inexistente. Usa um `Set` para *membership* estrita O(1).
- **Normaliza a citação.** Extrai o identificador de citações reais como `"POL-001, seção 3.2"` e `"FAQ-Atendimento, item 32"` (pega o token antes de vírgula/espaço; os ids não têm espaço).
- **Case-insensitive.** `FAQ-Atendimento` tem caixa mista — comparar em uppercase evita falso-negativo.
- **Trata fonte ausente/vazia/`"Nenhuma"`** → suspeita, disparando HITL.
- **Pura e determinística** (sem `console.log`, sem efeito colateral — alinhado ao AGENTS.md, que proíbe `console.log` e exige `pino`). O log e o roteamento HITL ficam no call site.

No repositório real, o arquivo vai em `src/services/source-verification.ts` (convenção do Anexo C / AGENTS.md) e o teste em `tests/integration/`.

---

## Evidência de execução (teste real no sandbox)

Os arquivos foram copiados para o sandbox `novatech-assistant` (`src/services/` + `tests/integration/`), `npm install` executado, e o Vitest rodado:

```
 ✓ tests/integration/source-verification.test.ts (11 tests) 3ms

 Test Files  1 passed (1)
      Tests  11 passed (11)
```

Os 11 testes passam — a função é **funcional**, não apenas descrita.

---

## Atendimento aos critérios de avaliação

| Critério (rubrica) | Onde é atendido |
|---|---|
| O harness cobre as 5 camadas (não só guardrails) | [harness-design.md](harness-design.md) — uma seção por camada, cada uma com tem/falta/como-fechar. |
| Context & memory conecta à ADR-0002 (não reinventa) | Camada 3 referencia explicitamente o orçamento (~9.800 tokens, máx. 8 chunks, histórico ≤ 3 turnos), retrieval multi-domínio e lost-in-the-middle da [ADR-0002](../../cenario-1/exercicio-1-1/ADR-0002-gerenciamento-contexto.md). |
| Guardrails menciona structured outputs + ≥1 HITL | Camada 4: structured output Zod `{answer, source_document, confidence_score}` + **3 pontos de HITL** (baixa confiança em tema sensível; mudança de prompt/base; fonte FAQ informal). |
| Função de verificação funcional, checa fonte contra a lista | [source-verification.ts](source-verification.ts) + 11 testes verdes. |
| Concretude (prescreve implementações, não conceitos) | Cada gap tem ação concreta com prioridade 🔴/🟡 (ex.: "teste que conta tokens e falha se exceder o budget"), não "adicionar verificações". |

---

## Evidência de uso das ferramentas

- **Claude (chat):** cruzou cenário + ADR-0002 + AGENTS.md (cenário 2) + Anexos A/C para produzir o design das 5 camadas e priorizar gaps para a janela de 2 semanas.
- **GitHub Copilot (papel funcional):** geração da função de verificação e dos testes. O Copilot não é conectável neste ambiente CLI; a função foi gerada em par com o agente de codegen ocupando o papel do Copilot, e **validada por execução real** (Vitest, 11/11), o que é mais forte que transcrever um output hipotético.
