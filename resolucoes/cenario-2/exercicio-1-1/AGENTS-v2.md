# AGENTS.md — NovaTech Assistant

> **Versão:** v2 (iterada após teste com Copilot — ver [analise-v1-seguido-ignorado.md](analise-v1-seguido-ignorado.md))
> **Mantenedor:** Tech Lead
> **Como ler este arquivo:** Você é um agente de IA (GitHub Copilot, Claude Code). Leia este arquivo INTEIRO antes de gerar qualquer artefato. As regras marcadas com **DEVE** / **NÃO DEVE** são obrigatórias. Quando houver um snippet "padrão canônico", copie o padrão — não invente um equivalente. Ao final de cada geração de código, valide seu output contra o **Checklist de Geração** no fim deste documento.

---

## Project Overview

O **NovaTech Assistant** é um assistente de IA que responde perguntas do time de atendimento da NovaTech (transportadora/logística) sobre **SLAs, frete e devoluções**, via RAG sobre a documentação interna.

- **Usuário primário:** atendente de suporte da NovaTech.
- **Restrições centrais de produto (resumo — detalhe na seção Product Rules):** o assistente **nunca inventa** valores; **sempre cita fonte**; quando não há resposta na base, **diz explicitamente**; responde em **português formal**.
- **Base documental:** 847 documentos consolidados (12 com contradições pendentes — Compliance).
- **Volume estimado:** ~192 consultas/dia (320 chamados/dia × 60%).

---

## Tech Stack & Architecture

### Stack autorizada (NÃO introduzir dependências fora desta lista sem ADR)

| Camada | Tecnologia | Regra dura |
|--------|-----------|-----------|
| Backend / API | TypeScript + Azure Functions v4 (HTTP triggers) | `strict: true`; assinatura `(request: HttpRequest, context: InvocationContext)` |
| Bot | TypeScript + Bot Framework | Interface no Teams |
| Painel web | React | Dashboard |
| Validação | **Zod** | input E output de todo endpoint — ver padrão canônico |
| Logging | **pino** via `src/shared/logger.ts` | **NÃO** usar `console.log` **nem** `context.log` para logs de aplicação |
| Erros | custom errors de `src/shared/errors.ts` | ver padrão canônico |
| Testes | **Vitest** | ver Testing Standards |
| Infra | Bicep | `infra/` (estado narrativo) |
| LLM | Azure OpenAI **GPT-4o** | ADR-0001 |
| Retrieval | Azure AI Search | ADR-0004 |

### Arquitetura (4 componentes) e onde cada arquivo VIVE

Um endpoint RAG **DEVE** ser dividido nos seguintes arquivos (não colocar tudo num só):

```
src/functions/<nome>/
├── handler.ts           # HTTP trigger: orquestra validação → serviços → resposta. Registra a function.
├── validator.ts         # Schemas Zod de request e response + função de parse
└── response-builder.ts  # Monta o objeto de resposta (inclui source_document)
src/services/            # search.ts, completion.ts, prompt-builder.ts, response-validator.ts
src/shared/              # types.ts, config.ts, logger.ts, errors.ts
tests/integration/       # testes de integração (msw para Azure)
tests/fixtures/          # chunks.ts, queries.ts, expected-responses.ts
```

Os 4 componentes: (1) pipeline de ingestão `src/pipeline/`; (2) API do assistente `src/functions/`; (3) bot do Teams `src/bot/`; (4) painel web `src/web/`.

### Gerenciamento de contexto — REGRAS DURAS (ADR-0002)

Ao montar o prompt para o GPT-4o, o código em `src/services/prompt-builder.ts` **DEVE** respeitar este orçamento. Estes números são limites, não sugestões:

| Componente | Limite |
|-----------|--------|
| System prompt | ~4.000 tokens |
| Chunks recuperados | ~8.000 tokens — **no máximo 8 chunks** de ~500 tokens |
| Histórico de sessão (comprimido) | ~1.500 tokens — **no máximo 3 turnos** |
| Pergunta atual | ~300 tokens |

- **NÃO DEVE** enviar a janela de 128K cheia; ela é capacidade de emergência.
- **Retrieval multi-domínio:** se a pergunta cruza 2+ domínios (SLA / Frete / Devolução), buscar **até 3 chunks por domínio** (máx. 8 no total), priorizando diversidade de fonte sobre similaridade global.
- **Posicionamento (lost in the middle):** chunks mais relevantes no INÍCIO do bloco de contexto; pergunta atual no FINAL.

### Documentos contraditórios — REGRAS DURAS (ADR-0003)

- Todo chunk carrega `status` (`ATIVO` | `SUPERSEDIDO` | `BLOQUEADO_REVISAO_HUMANA`) e `data_vigencia`.
- Reranking: documentos `SUPERSEDIDO` têm score multiplicado por 0.1.
- Quando o retrieval trouxer 2 versões do mesmo `id_procedimento`, o código **DEVE** repassar ambas ao prompt e o assistente **DEVE** apresentar as duas, marcando vigente vs anterior. **NÃO DEVE** interpolar valores entre versões.

