# Teste do AGENTS.md — Rodada 1 (sobre AGENTS-v1) — EXECUÇÃO REAL

> **Metodologia (importante para a avaliação de D2):** o GitHub Copilot não é conectável neste ambiente CLI. Para obter **evidência de teste real** (geração → avaliação → reescrita), em vez de transcrever outputs hipotéticos, foi invocado um **agente de codegen independente** (subagente Claude Code, papel `general-purpose`) atuando como pair-programmer, exatamente como o Copilot atuaria. Garantias de validade do teste:
> - O agente recebeu **somente o conteúdo do `AGENTS-v1.md`** + o prompt do desenvolvedor. **Não** teve acesso à análise, à resposta esperada, aos Anexos, às ADRs nem ao restante do repositório (instruído a não ler outros arquivos).
> - Os outputs abaixo são **literais**, exatamente como o agente os gerou. Não houve edição manual do código.
> - A rodada 2 ([teste-copilot-rodada-2.md](teste-copilot-rodada-2.md)) repetiu os **mesmos dois prompts** com um agente igualmente isolado, recebendo apenas o `AGENTS-v2.md` — permitindo comparar o efeito da iteração no AGENTS.md, com a variável "agente" controlada.

---

## Prompt 1 (desenvolvedor → agente)

> "Generate an Azure Function HTTP trigger for the `POST /api/query` endpoint of the NovaTech Assistant. Follow the repository's AGENTS.md."

### Output real — `src/functions/query.ts`

```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { z } from "zod";
import { logger } from "../shared/logger";
import { AppError, toErrorResponse } from "../shared/errors";
import { answerQuery } from "../services/queryService";

/**
 * POST /api/query
 * Endpoint da API do NovaTech Assistant.
 * Recebe a pergunta do atendente e retorna a resposta do assistente RAG,
 * sempre com citação de fonte (restrição central de produto).
 */

// Domínios suportados pelo retrieval (SLA, Frete, Devolução) — ADR-0004.
const DomainSchema = z.enum(["sla", "frete", "devolucao"]);

// ---- Input ----
const QueryRequestSchema = z.object({
  question: z.string().min(1, "question é obrigatória").max(2000),
  sessionId: z.string().uuid().optional(),
  // Histórico de sessão comprimido limitado a ~3 turnos (ADR-0002).
  history: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().min(1),
      }),
    )
    .max(6) // 3 turnos (par user/assistant)
    .optional(),
});

// ---- Output ----
const SourceSchema = z.object({
  documentId: z.string(),
  title: z.string(),
  domain: DomainSchema,
  // Metadados de vigência — ADR-0003.
  dataVigencia: z.string(),
  status: z.enum(["ativo", "inativo"]),
});

const QueryResponseSchema = z.object({
  // Quando não encontra resposta, answered = false e o texto diz explicitamente.
  answered: z.boolean(),
  answer: z.string(),
  sources: z.array(SourceSchema),
  // Informa quando existe versão anterior do procedimento (ADR-0003).
  hasPreviousVersions: z.boolean(),
});

export type QueryRequest = z.infer<typeof QueryRequestSchema>;
export type QueryResponse = z.infer<typeof QueryResponseSchema>;

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext,
): Promise<HttpResponseInit> {
  const log = logger.child({ invocationId: context.invocationId, route: "POST /api/query" });

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    log.warn("corpo da requisição não é JSON válido");
    return toErrorResponse(new AppError("INVALID_BODY", "Corpo da requisição inválido (JSON esperado).", 400));
  }

  // Validação de input com Zod.
  const parsedInput = QueryRequestSchema.safeParse(body);
  if (!parsedInput.success) {
    log.warn({ issues: parsedInput.error.issues }, "input inválido");
    return toErrorResponse(
      new AppError("VALIDATION_ERROR", "Parâmetros inválidos.", 400, parsedInput.error.flatten()),
    );
  }

  try {
    const result = await answerQuery(parsedInput.data, log);

    // Validação de output com Zod.
    const parsedOutput = QueryResponseSchema.parse(result);

    log.info(
      { answered: parsedOutput.answered, sourceCount: parsedOutput.sources.length },
      "consulta respondida",
    );

    return {
      status: 200,
      jsonBody: parsedOutput,
      headers: { "content-type": "application/json" },
    };
  } catch (err) {
    if (err instanceof AppError) {
      log.error({ code: err.code }, err.message);
      return toErrorResponse(err);
    }
    log.error({ err }, "erro inesperado ao processar consulta");
    return toErrorResponse(
      new AppError("INTERNAL_ERROR", "Erro interno ao processar a consulta.", 500),
    );
  }
}

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  route: "query",
  handler: queryHandler,
});
```

