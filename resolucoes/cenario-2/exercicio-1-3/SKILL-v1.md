# SKILL: azure-functions-endpoint

> **Nível:** Domain · **Versão:** v1 (antes do teste com agente) · **Mantenedor:** Tech Lead
> **Caminho no repo:** `skills/domain/azure-functions-endpoint.md`

## Frase-ativação (quando esta skill se aplica)
Use esta skill sempre que precisar **criar ou modificar um endpoint HTTP do NovaTech Assistant** implementado como **Azure Function v4** (ex.: query, feedback, health). Não use para o pipeline de ingestão nem para componentes React.

## Contexto
Os endpoints do assistente são Azure Functions v4 (HTTP trigger) em TypeScript. Eles recebem a requisição do atendente, validam, chamam os serviços de domínio (busca + completion) e devolvem uma resposta **com citação de fonte**. As decisões técnicas vêm das ADRs do cenário 1 (Azure OpenAI GPT-4o, context budget, vigência de documentos).

## Regras prescritivas
1. **DEVE** usar o modelo de programação **Azure Functions v4** (`app.http(...)`), assinatura `(request: HttpRequest, context: InvocationContext)`.
2. **DEVE** validar o input com **Zod** antes de qualquer lógica.
3. **DEVE** usar **TypeScript strict** — sem `any`; tipos vindos do Zod (`z.infer`) ou de `src/shared/types.ts`.
4. **DEVE** logar com **pino** via `src/shared/logger.ts`. **NÃO DEVE** usar `console.log`.
5. **DEVE** tratar erros: input inválido → HTTP 400; erro interno → HTTP 500.
6. **DEVE** dividir o endpoint em arquivos: `handler.ts`, `validator.ts`, e (quando há resposta de domínio) `response-builder.ts`, em `src/functions/<nome>/`.
7. **DEVE** citar a fonte do documento na resposta do assistente (rastreabilidade — guardrail do projeto).
8. A montagem de prompt e a chamada ao modelo ficam em `src/services/` — o handler **não** chama o Azure OpenAI diretamente.

## Exemplo — DO (endpoint correto)

`src/functions/query/validator.ts`
```typescript
import { z } from "zod";

export const QueryRequest = z.object({
  question: z.string().min(1).max(2000),
});
export type QueryRequest = z.infer<typeof QueryRequest>;
```

`src/functions/query/handler.ts`
```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { logger } from "../../shared/logger";
import { QueryRequest } from "./validator";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const input = QueryRequest.parse(await request.json());
    logger.info({ route: "api/query" }, "query received");
    // chama serviços de domínio (src/services) e monta a resposta
    return { status: 200, jsonBody: { answer: "...", source: "POL-001" } };
  } catch (err) {
    logger.error({ err }, "query failed");
    return { status: 400, jsonBody: { error: "invalid request" } };
  }
}

app.http("query", { methods: ["POST"], route: "api/query", handler: queryHandler });
```

## Exemplo — DON'T (endpoint errado)

```typescript
// ❌ sem Zod, com any, console.log, sem citar fonte, tudo num arquivo só
export async function query(req: any) {
  console.log("request", req);
  const body = await req.json();
  return { status: 200, jsonBody: { answer: "resposta" } }; // sem fonte
}
```

## Anti-padrões comuns
- Colocar validação, lógica e montagem de resposta tudo no `handler.ts`.
- Chamar o Azure OpenAI direto do handler em vez de usar `src/services/`.
- Retornar a resposta sem citar a fonte do documento.

## Dependências (ler antes)
- Foundation: `typescript-conventions`, `error-handling`.
- Domain: `azure-ai-search-integration` (para a parte de busca).
