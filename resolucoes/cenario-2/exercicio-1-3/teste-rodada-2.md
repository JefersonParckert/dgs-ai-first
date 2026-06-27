# Teste da Skill — Rodada 2 (sobre SKILL-v2) — EXECUÇÃO REAL

> **Metodologia:** segundo agente de codegen independente e isolado, **mesmo prompt** da rodada 1, recebendo **apenas** o `SKILL-v2.md`. Não viu a rodada 1 nem a análise. Variável "agente" controlada → a diferença é atribuível à iteração na skill. Output **literal** abaixo.

## Prompt (idêntico ao da rodada 1)
> "Generate the `POST /api/feedback` endpoint ... Follow the azure-functions-endpoint skill."

## Output real — `src/functions/feedback/validator.ts`
```typescript
import { z } from "zod";

export const FeedbackRequest = z.object({
  queryId: z.string().min(1),
  attendantId: z.string().min(1),
  reason: z.string().min(1),
});
export type FeedbackRequest = z.infer<typeof FeedbackRequest>;
```

## Output real — `src/functions/feedback/handler.ts`
```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { ZodError } from "zod";
import { logger } from "../../shared/logger";
import { FeedbackRequest } from "./validator";

export async function feedbackHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  const requestId = context.invocationId; // Regra 5
  try {
    const input = FeedbackRequest.parse(await request.json());
    logger.info(
      { requestId, route: "api/feedback", queryId: input.queryId, attendantId: input.attendantId },
      "feedback received"
    );
    return { status: 202, jsonBody: { status: "received", requestId } };
  } catch (err) {
    if (err instanceof ZodError) {
      logger.warn({ requestId, err }, "invalid input");
      return { status: 400, jsonBody: { error: "INVALID_INPUT", requestId } };
    }
    logger.error({ requestId, err }, "unhandled error");
    return { status: 500, jsonBody: { error: "INTERNAL_ERROR", requestId } };
  }
}

app.http("feedback", {
  methods: ["POST"],
  authLevel: "function",
  route: "api/feedback",
  handler: feedbackHandler,
});
```

## Output real — `tests/integration/feedback.test.ts`
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { HttpRequest, InvocationContext } from "@azure/functions";
import { feedbackHandler } from "../../src/functions/feedback/handler";

vi.mock("../../src/shared/logger", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

function makeContext(): InvocationContext {
  return { invocationId: "test-invocation-id" } as unknown as InvocationContext;
}
function makeRequest(body: unknown, opts?: { throwOnJson?: boolean }): HttpRequest {
  return {
    json: opts?.throwOnJson
      ? vi.fn().mockRejectedValue(new Error("boom"))
      : vi.fn().mockResolvedValue(body),
  } as unknown as HttpRequest;
}

describe("POST /api/feedback", () => {
  beforeEach(() => vi.clearAllMocks());

  it("caminho feliz: registra feedback e retorna requestId", async () => {
    const req = makeRequest({ queryId: "q-123", attendantId: "att-456", reason: "Resposta citou documento desatualizado." });
    const res = await feedbackHandler(req, makeContext());
    expect(res.status).toBe(202);
    expect(res.jsonBody).toEqual({ status: "received", requestId: "test-invocation-id" });
  });

  it("input inválido: retorna 400 INVALID_INPUT", async () => {
    const req = makeRequest({ queryId: "", attendantId: "att-456", reason: "" });
    const res = await feedbackHandler(req, makeContext());
    expect(res.status).toBe(400);
    expect(res.jsonBody).toEqual({ error: "INVALID_INPUT", requestId: "test-invocation-id" });
  });

  it("erro interno: retorna 500 INTERNAL_ERROR", async () => {
    const req = makeRequest(undefined, { throwOnJson: true });
    const res = await feedbackHandler(req, makeContext());
    expect(res.status).toBe(500);
    expect(res.jsonBody).toEqual({ error: "INTERNAL_ERROR", requestId: "test-invocation-id" });
  });
});
```

---

## Comparação real v1 × v2 (mesmo checklist de 12 itens)

| # | Critério | Rodada 1 (v1) | Rodada 2 (v2) |
|---|----------|:-------------:|:-------------:|
| 1 | Azure Functions v4 | ✅ | ✅ |
| 2 | Zod input (+output se domínio) | ✅ | ✅ |
| 3 | Sem `any` (z.infer) | ✅ | ✅ |
| 4 | pino, sem console.log | ✅ | ✅ |
| 5 | Erros 400/500 | ✅ | ✅ |
| 6 | Split handler/validator | ✅ | ✅ |
| 7 | Modelo só via services | ➖ N/A | ➖ N/A |
| 8 | **authLevel: "function"** | ❌ | ✅ |
| 9 | **shape de erro `{ error: CODE, requestId }`** | ❌ | ✅ |
| 10 | **requestId (invocationId) em log+erro** | ❌ | ✅ |
| 11 | **teste de integração (feliz/400/500)** | ❌ | ✅ |
| 12 | source_document se domínio | ➖ N/A (pulou certo) | ➖ N/A (pulou certo) |

**Placar:** v1 **6/10** → v2 **10/10** (itens aplicáveis: 1–6, 8–11).

### Por que melhorou
Os 4 itens que falharam no v1 eram **omissões da skill**. No v2 viraram instrução acionável:
- **Snippet canônico de handler** com `requestId` e shape de erro → o agente copiou literalmente (item 9, 10).
- **`authLevel: "function"` no exemplo + anti-padrão explícito** → endpoint deixou de nascer `anonymous` (item 8).
- **Regra 11 + dependência `create-integration-test`** → veio um teste com os 3 casos exigidos (item 11).
- O **Checklist de autovalidação** funcionou como verificação final (o agente listou nas notas que cumpriu authLevel, requestId, shapes e teste).

### Limitação reconhecida (persiste)
Segurança e contrato continuam sendo probabilísticos via skill. Recomendação: **rede determinística** — uma regra de ESLint que falhe em `authLevel: "anonymous"` e um teste de contrato que exija `requestId` nas respostas de erro. A skill **eleva a probabilidade**; o lint/teste **garante**.
