# ADR-0001: Escolha do Modelo de LLM

## Status: Aceito

## Contexto

O assistente de IA da NovaTech precisará responder ~192 consultas/dia envolvendo documentação (320 chamados/dia × 60%). Cada query compõe um contexto de entrada com: system prompt estático (~2.000 tokens), metadados do atendente e chamado (~500 tokens), chunks recuperados do RAG (~5 chunks × 500 tokens = 2.500 tokens), histórico de conversa da sessão Teams (~900 tokens — máximo 3 turnos anteriores comprimidos) e a pergunta em si (~200 tokens). Estimativa de saída: ~500 tokens por resposta.

**Consumo estimado por dia:**
- Input: 192 queries × 6.100 tokens = 1.171.200 tokens/dia
- Output: 192 queries × 500 tokens = 96.000 tokens/dia

A NovaTech possui licenças Microsoft 365 E3 e está disposta a provisionar Azure AI Services. O prazo do projeto é de 3 meses. Requisito crítico: o assistente nunca deve inventar informações (guardrail de não-alucinação).

## Versão Inicial da Decisão (antes do devil's advocate)

Azure OpenAI GPT-4o, pela integração nativa com o ecossistema Azure já provisionado.

## Devil's Advocate — Argumento contra GPT-4o

> "Por que não Claude 3.5 Sonnet? Ele possui janela de contexto de 200K tokens (vs 128K do GPT-4o), demonstra superioridade mensurável em seguimento de instruções complexas — exatamente o que os guardrails exigem ('nunca inventar valores', 'sempre citar fonte'). Está disponível no Azure Marketplace via Azure AI Foundry, portanto a 'integração nativa Azure' não é exclusividade do GPT-4o. O custo de input é menor ($3/1M vs $5/1M). Por que escolher o modelo inferior para o requisito mais crítico do projeto?"

**Revisão incorporada:** O argumento forçou a adição de critérios de avaliação explícitos para seguimento de guardrails e a inclusão de um A/B test no Sprint 1. A decisão final mantém GPT-4o como opção primária, mas com condição de reavaliação baseada em métricas mensuráveis.

## Decisão

Utilizar **Azure OpenAI Service com modelo GPT-4o** como LLM principal, com A/B test obrigatório no Sprint 1 comparando GPT-4o vs Claude 3.5 Sonnet (via Azure AI Foundry) especificamente na métrica de taxa de violação de guardrails.

**Critérios de seleção final após A/B test:**
1. Taxa de violação de guardrail de não-invenção (respostas com informações não presentes nos chunks)
2. Taxa de citação correta de fonte
3. Qualidade de resposta em PT-BR com terminologia de logística

Se GPT-4o não superar Sonnet em (1) e (2) com margem > 5%, migrar para Sonnet.

**Estimativa de custo mensal — GPT-4o (Azure OpenAI):**
| Item | Tokens/mês | Custo unitário | Custo/mês |
|------|-----------|----------------|-----------|
| Input | 35.136.000 | $5/1M | $175,68 |
| Output | 2.880.000 | $15/1M | $43,20 |
| **Total** | | | **~$219/mês** |

**Estimativa de custo mensal — Claude 3.5 Sonnet (Azure AI Foundry):**
| Item | Tokens/mês | Custo unitário | Custo/mês |
|------|-----------|----------------|-----------|
| Input | 35.136.000 | $3/1M | $105,41 |
| Output | 2.880.000 | $15/1M | $43,20 |
| **Total** | | | **~$149/mês** |

## Consequências

**Positivas:**
- Integração nativa com Azure AI Search, Azure Monitor, e Microsoft Entra ID — reduz semanas de desenvolvimento
- SLA corporativo da Microsoft com NovaTech já contratado (sem novo processo de procurement)
- Compliance e DLP gerenciados dentro do tenant Azure da NovaTech
- Janela de 128K tokens mais que suficiente para o orçamento de contexto estimado (~6.600 tokens/query)

**Negativas:**
- Custo por token maior que alternativas open-source
- Vendor lock-in no ecossistema Microsoft
- GPT-4o pode ser inferior ao Sonnet em seguimento de instruções complexas para PT-BR (risco mitigado pelo A/B test no Sprint 1)

## Alternativas Consideradas

### Alternativa 1: Claude 3.5 Sonnet via Azure AI Foundry
- **Prós:** 200K tokens de janela, menor custo de input, historicamente superior em seguimento de instruções complexas, melhor para PT-BR
- **Contras:** Integração com Azure AI Search requer adaptação adicional; menos suporte nativo de conectores Microsoft; processo de procurement diferente (mesmo que na Azure, requer habilitação separada)
- **Por que não escolhido inicialmente:** Integração nativa do GPT-4o com o ecossistema Microsoft reduz risco operacional no prazo de 3 meses. Mantido como candidato no A/B test.

### Alternativa 2: Modelos open-source (Llama 3.1 70B via Azure VM + Ollama)
- **Prós:** Custo marginal zero por token; dados nunca saem da infraestrutura NovaTech; sem dependência de APIs externas
- **Contras:** Qualidade de resposta inferior para PT-BR com instruções complexas; requer GPU no Azure (Standard_NC24s_v3 custa ~$3.600/mês); necessidade de fine-tuning para domínio logístico; context window limitada (32K em modelos open-source viáveis); time sem expertise em LLMOps; inviável no prazo de 3 meses
- **Por que descartada:** Custo de infraestrutura maior que SaaS; risco de qualidade inaceitável para o requisito de não-alucinação; complexidade operacional incompatível com 3 meses de prazo

### Alternativa 3: Google Gemini 1.5 Pro via Vertex AI
- **Prós:** 1M tokens de janela, preço competitivo
- **Contras:** Fora do ecossistema Microsoft; NovaTech não tem contratos com Google Cloud; requer novo processo de aprovação legal e de segurança; integração com SharePoint/Teams nativa inexistente
- **Por que descartada:** Conflito direto com a diretriz de usar Azure AI Services da NovaTech
