# Análise — o que o agente seguiu e o que ignorou (SKILL-v1)

Checklist único de 12 itens (mesma régua nas duas rodadas; itens N/A não contam no placar).

| # | Critério da skill / projeto | Explícito no v1? | Seguiu? | Evidência no output real |
|---|------------------------------|:----------------:|:-------:|--------------------------|
| 1 | Azure Functions v4 (`app.http`) | sim | ✅ | `app.http("feedback", {...})` |
| 2 | Validação de input com Zod | sim | ✅ | `FeedbackRequest.parse(...)` |
| 3 | Sem `any` (tipos via `z.infer`) | sim | ✅ | `type FeedbackRequest = z.infer<...>` |
| 4 | pino via `shared/logger`, sem `console.log` | sim | ✅ | `logger.warn/info/error`, zero `console.log` |
| 5 | Erros: 400 input / 500 interno | sim | ✅ | 400 no ZodError, 500 no catch interno |
| 6 | Split `handler.ts` / `validator.ts` | sim | ✅ | dois arquivos nos caminhos certos |
| 7 | Chamar modelo só via `src/services/` | sim | ➖ N/A | feedback não chama modelo (correto) |
| 8 | **`authLevel: "function"`** (segurança) | **não** | ❌ | omitido → default `anonymous` (endpoint aberto) |
| 9 | **Shape de erro canônico `{ error: CODE, requestId }`** | **não** | ❌ | usou strings livres `"invalid request"` / `"internal error"` |
| 10 | **Correlation id (`context.invocationId`) em log e resposta** | **não** | ❌ | `context` recebido mas nunca usado; sem requestId |
| 11 | **Teste de integração acompanhando o endpoint** | **não** | ❌ | nenhum teste gerado |
| 12 | `source_document` quando há resposta de domínio | sim | ➖ N/A | feedback não tem resposta de domínio (corretamente pulado) |

**Placar v1:** itens aplicáveis = 10 (1–6, 8–11). ✅ = 6 · ❌ = 4 → **6/10**.

## Diagnóstico (consistente com o aprendido nos exercícios 2.1)
Um agente capaz **cumpre o que está escrito explicitamente** (Zod, pino, sem `any`, split, 400/500, v4 — todos ✅) e ainda **raciocina sobre exceções** (pulou `source_document`/services por não se aplicarem ao feedback). Os erros estão **exatamente onde o v1 foi omisso**:

1. **`authLevel` (item 8):** o v1 nunca menciona — o agente caiu no default `anonymous`, deixando o endpoint **aberto**. É a falha mais grave (segurança) e 100% causada pela omissão da skill.
2. **Shape de erro (item 9):** sem um padrão canônico, o agente inventou strings (`"invalid request"`). Sem código de erro estável nem `requestId`, quebra a integração com o cliente e a correlação em logs.
3. **Correlation id (item 10):** o `context` é recebido mas o `invocationId` nunca entra no log/resposta — impossível rastrear uma chamada ponta a ponta. O v1 não pediu.
4. **Teste de integração (item 11):** a skill não diz que "todo endpoint nasce com teste", então nenhum teste veio. Para uma skill de *Domain* que governa a criação de endpoints, isso é um buraco.

## Alvos da iteração para o v2
Transformar os 4 itens omissos em **instrução acionável**: snippet canônico de handler com `requestId` + shape de erro `{ error, requestId }`, `authLevel: "function"` explícito, exigência de teste de integração acompanhando (com dependência na skill `testing-patterns`/`create-integration-test`), anti-padrões ampliados (authLevel anonymous, erro como string solta, `context` ignorado) e um **checklist de autovalidação**.

> **Limite reconhecido:** mesmo no v2, regras críticas de segurança/contrato devem ter rede determinística (lint que proíbe `authLevel: "anonymous"`, teste que exige `requestId` na resposta de erro) — prompt/skill é probabilístico.
