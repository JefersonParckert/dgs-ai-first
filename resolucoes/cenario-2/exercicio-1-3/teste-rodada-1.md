# Teste da Skill — Rodada 1 (sobre SKILL-v1) — EXECUÇÃO REAL

> **Metodologia:** um agente de codegen independente (subagente Claude Code, `general-purpose`) recebeu **apenas** o conteúdo de `skills/domain/azure-functions-endpoint.md` (v1) + o pedido de um desenvolvedor. Não viu este arquivo, a análise, nem código de referência (instruído a não ler outros arquivos). O GitHub Copilot não é conectável neste ambiente CLI; o agente ocupa o papel funcional dele. Output **literal** abaixo.

## Prompt (desenvolvedor → agente)
> "Generate the `POST /api/feedback` endpoint (atendente reporta que uma resposta do assistente estava incorreta). Recebe o id da query original, o id do atendente e um motivo em texto livre. Follow the azure-functions-endpoint skill."

## Output real — `src/functions/feedback/validator.ts`
```typescript
import { z } from "zod";

export const FeedbackRequest = z.object({
  queryId: z.string().uuid(),
  attendantId: z.string().min(1),
  reason: z.string().min(1).max(2000),
});

export type FeedbackRequest = z.infer<typeof FeedbackRequest>;
```

## Output real — `src/functions/feedback/handler.ts`
```typescript
import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { ZodError } from "zod";
import { logger } from "../../shared/logger";
import { FeedbackRequest } from "./validator";

export async function feedbackHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  let input: FeedbackRequest;

  try {
    input = FeedbackRequest.parse(await request.json());
  } catch (err) {
    if (err instanceof ZodError) {
      logger.warn({ route: "api/feedback", err }, "invalid feedback request");
      return { status: 400, jsonBody: { error: "invalid request" } };
    }
    logger.error({ route: "api/feedback", err }, "failed to read feedback body");
    return { status: 400, jsonBody: { error: "invalid request" } };
  }

  try {
    logger.info(
      { route: "api/feedback", queryId: input.queryId, attendantId: input.attendantId },
      "feedback received"
    );
    return { status: 201, jsonBody: { status: "recorded", queryId: input.queryId } };
  } catch (err) {
    logger.error({ route: "api/feedback", err }, "feedback failed");
    return { status: 500, jsonBody: { error: "internal error" } };
  }
}

app.http("feedback", {
  methods: ["POST"],
  route: "api/feedback",
  handler: feedbackHandler,
});
```

> O agente também notou, corretamente, que as Regras 7 e 8 (citar fonte / chamar Azure OpenAI via `src/services/`) **não se aplicam** ao feedback (não há resposta de domínio) e por isso não criou `response-builder.ts`. Bom julgamento — não é violação.

Análise detalhada em [analise-v1.md](analise-v1.md).
