# Critérios de Maturidade de Skill — quando está pronta para uso pelo time

Uma skill **não** está pronta "quando parece boa". Maturidade é medida por evidência empírica. Definimos 4 estágios; uma skill só é **promovida a `stable`** (uso liberado pelo time) quando cumpre TODOS os critérios mensuráveis do estágio.

## Estágios

| Estágio | Significado | Quem pode usar |
|---|---|---|
| `draft` | Escrita, ainda não testada com agente | só o autor |
| `testing` | Em ciclo de teste real com agente | autor + revisor |
| `stable` | Aprovada para uso geral | todo o time + agentes em CI |
| `deprecated` | Substituída/obsoleta | ninguém (aponta para a sucessora) |

## Critérios mensuráveis para promover a `stable`

1. **Testada com ≥ 3 gerações reais** de agente, em **≥ 2 alvos diferentes**, não só o exemplo da própria skill. *Esta skill: ✅ atendido — 3 gerações (feedback v1, feedback v2, query v2) em 2 alvos (`feedback` e `query`).*
2. **Aderência ≥ 90%** no checklist da skill na última rodada (itens aplicáveis). *Esta skill: ✅ v2 atingiu 10/10 (feedback) e 12/12 (query) = 100%.*
3. **Iteração documentada:** existe pelo menos um ciclo v(n)→v(n+1) registrado, com o placar antes/depois. *Esta skill: 6/10 → 10/10.*
4. **Anti-padrões validados:** cada anti-padrão listado foi **observado de fato** em uma geração sem guidance (não é hipotético). *Esta skill: `authLevel` anonymous, erro como string livre e `context` ignorado foram todos observados na rodada 1.*
5. **Sem regressão entre rodadas:** nenhum item que passou em v(n) falhou em v(n+1).
6. **Revisada por um segundo TL/Dev Sênior** (Gate 3 do AGENTS.md) e com dependências (Foundation/Domain/Artifact) existentes e linkadas.
7. **Rede determinística identificada** para as regras críticas: a skill aponta o que deve ser garantido por lint/teste (não só por prompt). *Esta skill: ESLint contra `authLevel:"anonymous"` + teste de contrato exigindo `requestId`.*

## Métricas de acompanhamento contínuo (após `stable`)

A skill é **artefato vivo** — monitorada após a promoção:

| Métrica | Como medir | Gatilho de revisão |
|---|---|---|
| Taxa de aderência em uso real | rodar o checklist em PRs que usaram a skill (amostragem) | < 85% por 2 sprints → reabrir para `testing` |
| Correções manuais recorrentes no code review | tags nos PRs ("skill-miss") | mesmo item corrigido 3×+ → a skill tem um buraco; iterar |
| Mudança de dependência/stack | ADR nova que afete o padrão (ex.: nova versão de Azure Functions, RO nativo no filesystem) | qualquer → revisar a skill no mesmo PR da ADR |
| Idade sem revisão | data do último update | > 1 trimestre sem toque → revisão de sanidade |

## Por que skills são artefatos vivos (evidência deste exercício)
A v1 desta skill parecia completa, mas o **teste real** revelou 4 buracos (authLevel, shape de erro, requestId, teste) que só apareceram quando um agente cego a gerou. A v2 os fechou. Isso demonstra o princípio: **skill não testada empiricamente é hipótese, não padrão.** A maturidade vem do loop *gerar → medir → reescrever*, repetido até a aderência estabilizar — e continua depois, porque stack, ADRs e agentes evoluem.

## Estado atual desta skill
`azure-functions-endpoint`: **`testing` → pronta para promoção a `stable`**. Critérios **1, 2, 3, 4, 5 e 7 já atendidos** (3 gerações em 2 alvos; aderência 100% na v2 em ambos; iteração 6/10→10/10→12/12 documentada; anti-padrões validados empiricamente; rede determinística identificada). Falta apenas o **critério 6** — revisão formal por um segundo Dev Sênior (Gate 3 do AGENTS.md), que é um gate humano a registrar no PR de promoção.
