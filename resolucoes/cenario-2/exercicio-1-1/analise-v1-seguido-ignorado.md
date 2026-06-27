# Análise — o que o agente seguiu e o que ignorou (AGENTS-v1) — sobre EXECUÇÃO REAL

> Esta análise é sobre o output **real** gerado em [teste-copilot-rodada-1.md](teste-copilot-rodada-1.md) por um agente de codegen que recebeu **apenas** o `AGENTS-v1.md`.

## Tabela de aderência (checklist único de convenções do projeto)

Usei o mesmo checklist de 14 itens nas duas rodadas, para a comparação ser justa.

| # | Convenção do projeto | Estava explícita no v1? | Seguiu? | Evidência no output real |
|---|----------------------|:----------------------:|:-------:|--------------------------|
| 1 | Azure Functions v4 (`app.http`) | sim | ✅ | `app.http("query", { ... })` |
| 2 | Zod no **input** | sim | ✅ | `QueryRequestSchema.safeParse(body)` |
| 3 | Zod no **output** | sim | ✅ | `QueryResponseSchema.parse(result)` |
| 4 | pino via logger compartilhado, sem `console.log`/`context.log` | sim | ✅ | `logger.child({...})`, zero `console.log` |
| 5 | Tratamento de erro estruturado (400/500) | sim (genérico) | ✅ | `AppError` + `toErrorResponse`, 400 e 500 |
| 6 | Sem `any` | sim (strict) | ✅ | usou `unknown` + `safeParse` |
| 7 | **Split handler.ts / validator.ts / response-builder.ts** | **não** (v1 só dizia "seguir a estrutura de pastas") | ❌ | tudo em um único `query.ts` |
| 8 | Campo **`source_document`** na resposta | **não** (v1 só dizia "sempre cita a fonte") | ❌ | usou um array `sources[]` com schema próprio |
| 9 | Context budget ADR-0002 (máx 8 chunks etc.) | sim (em prosa) | ⚠️ parcial | tratou só o limite de histórico (`max(6)` = 3 turnos); chunk budget ficou implícito no serviço |
| 10 | Vigência ADR-0003 (`status`/`data_vigencia`) | sim (em prosa) | ✅ | `dataVigencia`/`status` no `SourceSchema` + `hasPreviousVersions` |
| 11 | `authLevel: "function"` | **não** | ✅ | escolheu `function` por conta própria |
| 12 | Testes: `describe`/`it` em **inglês** (`should ... when ...`) | **não** | ❌ | nomes em português (`"retorna 400 quando..."`) |
| 13 | Testes: AAA + assertions específicas (sem `toBeDefined()` isolado) | **não** (sem seção de testes no v1) | ✅ | `toEqual`, `toBe`, `toHaveLength`, casos ricos |
| 14 | Testes em `tests/integration/` com **msw** + fixtures em `tests/fixtures/` | **não** | ❌ | co-locou `query.test.ts`, usou `vi.mock`, fixtures inline |

**Placar v1 (real):** 9 ✅ + 1 parcial (0,5) + 4 ❌ ≈ **9,5 / 14**.

## Diagnóstico — o padrão por trás dos acertos e erros

O resultado real revela um padrão **mais nuançado e mais honesto** do que se imaginaria:

1. **Um agente capaz já cumpre o que está escrito explicitamente.** Zod (input+output), pino, erro estruturado, sem `any` — tudo isso o v1 **dizia em texto direto**, e o agente cumpriu. Ou seja: para regras explícitas, mesmo um v1 "simples" funciona com um modelo competente.

2. **O agente erra exatamente onde o v1 deixou a convenção implícita ou "por referência".** Os 4 ❌ são todos itens que o v1 **não materializou no próprio arquivo**:
   - **Split de arquivos (item 7):** o v1 dizia "seguir a estrutura de pastas" sem mostrar os nomes `handler.ts`/`validator.ts`/`response-builder.ts`. O agente não abre o Anexo C — ele segue o que está no AGENTS.md. Resultado: um arquivo só.
   - **`source_document` (item 8):** o v1 só dizia "sempre cita a fonte". O agente citou fonte — mas com um contrato **diferente** (`sources[]`). Sem o nome exato do campo, o agente inventou um equivalente plausível, o que quebraria a integração com o resto do sistema.
   - **Convenções de teste (itens 12 e 14):** o v1 não tinha seção de testes. O agente escreveu bons testes, mas em português, co-locados e com `vi.mock` em vez de `tests/integration/` + msw.

3. **O agente preenche lacunas com defaults razoáveis — que podem divergir do projeto.** `authLevel: "function"` (acertou) e `sources[]` (divergiu) são os dois lados da mesma moeda: na ausência de instrução, o modelo decide sozinho. Às vezes coincide com o projeto, às vezes não — e essa imprevisibilidade é precisamente o que o AGENTS.md existe para eliminar.

## Conclusão da rodada 1

A lição empírica é mais sofisticada do que "o agente ignora o AGENTS.md vago": **um agente capaz eleva o piso** (cumpre o explícito sozinho), então o valor de um AGENTS.md prescritivo se concentra em **codificar as convenções que o modelo não tem como adivinhar** — nomes exatos de campo (`source_document`), layout de arquivos, local e estratégia de teste (msw, fixtures), e idioma dos nomes de teste.

A iteração para o v2, portanto, mira nesses 4 pontos: trazer os caminhos de arquivo para **dentro** do AGENTS.md, fixar `source_document` como **campo obrigatório do schema Zod**, e adicionar um **mínimo de Testing Standards** (inglês, AAA, msw, fixtures) — além de um checklist auto-verificável.

> **Limitação reconhecida honestamente:** o context budget (item 9) é o ponto mais difícil de garantir por prompt — o agente delega ao serviço e documenta o contrato, mas a garantia real depende de um teste determinístico em `prompt-builder.ts`. Nenhuma versão do AGENTS.md fecha essa lacuna sozinha; ela exige enforcement em código.