---

## Prompt 2 (desenvolvedor → agente)

> "Generate a test for that endpoint. Follow the AGENTS.md."

### Output real — `src/functions/query.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { HttpRequest, InvocationContext } from "@azure/functions";
import { queryHandler } from "./query";
import type { QueryResponse } from "./query";
import * as queryService from "../services/queryService";

// Mock do serviço de negócio para isolar o HTTP trigger.
vi.mock("../services/queryService", () => ({
  answerQuery: vi.fn(),
}));

// Logger não deve usar console.log (pino) — silenciado nos testes via child stub.
vi.mock("../shared/logger", () => {
  const log = {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    child: vi.fn(() => log),
  };
  return { logger: log };
});

function makeRequest(body: unknown, malformed = false): HttpRequest {
  return {
    json: malformed ? vi.fn().mockRejectedValue(new Error("bad json")) : vi.fn().mockResolvedValue(body),
  } as unknown as HttpRequest;
}

const context = { invocationId: "test-inv-1" } as unknown as InvocationContext;
const answerQueryMock = vi.mocked(queryService.answerQuery);

const validResponse: QueryResponse = {
  answered: true,
  answer: "O SLA de entrega é de 5 dias úteis.",
  sources: [
    {
      documentId: "doc-001",
      title: "Procedimento de SLA de Entrega",
      domain: "sla",
      dataVigencia: "2026-01-01",
      status: "ativo",
    },
  ],
  hasPreviousVersions: false,
};

describe("POST /api/query", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("retorna 200 com resposta validada para input válido", async () => {
    answerQueryMock.mockResolvedValue(validResponse);
    const req = makeRequest({ question: "Qual o SLA de entrega?" });
    const res = await queryHandler(req, context);
    expect(res.status).toBe(200);
    expect(res.jsonBody).toEqual(validResponse);
    expect(answerQueryMock).toHaveBeenCalledOnce();
  });

  it("retorna 400 quando o body não é JSON válido", async () => {
    const req = makeRequest(undefined, true);
    const res = await queryHandler(req, context);
    expect(res.status).toBe(400);
    expect(answerQueryMock).not.toHaveBeenCalled();
  });

  it("retorna 400 quando question está ausente (falha de validação Zod no input)", async () => {
    const req = makeRequest({ sessionId: "00000000-0000-0000-0000-000000000000" });
    const res = await queryHandler(req, context);
    expect(res.status).toBe(400);
    expect(answerQueryMock).not.toHaveBeenCalled();
  });

  it("retorna 400 quando history excede 3 turnos (limite ADR-0002)", async () => {
    const history = Array.from({ length: 8 }, (_, i) => ({
      role: i % 2 === 0 ? ("user" as const) : ("assistant" as const),
      content: `msg ${i}`,
    }));
    const req = makeRequest({ question: "pergunta", history });
    const res = await queryHandler(req, context);
    expect(res.status).toBe(400);
    expect(answerQueryMock).not.toHaveBeenCalled();
  });

  it("propaga resposta 'não encontrei' (answered=false) sem inventar conteúdo", async () => {
    const notFound: QueryResponse = {
      answered: false,
      answer: "Não encontrei essa informação na documentação interna.",
      sources: [],
      hasPreviousVersions: false,
    };
    answerQueryMock.mockResolvedValue(notFound);
    const req = makeRequest({ question: "pergunta sem cobertura" });
    const res = await queryHandler(req, context);
    expect(res.status).toBe(200);
    expect((res.jsonBody as QueryResponse).answered).toBe(false);
    expect((res.jsonBody as QueryResponse).sources).toHaveLength(0);
  });

  it("retorna 500 quando o serviço lança erro inesperado", async () => {
    answerQueryMock.mockRejectedValue(new Error("falha downstream"));
    const req = makeRequest({ question: "Qual o SLA?" });
    const res = await queryHandler(req, context);
    expect(res.status).toBe(500);
  });

  it("sinaliza versões anteriores quando há procedimento substituído (ADR-0003)", async () => {
    answerQueryMock.mockResolvedValue({ ...validResponse, hasPreviousVersions: true });
    const req = makeRequest({ question: "Qual a política de devolução atual?" });
    const res = await queryHandler(req, context);
    expect(res.status).toBe(200);
    expect((res.jsonBody as QueryResponse).hasPreviousVersions).toBe(true);
  });
});
```

A análise detalhada do que o agente seguiu/ignorou está em [analise-v1-seguido-ignorado.md](analise-v1-seguido-ignorado.md).
