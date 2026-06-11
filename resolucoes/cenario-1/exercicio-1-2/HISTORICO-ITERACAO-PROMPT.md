# Histórico de Iteração — Prompt NVT-ASSIST

> Demonstra a evolução do system prompt de v1.0.0 para v2.0.0, com feedback do Claude atuando como revisor crítico.

---

## Iteração 1 — Avaliação da v1.0.0 pelo Claude

### Prompt enviado ao Claude

```
Você é um engenheiro de software sênior especializado em sistemas de RAG e prompt engineering. 
Analise criticamente o system prompt abaixo para um assistente de IA de atendimento de 
uma empresa de logística. Identifique problemas, ambiguidades e riscos concretos que este 
prompt causaria em produção. Seja específico — cite exemplos de inputs que causariam 
comportamento indesejado.

PROMPT A REVISAR:
---
Você é o assistente de atendimento da NovaTech, empresa de logística.
Responda perguntas sobre procedimentos, SLAs e regras de frete.
Use apenas as informações dos documentos fornecidos.
Cite a fonte. Se não souber, diga que não sabe.
---

CONTEXTO DO PROJETO:
- O assistente opera no Microsoft Teams, integrado ao sistema de chamados
- Recebe chunks de documentação via RAG (Azure AI Search)
- Os chunks incluem metadados: fonte, seção, versão, data_vigencia
- Existem documentos contraditórios na base (PROC-042 v1 vs v2 com multiplicadores diferentes)
- Tiers de cliente: Gold, Silver, Standard — o SLA varia por tier
- Guardrails obrigatórios: (1) sempre citar fonte, (2) nunca inventar valores, 
  (3) fallback explícito quando sem resposta, (4) português formal
```

### Feedback do Claude (problemas identificados)

**1. "Se não souber, diga que não sabe" é perigoso**

> "O problema não é que o modelo vai 'não saber' — o modelo sempre vai ter uma resposta. O risco é que ele vai confundir 'não tem nos chunks fornecidos' com 'não conheço o assunto'. Um GPT-4o treinado com dados de logística pode perfeitamente responder sobre procedimentos de devolução de carga refrigerada usando conhecimento de treinamento, não os chunks NovaTech. O prompt atual não deixa explícito que a única fonte admissível são os chunks fornecidos — 'Use apenas as informações dos documentos fornecidos' é facilmente ignorado quando o modelo está em modo de completar uma resposta útil."

**Ação tomada:** REGRA 2 (proibição de invenção) e REGRA 4 (fallback com orientação de escalada) foram adicionadas com linguagem mais restritiva.

**2. Sem instrução de prioridade para versões conflitantes**

> "Quando o pipeline recuperar um chunk do PROC-042 v1.0 (multiplicador Norte: 1.6) e um chunk do PROC-042-v2 (multiplicador Norte: 1.8), o modelo vai resolver a contradição de forma não determinística — pode usar uma, pode usar a outra, pode até tentar calcular uma média. Não há instrução sobre o que fazer. Com a frase 'cite a fonte', o modelo vai citar uma das fontes — mas qual? A resposta muda dependendo da ordem em que os chunks aparecem no contexto (efeito lost in the middle). Este é exatamente o cenário de risco que o cliente NovaTech tem documentado."

**Ação tomada:** REGRA 3 adicionada com instrução explícita de usar `data_vigencia` como critério de prioridade e alertar o atendente sobre a versão anterior com valores diferentes.

**3. Tier do cliente não está sendo usado ativamente**

> "O prompt não instrui o modelo a olhar para os metadados do chamado. Se o atendente perguntar 'qual o SLA de resolução?', o modelo pode retornar os três tiers (Gold/Silver/Standard) da tabela — o que é tecnicamente correto mas operacionalmente inútil, porque o atendente precisa saber o SLA do cliente específico que está no chamado. O chunk de SLA contém os três tiers, o metadado do chamado contém o tier do cliente, mas o prompt não instrui a cruzar essas informações."

**Ação tomada:** Seção "INSTRUÇÃO SOBRE TIER DO CLIENTE" adicionada com instrução explícita de usar `tier_cliente` dos metadados do chamado para filtrar a resposta.

**4. Sem delimitadores de seção no prompt**

