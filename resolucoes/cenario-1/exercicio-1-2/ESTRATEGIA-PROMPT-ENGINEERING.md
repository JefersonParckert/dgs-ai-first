# Estratégia de Prompt Engineering como Artefato de Arquitetura
## Projeto: Assistente de IA NovaTech

> **Exercício 1.2 — Tech Lead | Cenário-Âncora 1**
> Referência às decisões: ADR-0001 (GPT-4o/Azure OpenAI), ADR-0002 (gerenciamento de contexto), ADR-0004 (Azure AI Search).

---

## 1. Prompts como Código — Governança e Versionamento

### 1.1 Onde ficam os prompts no repositório

```
infra-novatech-assistant/
└── prompts/
    ├── README.md                          ← este documento (convenções)
    ├── NVT-ASSIST-system-v1.0.0.md        ← system prompt estático, versão 1
    ├── NVT-ASSIST-system-v2.0.0.md        ← system prompt estático, versão 2 (atual)
    └── NVT-ASSIST-fallback-v1.0.0.md      ← prompt de fallback quando contexto vazio
tests/
    ├── test_prompt_harness.py             ← runner de testes automatizados
    └── test-cases-NVT-ASSIST-v1.json      ← perguntas + respostas esperadas + critérios
```

**Regra:** Prompts ficam no diretório `/prompts` do repositório principal, versionados via Git junto com o código da aplicação. Nenhum prompt pode existir como string hardcoded no código de aplicação — sempre referenciado por path e carregado em runtime.

### 1.2 Convenção de nomenclatura

```
{PRODUTO}-{COMPONENTE}-{TIPO}-v{MAJOR}.{MINOR}.{PATCH}.md
```

| Campo | Valores válidos | Exemplo |
|-------|----------------|---------|
| PRODUTO | `NVT-ASSIST` (assistente NovaTech) | `NVT-ASSIST` |
| COMPONENTE | `system`, `fallback`, `rerank`, `compress` | `system` |
| TIPO | Omitido para prompts completos; `fragment` para snippets reutilizáveis | — |
| VERSION | SemVer: MAJOR muda guardrails ou identidade; MINOR muda formato/instruções; PATCH corrige wording | `v2.0.0` |

**Por que SemVer para prompts?** Uma mudança de MAJOR significa que comportamentos observáveis mudam — métricas de QA podem ser invalidadas e testes precisam ser rebaseados. MINOR e PATCH são retrocompatíveis para os critérios de avaliação existentes.

### 1.3 Processo de alteração

| Tipo de mudança | Quem pode propor | Quem aprova | O que é obrigatório antes de merge |
|----------------|-----------------|-------------|-------------------------------------|
| PATCH (wording) | Desenvolvedor | Tech Lead | Regressão no test harness (100% pass) |
| MINOR (formato, instrução) | Desenvolvedor, Product Specialist | Tech Lead | Regressão + revisão manual de 10 casos |
| MAJOR (guardrail, identidade) | Tech Lead, Product Specialist | Tech Lead + QA Lead | Regressão + suite completa de QA + sign-off do Product Specialist |

**Regra:** Toda mudança de prompt passa por Pull Request, com diff do prompt no body do PR. A pipeline de CI/CD executa `test_prompt_harness.py` automaticamente em PRs que modificam arquivos em `/prompts/`.

### 1.4 Rastreabilidade

Cada deploy do assistente deve logar qual versão de prompt está ativa:
```json
{
  "deployment_id": "nvt-assist-prod-20240315",
  "system_prompt_version": "NVT-ASSIST-system-v2.0.0",
  "test_cases_version": "test-cases-NVT-ASSIST-v1",
  "model": "gpt-4o",
  "model_version": "2024-02-15-preview"
}
```

Isso garante que incidentes de produção possam ser correlacionados com a versão do prompt ativa no momento — essencial para debug de regressões.

---

## 2. Anatomia do Contexto — Engenharia de Contexto por Query

O contexto que o modelo recebe a cada query não é "o prompt" — é uma composição de múltiplas partes com diferentes ciclos de vida, tamanhos e prioridades. A arquitetura define explicitamente o orçamento de cada parte (alinhado com ADR-0002).

