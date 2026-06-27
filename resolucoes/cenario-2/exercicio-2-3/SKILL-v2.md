# SKILL: azure-functions-endpoint

> **Nível:** Domain · **Versão:** v2 (iterada após teste real — ver [analise-v1.md](analise-v1.md)) · **Mantenedor:** Tech Lead
> **Caminho no repo:** `skills/domain/azure-functions-endpoint.md`
> **Como usar:** quando esta skill estiver ativa, copie os **padrões canônicos** abaixo (não invente equivalentes) e, ao terminar, valide o output contra o **Checklist de autovalidação** no fim.

## Frase-ativação (quando esta skill se aplica)
Use sempre que precisar **criar ou modificar um endpoint HTTP do NovaTech Assistant** como **Azure Function v4** (query, feedback, health, etc.). Não use para o pipeline de ingestão nem para componentes React.

## Contexto
Endpoints do assistente são Azure Functions v4 (HTTP trigger) em TypeScript strict. Recebem a requisição do atendente, validam com Zod, chamam serviços de domínio (`src/services/`) e devolvem resposta — com **fonte citada** quando há resposta de domínio. Decisões: Azure OpenAI GPT-4o, context budget (ADR-0002), vigência de documentos (ADR-0003).

## Regras prescritivas (DEVE / NÃO DEVE)
1. **DEVE** usar Azure Functions v4 (`app.http(...)`), assinatura `(request: HttpRequest, context: InvocationContext)`.
2. **DEVE** validar input com **Zod** antes de qualquer lógica; quando o endpoint produz resposta de domínio, validar também o **output** com Zod.
3. **DEVE** usar TypeScript strict — **NÃO DEVE** usar `any`; tipos via `z.infer` ou `src/shared/types.ts`.
4. **DEVE** logar com **pino** via `src/shared/logger.ts`. **NÃO DEVE** usar `console.log` nem `context.log` para logs de aplicação.
5. **DEVE** extrair `const requestId = context.invocationId` e **incluí-lo em todo log e em toda resposta de erro** (correlação ponta a ponta).
6. **DEVE** tratar erros com o **shape canônico**: input inválido → 400 `{ error: "INVALID_INPUT", requestId }`; erro interno → 500 `{ error: "INTERNAL_ERROR", requestId }`. **NÃO DEVE** retornar strings de erro livres.
7. **DEVE** definir `authLevel: "function"` no registro do endpoint. **NÃO DEVE** usar `authLevel: "anonymous"`.
8. **DEVE** dividir em arquivos: `handler.ts`, `validator.ts` e — **somente quando há resposta de domínio** — `response-builder.ts`, em `src/functions/<nome>/`.
9. **DEVE** citar a fonte (`source_document`) **quando o endpoint retorna resposta de domínio do assistente**. Endpoints sem resposta de domínio (ex.: feedback, health) **não** precisam.
10. A montagem de prompt e a chamada ao modelo ficam em `src/services/` — o handler **NÃO** chama o Azure OpenAI diretamente.
11. **DEVE** acompanhar todo endpoint novo de um **teste de integração** em `tests/integration/<nome>.test.ts` (ver dependências) cobrindo: caminho feliz, input inválido (400) e erro interno (500).

## Padrão canônico — validator (input, e output quando há domínio)
```typescript
// src/functions/<nome>/validator.ts
import { z } from "zod";

export const FooRequest = z.object({
  // campos do request...
});
export type FooRequest = z.infer<typeof FooRequest>;

// Só quando há resposta de domínio do assistente:
export const FooResponse = z.object({
  answer: z.string(),
  source_document: z.string(), // OBRIGATÓRIO em respostas de domínio (Regra 9)
});
export type FooResponse = z.infer<typeof FooResponse>;
```

## Padrão canônico — handler (copie esta estrutura)
```typescript
// src/functions/<nome>/handler.ts
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { ZodError } from "zod";
import { logger } from "../../shared/logger";
import { FooRequest } from "./validator";

export async function fooHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  const requestId = context.invocationId;            // Regra 5
  try {
    const input = FooRequest.parse(await request.json());
    logger.info({ requestId, route: "api/foo" }, "foo received");

    // ... lógica: chamar src/services/* quando precisar de busca/modelo ...

    return { status: 200, jsonBody: { /* resposta; inclua source_document se domínio */ } };
  } catch (err) {
    if (err instanceof ZodError) {
      logger.warn({ requestId, err }, "invalid input");
      return { status: 400, jsonBody: { error: "INVALID_INPUT", requestId } };   // Regra 6
    }
    logger.error({ requestId, err }, "unhandled error");
    return { status: 500, jsonBody: { error: "INTERNAL_ERROR", requestId } };    // Regra 6
  }
}

app.http("foo", {
  methods: ["POST"],
  authLevel: "function",   // Regra 7 — nunca "anonymous"
  route: "api/foo",
  handler: fooHandler,
});
```

## Exemplo — DON'T (com o porquê)
```typescript
export async function foo(req: any) {              // ❌ any (Regra 3)
  console.log("request", req);                     // ❌ console.log (Regra 4)
  const body = await req.json();                   // ❌ sem Zod (Regra 2)
  return { status: 200, jsonBody: { answer: "x" } }; // ❌ sem source_document em domínio (Regra 9)
}
app.http("foo", { methods: ["POST"], handler: foo }); // ❌ sem authLevel → anonymous (Regra 7)
```

## Anti-padrões comuns (o agente realmente gera isto sem guidance)
- **`authLevel` omitido** → endpoint cai em `anonymous` (aberto). Sempre `"function"`.
- **Erro como string livre** (`{ error: "invalid request" }`) em vez do shape `{ error: CODE, requestId }` → quebra cliente e correlação.
- **`context` recebido e ignorado** → sem `requestId` no log/resposta, impossível rastrear a chamada.
- Tudo num `handler.ts` só (validação + lógica + montagem).
- Chamar Azure OpenAI direto do handler em vez de `src/services/`.
- Endpoint sem teste de integração acompanhante.
- Resposta de domínio sem `source_document`.

## Dependências (ler antes)
- Foundation: `typescript-conventions`, `error-handling`.
- Domain: `azure-ai-search-integration` (para a parte de busca), `testing-patterns`.
- Artifact: `create-integration-test` (para o teste acompanhante da Regra 11).

## Checklist de autovalidação (o agente DEVE conferir antes de entregar)
- [ ] `app.http` v4 com `authLevel: "function"`.
- [ ] Input validado com Zod; output validado com Zod se há resposta de domínio.
- [ ] Sem `any`; tipos via `z.infer`.
- [ ] Logs via `shared/logger` (pino), com `requestId`; sem `console.log`/`context.log`.
- [ ] Erros no shape `{ error: CODE, requestId }` — 400 input, 500 interno.
- [ ] Arquivos separados (`handler.ts`, `validator.ts`, +`response-builder.ts` se domínio).
- [ ] `source_document` presente se a resposta é de domínio.
- [ ] Teste de integração criado em `tests/integration/<nome>.test.ts`.