> "Um prompt de produção que vai crescer ao longo do projeto precisa de estrutura. Sem headers e seções, a próxima pessoa que for fazer uma alteração MINOR vai inserir conteúdo no lugar errado. Além disso, em prompts mais longos, o modelo tende a prestar mais atenção em conteúdo estruturado com headers claros. Use markdown com headers para separar identidade, regras, formato e instruções de contexto."

**Ação tomada:** Prompt v2.0.0 organizado em seções com headers markdown: IDENTIDADE E ESCOPO, CONTEXTO DA CONSULTA, DOCUMENTOS FORNECIDOS, REGRAS OBRIGATÓRIAS, FORMATO DE RESPOSTA.

**5. Ausência de checklist interno para o modelo**

> "Para modelos de alta capacidade como GPT-4o, uma instrução de 'checklist interno antes de responder' funciona como chain-of-thought implícito para verificação de guardrails. Não é um trick — é uma instrução explícita de auto-verificação que reduz taxa de violação de guardrails em ~15-20% em benchmarks internos de seguimento de instrução. Custo: ~50 tokens. ROI: significativo para um guardrail que é hard requirement do cliente."

**Ação tomada:** CHECKLIST INTERNO adicionado ao final do prompt como instrução de auto-verificação não exibida ao usuário.

---

## Iteração 2 — Revisão da v2.0.0 pelo Claude (devil's advocate final)

### Prompt enviado ao Claude

```
Revise a versão 2.0.0 do prompt abaixo. Identifique se há inconsistências internas, 
instruções que se contradizem, ou riscos residuais que não foram endereçados. 
Seja específico sobre o que ainda pode falhar.

[conteúdo completo do NVT-ASSIST-system-v2.0.0.md]
```

### Feedback do Claude na v2.0.0

**Risco residual 1: REGRA 2 usa "nunca inventar" mas REGRA 4 não é suficientemente específica**

> "A REGRA 4 diz 'diga explicitamente que não encontrou e oriente a escalar'. Mas ela não instrui o modelo sobre o que fazer quando PARTE da pergunta tem resposta nos chunks e PARTE não tem. Ex: 'Qual o prazo de devolução e o procedimento de avaria para carga refrigerada?' — a devolução tem resposta, a avaria refrigerada não. O modelo pode silenciosamente omitir que a segunda parte não foi respondida. A instrução de 'responder o que encontrou e explicitar o que não encontrou' está ausente."

**Decisão:** Aceitar o risco residual para MVP v2.0.0. Caso de uso de pergunta composta parcialmente respondida será endereçado em v2.1.0 com instrução explícita de resposta particionada.

**Risco residual 2: Checklist interno pode aumentar verbosidade**

> "O CHECKLIST INTERNO com '[ ] Toda informação factual tem citação?' pode, em modelos menos capazes ou prompts menos elaborados, gerar saídas onde o modelo mostra o checklist na resposta. A instrução '(não mostrar ao usuário)' é suficiente para GPT-4o em condições normais, mas pode falhar em edge cases de contexto cheio quando as instruções do início são comprimidas pelo efeito lost in the middle."

**Decisão:** Aceitar. A posição do checklist no final do prompt (posição de alta atenção) mitiga o risco de lost in the middle. Monitorar nas primeiras 2 semanas de produção — se o checklist aparecer em respostas, mover para seção REGRAS OBRIGATÓRIAS.

---

## Comparativo v1.0.0 vs v2.0.0

| Dimensão | v1.0.0 | v2.0.0 |
|----------|--------|--------|
| Tamanho | ~80 tokens | ~1.850 tokens |
| Guardrail de não-invenção | Implícito ("use apenas...") | Explícito (REGRA 2) |
| Tratamento de versões conflitantes | Ausente | REGRA 3 com data_vigencia |
| Fallback quando sem resposta | "diga que não sabe" | REGRA 4 com orientação de escalada |
| Uso de metadados do chamado | Não mencionado | Seção CONTEXTO DA CONSULTA + INSTRUÇÃO DE TIER |
| Formato de resposta | Livre | Estruturado (Resposta / Fontes / Observações) |
| Verificabilidade pelo harness | Baixa (sem padrão) | Alta ([Fonte: DOC, seção X]) |
| Auto-verificação interna | Ausente | CHECKLIST INTERNO |
| Estrutura do prompt | Parágrafo único | Seções com headers markdown |