### 2.1 Diagrama de composição

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXTO COMPLETO POR QUERY               │
│                    Budget máximo: ~9.800 tokens               │
├─────────────────────────────────────────────────────────────┤
│  [1] SYSTEM PROMPT (ESTÁTICO)                    ~2.000 tok  │
│      • Identidade e papel                                    │
│      • Guardrails (regras de comportamento)                  │
│      • Instruções de formato de resposta                     │
│      • Prioridade entre fontes conflitantes                  │
│      • Instrução de fallback (sem resposta)                  │
│      Frequência de mudança: raramente (MAJOR/MINOR release)  │
├─────────────────────────────────────────────────────────────┤
│  [2] METADADOS DO CHAMADO (DINÂMICO)               ~500 tok  │
│      • Tier do cliente (Gold/Silver/Standard)                │
│      • ID do chamado e timestamp                             │
│      • ID do atendente (para log de auditoria)               │
│      Frequência de mudança: por query (cada chamado)         │
├─────────────────────────────────────────────────────────────┤
│  [3] CHUNKS RECUPERADOS (DINÂMICO)              ~4.000 tok   │
│      • Máximo 8 chunks × 500 tokens                          │
│      • Posicionados ANTES do meio do contexto               │
│        (mitiga efeito lost in the middle)                    │
│      • Ordenados por relevância: mais relevante primeiro     │
│      • Cada chunk inclui metadado: fonte, seção, versão,     │
│        data_vigencia                                         │
│      Frequência de mudança: por query (retrieval fresh)      │
├─────────────────────────────────────────────────────────────┤
│  [4] HISTÓRICO COMPRIMIDO DA SESSÃO (DINÂMICO)  ~1.500 tok  │
│      • Turnos 1–3: texto completo                            │
│      • Turnos 4+: comprimidos para 1 frase por turno         │
│      • Reset por relevância (similaridade < 0.3)             │
│      • Reset por volume (> 1.500 tokens após compressão)     │
│      Frequência de mudança: cresce dentro da sessão Teams    │
├─────────────────────────────────────────────────────────────┤
│  [5] PERGUNTA ATUAL (DINÂMICO)                    ~300 tok   │
│      • Posicionada ao final do contexto (alta atenção)       │
│      • Precedida de delimitador explícito                    │
│      Frequência de mudança: por query                        │
├─────────────────────────────────────────────────────────────┤
│  [6] BUFFER DE RESPOSTA (RESERVADO)             ~1.500 tok   │
│      • Não é input — é headroom reservado para output        │
│      • Garante que a resposta não seja truncada              │
│      Não é parte do contexto de entrada                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Tabela de orçamento

| # | Componente | Tipo | Tokens reservados | % do budget |
|---|-----------|------|------------------|-------------|
| 1 | System prompt | **Estático** | 2.000 | 20% |
| 2 | Metadados do chamado | Dinâmico | 500 | 5% |
| 3 | Chunks recuperados (RAG) | Dinâmico | 4.000 | 41% |
| 4 | Histórico comprimido da sessão | Dinâmico, crescente | 1.500 | 15% |
| 5 | Pergunta atual | Dinâmico | 300 | 3% |
| 6 | Buffer de geração | Reservado (output) | 1.500 | 15% |
| | **Total** | | **9.800** | **100%** |

**Contexto de 9.800 tokens vs janela de 128K do GPT-4o:** Operar com budget controlado não é limitação técnica — é decisão de engenharia. Usar toda a janela disponível de forma não gerenciada levaria a context rot progressivo (informação irrelevante acumulada), maior custo por query e imprevisibilidade de qualidade. O budget explícito garante que o comportamento do modelo seja previsível e testável.

### 2.3 Posicionamento no contexto (lost in the middle)

```
[system prompt]                     ← alta atenção (início)
[metadados do chamado]              ← alta atenção
[chunks mais relevantes — top 3]    ← posição de alta atenção
[chunks de suporte — restantes]     ← meio (atenção reduzida — aceitável para suporte)
[histórico comprimido da sessão]    ← meio a fim
[PERGUNTA ATUAL]                    ← alta atenção (fim)
```

O chunk com maior score de relevância vai na posição 3 (imediatamente após metadados), não no meio dos 8 chunks. A pergunta vai sempre ao final — posição de maior atenção do modelo.

---

## 3. Enforcement: Probabilístico vs Determinístico

### 3.1 O problema

Guardrails definidos no system prompt são instruções em linguagem natural — o modelo tende a segui-los, mas não é garantido. São enforcement **probabilístico**: "sempre cite a fonte" funciona bem em média, mas pode falhar em casos extremos (contexto cheio, pergunta ambígua, jailbreak não intencional).

