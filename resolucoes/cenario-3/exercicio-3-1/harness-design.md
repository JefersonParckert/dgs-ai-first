# Design do Harness — NovaTech Assistant

> **Cenário 3 — Exercício 3.1 (Tech Lead) · Tópico: Harness Engineering**
> **Ferramentas:** Claude (chat) para o design das 5 camadas; GitHub Copilot para a função de verificação (`source-verification.ts`).
> **Objetivo:** descrever o harness que envolve o assistente — o que separa um protótipo de um sistema de produção governável.

O harness é o conjunto de verificações e limites em torno do LLM. O modelo é **probabilístico**; o harness é a **rede determinística** que torna o comportamento previsível e auditável. Abaixo, as 5 camadas. Para cada uma: **o que já está implementado**, **o que falta** e **como fechar o gap**.

Legenda de prioridade para a demo da diretoria (2 semanas): 🔴 bloqueante · 🟡 desejável.

---

## Camada 1 — Tool Orchestration
*Coordenação de ingestão, retrieval e geração.*

| | |
|---|---|
| **O que já está** | Pipeline de ingestão processa os 847 documentos e indexa no Azure AI Search. Query endpoint (`src/functions/query/`) recebe POST, dispara retrieval e geração via `src/services/search.ts` + `completion.ts`, e monta a resposta em `response-builder.ts`. Bot do Teams em staging com 5 atendentes-piloto. Arquitetura de 4 componentes definida no AGENTS.md (pipeline / API / bot / web). |
| **O que falta** | Orquestração resiliente: retry com *exponential backoff* nas chamadas Azure (Search/OpenAI) está no AGENTS.md como regra, mas precisa estar de fato no código. Não há *circuit breaker* nem *timeout* explícito por etapa, nem *fallback* quando o Search retorna zero chunks. |
| **Como fechar o gap** | 🔴 Implementar retry+timeout em `search.ts`/`completion.ts` (a regra já existe no AGENTS.md; falta a implementação). 🔴 Definir o fluxo determinístico do handler: `validar input (Zod) → retrieval → montar prompt (dentro do budget) → completion → verificar output → responder ou rotear HITL`. 🟡 *Circuit breaker* para degradar para "não consigo responder agora" em vez de erro 500. |

---

## Camada 2 — Verification Loops
*Verificação automática de outputs: a fonte é válida? O schema do structured output foi respeitado?*

| | |
|---|---|
| **O que já está** | Nada determinístico em produção — a confiabilidade depende inteiramente do prompt (probabilístico), e os testes internos mostraram **12% de respostas incorretas** (alucinação, doc desatualizado, chunk errado). O módulo `src/services/response-validator.ts` existe no scaffold mas está vazio. |
| **O que falta** | (a) Validação do structured output contra schema Zod antes de qualquer checagem de conteúdo. (b) Verificação de que a fonte citada existe na base. (c) Detecção de uso de fonte não confiável (FAQ informal) para temas críticos. |
| **Como fechar o gap** | 🔴 **Entregue neste exercício:** `source-verification.ts` — função determinística que confirma se `source_document` está na lista de documentos válidos da NovaTech (`POL-001`, `PROC-042`, `PROC-042-v2`, `SLA-2024`, `FAQ-Atendimento`). Fonte inexistente → resposta marcada como **suspeita** → roteada para HITL. Testada com 11 casos no Vitest (ver `source-verification.test.ts`). 🟡 Próximos loops: validação de schema Zod (parceria com Dev 3.1) e flag de "fonte = FAQ informal em tema crítico" como confiança rebaixada. |

> **Por que determinístico e não só prompt:** "sempre cite uma fonte válida" no system prompt reduz, mas não elimina, citações inválidas — o modelo às vezes inventa um ID plausível. A função do exercício transforma isso em uma garantia binária e auditável: a resposta com fonte inválida **não chega ao atendente** sem revisão.

---

## Camada 3 — Context & Memory
*Manutenção de contexto entre interações, respeitando o context budget da **ADR-0002**.*

Esta camada **não reinventa** a estratégia de contexto — ela operacionaliza a [ADR-0002 (Gerenciamento de Contexto)](../../cenario-1/exercicio-1-1/ADR-0002-gerenciamento-contexto.md), decidida no cenário 1 e já codificada como regra dura no AGENTS.md.

| | |
|---|---|
| **O que já está** | A ADR-0002 define o **orçamento por query** (~9.800 tokens: system ~2.000, metadados ~500, chunks ~4.000 com **máx. 8 chunks × 500**, histórico comprimido ~1.500, pergunta ~300, buffer ~1.500), a **recuperação multi-domínio** (até 3 chunks/domínio quando a pergunta cruza SLA/Frete/Devolução), o tratamento de **lost-in-the-middle** (chunks relevantes no início, pergunta no fim) e a **gestão de context rot** (janela deslizante + compressão semântica a partir do turno 4; reset por baixa similaridade < 0.3 ou por volume > 1.500 tokens). O AGENTS.md replica esses limites como contrato para o `prompt-builder.ts`. |
| **O que falta** | A garantia hoje é **documental**, não executável: o `prompt-builder.ts` deve respeitar o budget, mas nada falha o build se ele estourar. A análise do cenário 2 já apontou que o context budget foi o único item não-pleno nas duas rodadas de teste do AGENTS.md. |
| **Como fechar o gap** | 🔴 Teste determinístico que conta tokens do prompt montado e **falha** se exceder o budget da ADR-0002 (máx. 8 chunks, histórico ≤ 3 turnos). 🟡 Assertiva de ordem (lost-in-the-middle): chunk de maior score na primeira posição. 🟡 Métrica de quantos resets de sessão ocorrem (sinal de falsos positivos do gatilho de similaridade). A memória de sessão do Teams segue a janela deslizante da ADR-0002 — sem persistência além da sessão (privacidade). |

