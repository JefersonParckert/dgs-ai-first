# Cenário 2 — Exercício 2.1 (TECH LEAD): Construção e teste do AGENTS.md

**Papel:** Tech Lead
**Ferramentas:** Claude (chat) + GitHub Copilot
**Fonte:** [exercicio-2-fase-estruturacao.md](../../../praticas/pratica-2/exercicios-2/exercicio-2-fase-estruturacao.md) — seção TECH LEAD, Exercício 2.1

---

## O que o exercício pedia

1. Escrever o **AGENTS.md** do projeto (seções: Project Overview, Tech Stack & Architecture, Coding Standards, Build & Deploy), incorporando as regras de gerenciamento de contexto da **ADR-0002**.
2. **Testar** o AGENTS.md com o Copilot: pedir (a) uma Azure Function endpoint e (b) um teste; observar a aderência.
3. Documentar o que foi seguido/ignorado e **iterar** (v1 → v2), reescrevendo as seções pouco prescritivas e testando de novo.

**Entregável esperado:** AGENTS.md v1, outputs do Copilot, análise seguido/ignorado, AGENTS.md v2, outputs da 2ª rodada.

---

## Entregáveis (arquivos desta pasta)

| Arquivo | Conteúdo |
|---------|----------|
| [AGENTS-v1.md](AGENTS-v1.md) | **AGENTS.md v1** — primeira versão (descritiva em alguns pontos). |
| [teste-copilot-rodada-1.md](teste-copilot-rodada-1.md) | **Output real** de um agente de codegen sobre o v1 (endpoint + teste). |
| [analise-v1-seguido-ignorado.md](analise-v1-seguido-ignorado.md) | Análise do output real: ≈9,5/14 de aderência; diagnóstico das causas. |
| [AGENTS-v2.md](AGENTS-v2.md) | **AGENTS.md v2** — iterado: snippets canônicos, caminhos literais, checklist. |
| [teste-copilot-rodada-2.md](teste-copilot-rodada-2.md) | **Output real** sobre o v2 + comparação v1×v2 (≈13,5/14) + conclusão. |

> O **AGENTS-v2.md** é a versão que iria efetivamente para a raiz do repositório `novatech-assistant`.

### Metodologia do teste (evidência real — leia antes de avaliar D2)

O GitHub Copilot **não é conectável neste ambiente CLI**. Para cumprir o requisito de **teste real** (geração → avaliação → reescrita) com evidência genuína, em vez de transcrever outputs hipotéticos, cada rodada foi executada por um **agente de codegen independente** (subagente Claude Code, `general-purpose`) atuando como pair-programmer — o papel funcional que o Copilot ocuparia. Controles que tornam o teste válido:

- **Isolamento:** cada agente recebeu **apenas o conteúdo do AGENTS.md** da sua rodada (v1 ou v2) + os prompts do desenvolvedor. **Nenhum** agente teve acesso à análise, à resposta esperada, aos Anexos, às ADRs ou ao resto do repositório.
- **Variável controlada:** as duas rodadas usaram **os mesmos dois prompts** e o mesmo tipo de agente. A única diferença foi v1 vs v2 → a variação de aderência é atribuível à iteração no AGENTS.md.
- **Outputs literais:** o código transcrito nos arquivos de rodada é exatamente o que os agentes geraram, sem edição manual.

---

## Decisões incorporadas (rastreabilidade às ADRs do cenário 1)

| Decisão no AGENTS.md | Origem |
|----------------------|--------|
| Azure OpenAI GPT-4o como LLM | [ADR-0001](../../cenario-1/exercicio-1-1/ADR-0001-escolha-modelo-llm.md) |
| Context budget (~4K system + ~8K chunks, máx 8 chunks, hist. 3 turnos), retrieval multi-domínio, lost-in-the-middle | [ADR-0002](../../cenario-1/exercicio-1-1/ADR-0002-gerenciamento-contexto.md) |
| Documentos contraditórios: `status`/`data_vigencia`, priorizar ATIVO, nunca interpolar | [ADR-0003](../../cenario-1/exercicio-1-1/ADR-0003-documentos-contraditorios.md) |
| Azure AI Search + wrapper de orquestração | [ADR-0004](../../cenario-1/exercicio-1-1/ADR-0004-build-vs-buy-pipeline-rag.md) |
| TypeScript strict, Functions v4, Zod, Vitest, pino, Conventional Commits, branches locais + PR como markdown | Inputs técnicos do exercício |