Algumas verificações podem e devem ser aplicadas fora do modelo, em código, onde o comportamento é determinístico e não depende da interpretação do LLM.

### 3.2 Mapeamento por guardrail

| Guardrail (definido pelo Product Specialist) | Onde enforçar | Mecanismo | Justificativa |
|----------------------------------------------|---------------|-----------|---------------|
| **(1) Sempre citar fonte** | **Prompt + Código** | Prompt: instrução explícita com formato `[Fonte: DOC-XXX, seção Y.Y]`. Código: regex pós-resposta valida presença do padrão. Resposta sem citação é rejeitada antes de chegar ao atendente. | Citação tem formato estruturado verificável. Verificação determinística é viável e barata. |
| **(2) Nunca inventar prazos ou valores numéricos** | **Prompt** (probabilístico) | Instrução "use apenas os valores numéricos presentes nos chunks fornecidos; se não encontrar o valor exato, diga que não encontrou". | Verificação determinística de números requer base de dados de referência completa — inviável no MVP. O guardrail probabilístico cobre > 95% dos casos; falhas residuais são capturadas no processo de feedback do atendente. |
| **(3) Quando não encontrar, dizer explicitamente** | **Prompt + Código** | Prompt: instrução explícita com frase-padrão. Código: se chunks recuperados têm score < 0.5, injetar metadado `"low_confidence": true` no contexto — o prompt instrui o modelo a ativar o comportamento de fallback quando vir esse metadado. | A condição de baixa confiança é detectável no pipeline de retrieval antes de chamar o LLM. |
| **(4) Responder em português formal** | **Prompt** (probabilístico) | Instrução no system prompt. Verificação de idioma em código é possível mas de baixo valor de negócio: o modelo GPT-4o em PT-BR dificilmente responde em outro idioma quando instruído. | Falhas de idioma são raras e detectadas facilmente pelo atendente. Custo de implementação > benefício. |

### 3.3 Arquitetura de harness (camada pós-LLM)

```
┌─────────────────────────────────────────────────────────────┐
│                     PIPELINE POR QUERY                       │
│                                                              │
│  Retrieval ──→ Composição de ──→  LLM         ──→ Harness  │
│  (Azure AI     contexto            (GPT-4o)       Pós-LLM  │
│   Search)      (ADR-0002)          (ADR-0001)     (código) │
│                                                    │         │
│                                                    ├── [DET] Valida citação de fonte (regex)
│                                                    ├── [DET] Valida ausência de termos proibidos
│                                                    ├── [DET] Verifica tamanho mínimo da resposta
│                                                    ├── [PROB] Log de confiança do retrieval
│                                                    └── Resposta liberada para o atendente
│                                                              │
│                                              Se validação falhar:
│                                              → Resposta substituída por mensagem padrão de fallback
│                                              → Alerta logado para revisão do QA
└─────────────────────────────────────────────────────────────┘
```

**[DET]** = Determinístico (código).  
**[PROB]** = Probabilístico (confia no modelo, apenas loga para análise).

### 3.4 Termos proibidos (enforcement determinístico)

O harness verifica que a resposta **não contém** nenhum desses padrões:
- Frases de certeza fabricada sem fonte: `"com certeza"`, `"definitivamente"`, `"sempre será"` sem `[Fonte:` precedendo
- Referência a tiers inexistentes: `"Platinum"`, `"Diamond"`, `"VIP"` (que não existem no SLA-2024)
- Valores numéricos sem citação de fonte na mesma frase (regex: número seguido de unidade sem `[Fonte:` nos 200 tokens anteriores)

---

## 4. Referências Cruzadas

| Decisão | ADR de referência |
|---------|------------------|
| Modelo e custo por token | [ADR-0001](../exercicio-1-1/ADR-0001-escolha-modelo-llm.md) |
| Orçamento de contexto e budget por componente | [ADR-0002](../exercicio-1-1/ADR-0002-gerenciamento-contexto.md) |
| Tratamento de documentos contraditórios no contexto | [ADR-0003](../exercicio-1-1/ADR-0003-documentos-contraditorios.md) |
| Stack de retrieval (Azure AI Search) | [ADR-0004](../exercicio-1-1/ADR-0004-build-vs-buy-pipeline-rag.md) |