---

## Coding Standards

### Padrão canônico — logging (substitui qualquer outro logger)

```typescript
// SEMPRE importe o logger compartilhado. NÃO use console.log nem context.log.
import { logger } from "../../shared/logger";

logger.info({ requestId, route: "api/query" }, "query received");
logger.error({ err, requestId }, "azure search failed");
```

### Padrão canônico — validação com Zod (input E output)

```typescript
// src/functions/query/validator.ts
import { z } from "zod";

export const QueryRequest = z.object({
  question: z.string().min(1).max(2000),
  clientTier: z.enum(["Gold", "Silver", "Standard"]).optional(),
  sessionId: z.string().uuid().optional(),
});
export type QueryRequest = z.infer<typeof QueryRequest>;

export const QueryResponse = z.object({
  answer: z.string(),
  source_document: z.string(),        // OBRIGATÓRIO — ver Product Rules
  confidence: z.enum(["high", "low"]),
});
export type QueryResponse = z.infer<typeof QueryResponse>;
```

### Padrão canônico — erro e handler

```typescript
// src/functions/query/handler.ts
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { logger } from "../../shared/logger";
import { ValidationError, AppError } from "../../shared/errors";
import { QueryRequest, QueryResponse } from "./validator";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  const requestId = context.invocationId;
  try {
    const parsed = QueryRequest.parse(await request.json()); // lança ZodError se inválido
    logger.info({ requestId, route: "api/query" }, "query received");

    // ... search + prompt-builder (respeitando context budget) + completion ...

    const body: QueryResponse = QueryResponse.parse(/* response-builder result */);
    return { status: 200, jsonBody: body };
  } catch (err) {
    if (err instanceof ValidationError || err?.name === "ZodError") {
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

### Regras gerais

- `strict: true`. **NÃO DEVE** usar `any`; use os tipos inferidos do Zod ou tipos de `src/shared/types.ts`.
- Toda resposta de endpoint do assistente **DEVE** incluir `source_document` (campo obrigatório no schema Zod de output).
- Comentários e nomes de identificadores em **inglês**; documentos de status/PR em **português**.
- Chamadas a Azure (Search/OpenAI) **DEVEM** usar retry com exponential backoff.

---

## Product Rules & Guardrails (Product Specialist)

> _A ser escrito pelo Product Specialist (exercício PS 2.3). O contrato `source_document` obrigatório e o glossário de domínio vivem aqui._

## Testing Standards (QA)

> _A ser escrito pelo QA (exercício QA 2.1). **Mínimo provisório definido pelo Tech Lead até a seção ser preenchida:**_
> - `describe('<Modulo>', () => it('should <comportamento> when <condição>'))` em inglês.
> - Arrange / Act / Assert explícitos.
> - Assertions específicas ao comportamento. **NÃO DEVE** usar `toBeDefined()` / `toBeTruthy()` isolados.
> - **NÃO DEVE** chamar serviços reais (Azure) — usar msw/mocks. Testes de integração em `tests/integration/`, fixtures em `tests/fixtures/`.

## Project Management Rules (Delivery Manager)

> _A ser escrito pelo Delivery Manager (exercício DM 2.3)._

---

## Build & Deploy

- **Branch strategy:** feature branches **locais** (sem remoto nesta fase).
- **"Abrir PR":** criar a branch e escrever a descrição em `docs/pull-requests/PR-NNNN.md` com: objetivo, mudanças, e checklist dos validation gates. Revisão simulada localmente.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- **CI:** `.github/workflows/ci.yml` → lint + test + build. Coverage mínimo 80% (linhas).
- **Deploy:** estado narrativo — nenhum recurso Azure real é provisionado nesta fase.

---

## Checklist de Geração (o agente DEVE validar o próprio output contra isto)

Ao gerar um endpoint:
- [ ] Arquivos separados: `handler.ts`, `validator.ts`, `response-builder.ts`.
- [ ] Input e output validados com Zod (sem `any`).
- [ ] Logging via `src/shared/logger.ts` (pino) — sem `console.log`/`context.log`.
- [ ] `try/catch` com erro estruturado (`{ error, requestId }`) — 400 para input inválido, 500 para erro interno.
- [ ] Resposta inclui `source_document`.
- [ ] Prompt respeita o context budget (máx 8 chunks; histórico de até 3 turnos).
- [ ] `authLevel: "function"` (não `anonymous`).

Ao gerar um teste:
- [ ] `describe`/`it` descritivos em inglês (`should ... when ...`).
- [ ] Arrange/Act/Assert explícitos.
- [ ] Assertions específicas (não `toBeDefined()` isolado).
- [ ] Sem chamadas a serviços reais (msw/mocks); fixtures em `tests/fixtures/`.
