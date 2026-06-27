# Cenário 3 — Exercício 3.2 (TECH LEAD): Revisão crítica da arquitetura gerada com IA

**Papel:** Tech Lead
**Tópico:** Revisão Crítica de Outputs de IA
**Ferramenta:** Claude (chat)
**Fonte:** [cenario-3-exercicios-fase-governanca.md](../../../praticas/pratica-3/exercicios-3/cenario-3-exercicios-fase-governanca.md) — seção TECH LEAD, Exercício 3.2

---

## O que o exercício pedia

1. Fazer a **própria avaliação de riscos ANTES de usar o Claude**. Para cada artefato gerado com IA: qual o risco de ter sido gerado por IA, e o que verificar antes do go-live.
2. Usar o **Claude como co-reviewer** e comparar as listas.
3. **Priorizar**: dado que há 2 semanas, o que verificar primeiro? O que aceitar como risco residual?

**Artefatos:** AGENTS.md (refinado 4×, 15 págs); 3 skills (Foundation refinada, 2 sem refino); pipeline + query endpoint (~60–70% Copilot); system prompt (6 iterações sem changelog).

---

## Entregável

| Arquivo | Conteúdo |
|---------|----------|
| [revisao-riscos.md](revisao-riscos.md) | **Parte 1** — minha avaliação independente (antes do Claude), por artefato, com severidade. **Parte 2** — complementação do Claude (riscos adicionais). **Parte 3** — comparação honesta humano×Claude. **Parte 4** — priorização das 2 semanas + risco residual explícito. |

---

## Atendimento aos critérios de avaliação

| Critério (rubrica TL 3.2) | Onde é atendido |
|---|---|
| **Skills sem refinamento = risco** | Parte 1.B — Severidade Alta; padrão de codegen não validado pode propagar inconsistência (ex.: `jest` vs Vitest); ligado ao incidente do módulo de feedback. |
| **Prompt sem changelog = risco de governança** | Parte 1.D — 6 iterações sem registro = rollback informado impossível; viola a convenção do `prompt-changelog.md` do Anexo C. |
| **Análise própria ANTES do Claude** | Parte 1 é integralmente independente; Parte 2 (Claude) vem depois e a Parte 3 mostra o que era meu vs. o que ele acrescentou. |
| **Priorização pragmática** | Parte 4 — sequência Semana 1/2 ordenada por redução de risco; risco residual aceito de forma explícita (AGENTS.md bloat, código Copilot fora do caminho de resposta, automation bias). |
| **Comparação com Claude honesta** | Parte 3 — reconhece **2 riscos que eu não vi** (golden dataset não validado; risco de composição fim-a-fim) e 1 de processo (automation bias). Não é "já sabia tudo". |

---

## Conexão com os artefatos dos cenários 1 e 2 (D5)

- **ADR-0002** (context budget) e **ADR-0003** (documentos contraditórios, PROC-042 vs v2) — usadas como critério de review do código Copilot.
- **AGENTS.md / hierarquia de skills Foundation→Domain→Artifact** (Anexo C) — base para testar as skills não refinadas.
- **`/prompts/prompt-changelog.md` e `/prompts/eval/golden-queries.json`** (Anexo C) — convenções do projeto usadas na priorização.
- **Harness do Exercício 3.1** — o HITL para mudanças de prompt/base e para respostas suspeitas é a mitigação do risco residual.

---

## Evidência de uso da ferramenta (D2)

- **Claude (chat):** usado como **co-reviewer na ordem correta** — minha avaliação foi feita primeiro (Parte 1), depois o Claude foi consultado com prompt específico (*"que riscos eu deixei passar?"*), e o resultado foi confrontado criticamente (Parte 3), incorporando o que era válido (golden dataset, review fim-a-fim) na priorização.
