# Teste da Skill — Rodada 3 (SKILL-v2, alvo `query`) — EXECUÇÃO REAL

> **Por que esta rodada existe:** o alvo `feedback` (rodadas 1–2) **não tem resposta de domínio**, então não exercitou as regras 2 (output Zod), 9 (`source_document`), 8 (`response-builder.ts`) e 10 (serviços). Esta 3ª geração usa um alvo **com resposta de domínio** (`query`), validando a skill no caminho completo — e fechando o critério de maturidade #1 (≥3 gerações, ≥2 alvos).
> Agente isolado, recebendo **apenas** o `SKILL-v2.md`. Output literal (resumido nos pontos que repetem o padrão já mostrado na rodada 2).

## Prompt
> "Generate the `POST /api/query` endpoint. Recebe a pergunta do atendente, busca na base, chama o modelo, e retorna a resposta do assistente COM a fonte citada. Follow the azure-functions-endpoint skill."

## Arquivos gerados (caminhos)
- `src/functions/query/validator.ts` — `QueryRequest` **e** `QueryResponse` (com `source_document`).
- `src/functions/query/response-builder.ts` — valida o output com `QueryResponse.parse(...)`.
- `src/services/query-service.ts` — busca + montagem de prompt + chamada ao modelo (fora do handler).
- `src/functions/query/handler.ts` — orquestra; `authLevel: "function"`; `requestId`; erros canônicos.
- `tests/integration/query.test.ts` — caminho feliz (200 com `source_document`), 400, 500.

## Trechos-chave (output real)
```typescript
// validator.ts — output validado com Zod, source_document obrigatório (Regras 2 e 9)
export const QueryResponse = z.object({
  answer: z.string(),
  source_document: z.string(),
});
export type QueryResponse = z.infer<typeof QueryResponse>;
```
```typescript
// response-builder.ts — valida o output antes de retornar
export function buildQueryResponse(result: QueryResult): QueryResponse {
  return QueryResponse.parse({ answer: result.answer, source_document: result.source_document });
}
```
```typescript
// handler.ts — handler NÃO chama o modelo; delega a src/services (Regra 10)
const result = await answerQuestion(input.question, requestId);
const body = buildQueryResponse(result);
return { status: 200, jsonBody: body };
```
```typescript
// query.test.ts — caminho feliz exige answer + source_document citado
expect(res.jsonBody).toEqual({
  answer: "Reset the router by holding the power button for 10 seconds.",
  source_document: "kb/router-troubleshooting.md",
});
```

## Aderência (checklist de 12 itens, alvo com domínio → todos aplicáveis)

| # | Critério | query (v2) |
|---|----------|:----------:|
| 1 | Functions v4 | ✅ |
| 2 | Zod input **+ output** | ✅ |
| 3 | Sem `any` | ✅ |
| 4 | pino, sem console.log | ✅ |
| 5 | Erros 400/500 | ✅ |
| 6 | Split handler/validator/**response-builder** | ✅ |
| 7 | **Modelo só via services** | ✅ |
| 8 | authLevel "function" | ✅ |
| 9 | shape de erro `{ error, requestId }` | ✅ |
| 10 | requestId em log+erro | ✅ |
| 11 | teste de integração (feliz/400/500) | ✅ |
| 12 | **source_document** (resposta de domínio) | ✅ |

**Placar query (v2): 12/12** (todos os itens aplicáveis, incluindo os 4 específicos de domínio que o feedback não testava).

## Conclusão das 3 rodadas

| Rodada | Alvo | Skill | Aderência |
|---|---|:--:|:--:|
| 1 | feedback | v1 | 6/10 |
| 2 | feedback | v2 | 10/10 |
| 3 | query | v2 | 12/12 |

A v2 se mostrou aderente em **2 alvos distintos**, incluindo o caminho de resposta de domínio. O ciclo *gerar → medir → reescrever → re-testar* produziu ganho real e a skill cobre agora tanto endpoints simples (feedback) quanto de domínio (query).