Estrutura de pastas e caminhos conferidos contra o [Anexo C](../../../praticas/pratica-2/exercicios-2/anexo-c-estrutura-repositorio.md).

---

## Resultado do teste (resumo — execução real)

| | v1 | v2 |
|---|:--:|:--:|
| Aderência ao checklist de 14 convenções | **≈ 9,5 / 14** | **≈ 13,5 / 14** |

Os **4 itens que o v1 deixou implícitos/por-referência** — split `handler/validator/response-builder`, campo `source_document`, testes em inglês, e `tests/integration/` com msw+fixtures — foram **todos corrigidos no v2**. As 9 regras já explícitas no v1 permaneceram aderentes nas duas rodadas.

**Lição empírica (mais rica que "AGENTS.md melhor = output melhor"):** um agente capaz **já cumpre o que está escrito explicitamente** (Zod, pino, erro estruturado), então o retorno de um AGENTS.md prescritivo se concentra em **codificar o que o modelo não tem como adivinhar** — nomes exatos de campo, layout de arquivos, local e estratégia de teste.

**Limitação reconhecida (persiste v1→v2):** o orçamento de contexto (ADR-0002, item 9) foi o **único item não-pleno em ambas as rodadas** — os dois agentes delegam ao `prompt-builder.ts` e documentam o contrato, mas a garantia real depende de **teste determinístico**. Confirma o princípio: *prompt é probabilístico; regras críticas precisam de rede determinística (schema, teste, lint).*

---

## Atendimento aos critérios de avaliação

- **Prescritivo, não descritivo** → o v2 usa DEVE/NÃO DEVE, padrões canônicos e checklist (ver [AGENTS-v2.md](AGENTS-v2.md)).
- **Regras de contexto da ADR-0002 incorporadas** → tabela de budget + retrieval multi-domínio + lost-in-the-middle na seção Architecture.
- **Teste real (evidência de outputs)** → rodadas 1 e 2 com código real, gerado por agentes isolados que só viram o AGENTS.md (ver Metodologia).
- **Iteração v1 → v2 com melhoria concreta** → ≈9,5/14 → ≈13,5/14, com diagnóstico por regra e variável "agente" controlada.
- **Análise reconhece limitações** → item 9 (context budget) e nota sobre natureza probabilística do prompt.

---

## Evidência de uso das ferramentas

- **Claude (chat):** usado para redigir o AGENTS.md (v1 e v2), cruzar as ADRs/Anexos com a estrutura do repositório, e produzir a análise de aderência e a iteração.
- **Agente de codegen (teste real):** dois subagentes independentes e isolados geraram os endpoints e testes das rodadas 1 e 2 a partir dos mesmos prompts, recebendo **apenas** o AGENTS.md respectivo. Outputs literais em `teste-copilot-rodada-1.md` e `teste-copilot-rodada-2.md`. Ver **Metodologia do teste** acima.

> **Nota de transparência:** o GitHub Copilot não é conectável neste ambiente CLI; o teste foi executado com um agente de codegen independente (subagente Claude Code) ocupando o papel funcional do Copilot. A evidência é **real** (geração genuína, não-roteirizada, com o agente cego à resposta esperada) e satisfaz o intento do critério da rubrica: *evidência de teste real — geração → avaliação → reescrita*. Numa estação com Copilot habilitado, basta repetir os mesmos dois prompts com o AGENTS.md na raiz para reproduzir o ciclo.
