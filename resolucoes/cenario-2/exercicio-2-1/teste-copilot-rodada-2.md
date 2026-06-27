# Teste do AGENTS.md — Rodada 2 (sobre AGENTS-v2) — EXECUÇÃO REAL

> **Metodologia:** um **segundo agente de codegen independente** (mesmo tipo do da rodada 1, igualmente isolado) recebeu **apenas o conteúdo do `AGENTS-v2.md`** e os **mesmos dois prompts** da rodada 1. Não viu a rodada 1, a análise, nem qualquer resposta esperada. Variável "agente" controlada → a diferença observada é atribuível à iteração no AGENTS.md. Outputs literais abaixo.

---

## Prompt 1 (idêntico ao da rodada 1)

> "Generate an Azure Function HTTP trigger for the `POST /api/query` endpoint of the NovaTech Assistant. Follow the repository's AGENTS.md."

### Output real — `src/functions/query/validator.ts`

```typescript
import { z } from "zod";

export const QueryRequest = z.object({
  question: z.string().min(1).max(2000),
  clientTier: z.enum(["Gold", "Silver", "Standard"]).optional(),
  sessionId: z.string().uuid().optional(),
});
export type QueryRequest = z.infer<typeof QueryRequest>;

export const QueryResponse = z.object({
  answer: z.string(),
  source_document: z.string(), // OBRIGATÓRIO
  confidence: z.enum(["high", "low"]),
});
export type QueryResponse = z.infer<typeof QueryResponse>;

export function parseQueryRequest(input: unknown): QueryRequest {
  return QueryRequest.parse(input);
}

export function parseQueryResponse(input: unknown): QueryResponse {
  return QueryResponse.parse(input);
}
```

### Output real — `src/functions/query/response-builder.ts`

```typescript
import { QueryResponse, parseQueryResponse } from "./validator";
import type { RetrievedChunk } from "../../shared/types";
import type { CompletionResult } from "../../services/completion";

/**
 * Builds the validated endpoint response. The source_document field is
 * mandatory: it is derived from the most relevant retrieved chunk so the
 * assistant always cites its source.
 */
export function buildQueryResponse(
  completion: CompletionResult,
  topChunk: RetrievedChunk
): QueryResponse {
  const body = {
    answer: completion.answer,
    source_document: topChunk.source_document,
    confidence: completion.confidence,
  };

  // Validate output (Zod) before returning it to the caller.
  return parseQueryResponse(body);
}
```

### Output real — `src/functions/query/handler.ts`

```typescript
import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { logger } from "../../shared/logger";
import { ValidationError } from "../../shared/errors";
import { parseQueryRequest, QueryResponse } from "./validator";
import { buildQueryResponse } from "./response-builder";
import { search } from "../../services/search";
import { buildPrompt } from "../../services/prompt-builder";
import { complete } from "../../services/completion";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  const requestId = context.invocationId;
  try {
    const parsed = parseQueryRequest(await request.json());
    logger.info({ requestId, route: "api/query" }, "query received");

    // Retrieval: returns ranked chunks already filtered/scored per ADR-0003
    // (SUPERSEDIDO score x 0.1) with retry/backoff handled inside the service.
    const chunks = await search({
      question: parsed.question,
      clientTier: parsed.clientTier,
      requestId,
    });

    // Prompt assembly respects the context budget (ADR-0002):
    // system ~4k, max 8 chunks (~8k), history max 3 turns (~1.5k), question ~300.
    const prompt = buildPrompt({
      question: parsed.question,
      chunks,
      sessionId: parsed.sessionId,
      requestId,
    });

    // Completion: Azure OpenAI GPT-4o, retry with exponential backoff in-service.
    const completion = await complete({ prompt, requestId });

    const topChunk = chunks[0];
    const body: QueryResponse = buildQueryResponse(completion, topChunk);

    return { status: 200, jsonBody: body };
  } catch (err) {
    if (err instanceof ValidationError || (err as { name?: string })?.name === "ZodError") {
      logger.warn({ requestId, err }, "invalid input");
      return { status: 400, jsonBody: { error: "INVALID_INPUT", requestId } };
    }
    logger.error({ requestId, err }, "unhandled error");
    return { status: 500, jsonBody: { error: "INTERNAL_ERROR", requestId } };
  }
}

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  route: "api/query",
  handler: queryHandler,
});
```