---

## Camada 4 — Guardrails
*Limites que o sistema não pode ultrapassar: structured outputs + código (determinísticos) e prompt (probabilísticos), com pontos de human-in-the-loop.*

| | |
|---|---|
| **O que já está** | Guardrails de produto formalizados no cenário 2 (DEVE / NÃO DEVE / QUANDO EM DÚVIDA). Regra de `source_document` obrigatório expressa no schema de output do AGENTS.md. Mas hoje a resposta é **texto livre**: quando o modelo "esquece" a fonte, nada impede a resposta de seguir. |
| **O que falta** | (a) **Structured output** efetivo: forçar a resposta em JSON `{ answer, source_document, confidence_score }` validado por Zod, rejeitando o que não bate com o formato antes de checar conteúdo. (b) Guardrail determinístico de "carga perigosa + devolução DEVE conter a negativa" (POL-001 §3.2). (c) Roteamento HITL definido por risco. |
| **Como fechar o gap** | **Structured outputs:** 🔴 adotar o schema Zod `QueryResponse` (parceria Dev 3.1) — resposta que não valida é rejeitada e substituída por mensagem padrão segura. A camada 2 (verification) checa o *conteúdo* dos campos depois que o *formato* foi garantido aqui. **Determinísticos via código:** 🔴 a função `source-verification.ts` deste exercício é um guardrail desta camada; 🔴 bloqueio de "carga perigosa devolvível" (Dev 3.1). **Probabilísticos via prompt:** system prompt reforça nunca inventar, sempre citar, responder em PT formal. |

### Pontos de Human-in-the-Loop (HITL)

O HITL é acionado por **risco da decisão**, não por todas as respostas (isso inviabilizaria o ganho de produtividade). Pontos concretos:

1. **🔴 Baixa confiança em tema sensível → revisão obrigatória.** Resposta com `confidence_score = baixa` **OU** marcada como suspeita pela camada 2 (fonte inválida/ausente), sobre **carga perigosa, sinistro/dano, ou exceção de SLA contratual**, **não vai direto ao atendente**: entra numa fila de revisão e um **supervisor de atendimento** aprova/corrige antes de liberar. Justificativa de domínio: carga perigosa tem exceção legal (POL-001 §3.2) e o FAQ informal contradiz a regra formal (FAQ-03) — é exatamente onde uma alucinação confiante causa dano.
2. **🔴 Mudança no system prompt ou na base documental → aprovação do Tech Lead** antes de produção (conecta com o harness de produto, PS 3.2): nenhuma alteração que afete o comportamento do assistente sobe sem revisão humana e registro no `prompt-changelog.md`.
3. **🟡 Fonte = FAQ informal em tema crítico → revisão.** O FAQ-Atendimento não é validado por Compliance; resposta crítica baseada nele é rebaixada para revisão.

---

## Camada 5 — Observability
*Logs, métricas e alertas — visibilidade do que acontece em produção.*

| | |
|---|---|
| **O que já está** | `pino` via `src/shared/logger.ts` padronizado no AGENTS.md (proibido `console.log`). Logs estruturados com `requestId`/`route` no handler canônico. |
| **O que falta** | Métricas de qualidade e negócio, e alertas com threshold. Não há painel nem rastreabilidade fim-a-fim de uma query (retrieval → chunks usados → resposta → veredito da verificação → feedback). |
| **Como fechar o gap** | 🔴 Logar, por query: `requestId`, domínios detectados, IDs dos chunks recuperados, `confidence_score`, **veredito da `source-verification` (`suspicious`/`isValid`/`reason`)**, e se houve roteamento HITL. 🔴 Alerta determinístico: "% de respostas suspeitas (fonte inválida) > 5% em 24h → notificar o time". 🟡 Dashboard com taxa de feedback negativo, latência, % de escalações e documentos mais consultados (alinhado à observabilidade do DM 3.2). **Nunca logar dado pessoal do atendente** (e-mail/nome) — regra do AGENTS.md. |

---

## Resumo: o que a camada de Verification Loops entrega neste exercício

A função `verifySourceDocument` (em [`source-verification.ts`](source-verification.ts)) é a verificação implementada da camada 2:

- Recebe o `source_document` da resposta do modelo.
- Extrai o **identificador curto** (lida com citações como `"POL-001, seção 3.2"` e `"FAQ-Atendimento, item 32"`).
- Compara por **igualdade exata** (case-insensitive) contra a lista de documentos válidos — **nunca por prefixo** (`PROC-042` é prefixo de `PROC-042-v2`; um `startsWith` aceitaria um `PROC-042-v9` inexistente).
- Marca a resposta como **suspeita** quando a fonte é inválida, ausente, ou literal como `"Nenhuma"` — disparando o HITL da camada 4.
- É **pura e determinística** (sem efeitos colaterais); o log (pino) e o roteamento acontecem no call site.

Validada com **11 testes Vitest** (todos passando) — ver [`source-verification.test.ts`](source-verification.test.ts) e a evidência de execução no [README](README.md).