---

## Prompt 2 (idêntico ao da rodada 1)

> "Generate a test for that endpoint. Follow the AGENTS.md."

### Output real — `tests/integration/query.test.ts`

```typescript
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import type { HttpRequest, InvocationContext } from "@azure/functions";
import { queryHandler } from "../../src/functions/query/handler";
import { validQuery, multiDomainQuery } from "../fixtures/queries";
import { activeChunk } from "../fixtures/chunks";
import { expectedAnswer } from "../fixtures/expected-responses";

// Mock Azure AI Search + Azure OpenAI HTTP endpoints. No real services are called.
const server = setupServer(
  http.post("https://*.search.windows.net/*", () =>
    HttpResponse.json({ value: [activeChunk] })
  ),
  http.post("https://*.openai.azure.com/*", () =>
    HttpResponse.json({
      choices: [{ message: { content: expectedAnswer.answer } }],
    })
  )
);

function makeRequest(body: unknown): HttpRequest {
  return { json: async () => body } as unknown as HttpRequest;
}

function makeContext(): InvocationContext {
  return { invocationId: "test-invocation-id" } as unknown as InvocationContext;
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("queryHandler", () => {
  it("should return 200 with an answer and source_document when input is valid", async () => {
    // Arrange
    const request = makeRequest(validQuery);
    const context = makeContext();
    // Act
    const response = await queryHandler(request, context);
    // Assert
    expect(response.status).toBe(200);
    const body = response.jsonBody as {
      answer: string;
      source_document: string;
      confidence: "high" | "low";
    };
    expect(body.answer).toBe(expectedAnswer.answer);
    expect(body.source_document).toBe(activeChunk.source_document);
    expect(["high", "low"]).toContain(body.confidence);
  });

  it("should return 400 INVALID_INPUT when question is missing", async () => {
    // Arrange
    const request = makeRequest({ clientTier: "Gold" });
    const context = makeContext();
    // Act
    const response = await queryHandler(request, context);
    // Assert
    expect(response.status).toBe(400);
    expect(response.jsonBody).toEqual({
      error: "INVALID_INPUT",
      requestId: "test-invocation-id",
    });
  });

  it("should return 400 INVALID_INPUT when question exceeds max length", async () => {
    // Arrange
    const request = makeRequest({ question: "a".repeat(2001) });
    const context = makeContext();
    // Act
    const response = await queryHandler(request, context);
    // Assert
    expect(response.status).toBe(400);
    expect((response.jsonBody as { error: string }).error).toBe("INVALID_INPUT");
  });

  it("should always include a non-empty source_document when answering a multi-domain query", async () => {
    // Arrange
    const request = makeRequest(multiDomainQuery);
    const context = makeContext();
    // Act
    const response = await queryHandler(request, context);
    // Assert
    expect(response.status).toBe(200);
    const body = response.jsonBody as { source_document: string };
    expect(body.source_document.length).toBeGreaterThan(0);
  });
});
```

---

## Análise da rodada 2 — comparação real v1 × v2

Mesmo checklist de 14 itens da rodada 1, aplicado ao output real do v2:

| # | Convenção | Rodada 1 (v1) | Rodada 2 (v2) | Comentário |
|---|-----------|:-------------:|:-------------:|-----------|
| 1 | Azure Functions v4 | ✅ | ✅ | mantido |
| 2 | Zod input | ✅ | ✅ | mantido |
| 3 | Zod output | ✅ | ✅ | mantido |
| 4 | pino, sem console.log/context.log | ✅ | ✅ | mantido |
| 5 | erro estruturado 400/500 | ✅ | ✅ | v2 no formato exato `{ error, requestId }` |
| 6 | sem `any` | ✅ | ✅ | mantido |
| 7 | **split handler/validator/response-builder** | ❌ | ✅ | gerou os 3 arquivos nos caminhos exatos |
| 8 | **campo `source_document`** | ❌ | ✅ | obrigatório no schema e preenchido no builder |
| 9 | context budget ADR-0002 | ⚠️ | ⚠️ | em ambos delegado ao `prompt-builder`; no v2 com contrato documentado e limites explícitos no comentário |
| 10 | vigência ADR-0003 | ✅ | ✅ | v2 referencia `SUPERSEDIDO score × 0.1` |
| 11 | `authLevel: "function"` | ✅ | ✅ | mantido |
| 12 | **testes em inglês `should...when`** | ❌ | ✅ | corrigido |
| 13 | AAA + assertions específicas | ✅ | ✅ | v2 com Arrange/Act/Assert rotulados |
| 14 | **`tests/integration/` + msw + fixtures** | ❌ | ✅ | usou `setupServer`/msw e `tests/fixtures/` |

**Placar v2 (real):** 13 ✅ + 1 parcial (item 9) ≈ **13,5 / 14**.

### Evolução medida (real)

| | Rodada 1 (v1) | Rodada 2 (v2) |
|---|:--:|:--:|
| Aderência | **≈ 9,5 / 14** | **≈ 13,5 / 14** |

Os **4 itens que o v1 deixou implícitos** (split de arquivos, `source_document`, testes em inglês, msw/fixtures em `tests/integration/`) foram **todos corrigidos** no v2 — exatamente os pontos visados pela iteração. As 9 regras já explícitas no v1 permaneceram aderentes. Isso confirma a relação causa→efeito: **materializar a convenção dentro do AGENTS.md (caminhos literais, nome de campo no schema, mínimo de testing standards, checklist) elevou a aderência.**

### Por que funcionou

- **Caminhos de arquivo literais** no próprio AGENTS.md → o agente gerou `handler.ts`/`validator.ts`/`response-builder.ts` sem precisar do Anexo C.
- **`source_document` como campo obrigatório do schema Zod** → moveu a regra de produto de "prosa" para **contrato verificável**: agora um teste falha se o campo sumir (enforcement determinístico, não só prompt).
- **Mínimo de Testing Standards + Checklist de Geração** → testes em inglês, AAA, msw e fixtures no lugar certo; o agente usou o checklist como auto-verificação.

### Limitação reconhecida (persiste do v1 → v2)

O **context budget (item 9)** continua sendo o único item não-pleno em ambas as rodadas. Os dois agentes delegam o controle de orçamento ao `prompt-builder.ts` e documentam o contrato, mas **a garantia real de que o prompt nunca estoura o budget depende da implementação do serviço**, não do AGENTS.md. Conclusão honesta: regras probabilísticas (prompt) precisam de **rede determinística** — neste caso, um teste unitário de `prompt-builder.ts` que falhe se o total de tokens exceder o limite da ADR-0002. Nenhuma redação do AGENTS.md fecha essa lacuna sozinha.

### Conclusão geral

A iteração v1 → v2 produziu ganho **real e mensurável** (≈9,5 → ≈13,5 de 14) num teste com a variável "agente" controlada. A lição é mais rica do que "AGENTS.md melhor = output melhor": um agente capaz já cumpre o explícito, então o retorno de um AGENTS.md prescritivo está em **codificar o que o modelo não adivinha** (nomes exatos, layout, local/estratégia de teste) e em **mover as regras críticas para enforcement determinístico** (schema, teste, lint). E nem assim 100% é garantido por prompt — o item 9 é a prova honesta disso.
