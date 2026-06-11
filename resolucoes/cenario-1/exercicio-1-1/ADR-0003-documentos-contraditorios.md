# ADR-0003: Tratamento de Documentos Contraditórios

## Status: Aceito

## Contexto

A NovaTech possui documentação com contradições explícitas confirmadas. O caso mais crítico identificado: **PROC-042** (Procedimento de Cálculo de Frete Especial, versão original) e **PROC-042-v2** (versão revisada), ambos com mesma numeração de procedimento e sem indicação clara de qual é o vigente. Os multiplicadores regionais diferem entre as versões. O atendimento hoje resolve essa ambiguidade "perguntando para quem sabe" — comportamento que o assistente não pode replicar.

Se o pipeline de RAG indexar ambos os documentos sem tratamento, os dois poderão ser recuperados simultaneamente para a mesma pergunta. O LLM, sem instrução explícita, pode:
1. Misturar valores das duas versões sem perceber a contradição
2. Escolher arbitrariamente uma versão sem indicar qual escolheu
3. Gerar uma "média" dos valores que não existe em nenhum documento

Qualquer dos três comportamentos é mais perigoso que admitir a contradição explicitamente.

Além do PROC-042, foram identificados ao menos 3 outros procedimentos com versões contraditórias na base de documentos da NovaTech.

## Versão Inicial da Decisão (antes do devil's advocate)

Indexar apenas a versão mais recente por data de modificação de arquivo. Com um único documento por ID de procedimento no índice, o problema de contradição não existiria.

## Devil's Advocate — Argumento contra a versão inicial

> "Data de modificação de arquivo não é data de vigência de negócio. O PROC-042-v2 pode ter sido criado no sistema antes do PROC-042 original — nomes de arquivo e timestamps de sistema não refletem a hierarquia documental da NovaTech. Você estaria silenciando a contradição, não resolvendo. O atendente receberia uma resposta confiante baseada possivelmente na versão errada, sem nenhum aviso. O requisito crítico do projeto é exatamente o oposto: nunca selecionar silenciosamente — sempre com rastreabilidade. Além disso, se ambas as versões tiverem a mesma data de modificação (co-existência no mesmo SharePoint), qual critério de desempate você usa?"

**Revisão incorporada:** O argumento forçou o reconhecimento de que o problema não é de deduplicação técnica, mas de governança de vigência. A solução passou a exigir metadado explícito de `data_vigencia` como campo de negócio — distinto de qualquer timestamp de sistema — e uma fila de revisão humana para casos sem metadado. A Camada 3 (instrução no system prompt) foi adicionada para garantir transparência ao atendente mesmo quando ambas as versões são recuperadas simultaneamente.

## Decisão

### Camada 1: Pipeline de ingestão — metadados obrigatórios

Durante a ingestão, todo documento que compartilhe identificador de procedimento (ex: PROC-042) com outro documento já indexado **deve** ter campo de vigência explícito preenchido. O pipeline implementará as seguintes regras:

```
SE documento.id_procedimento == documento_existente.id_procedimento
   E documento.conteudo != documento_existente.conteudo
ENTÃO:
   SE documento.data_vigencia IS NULL:
       status = "BLOQUEADO_REVISAO_HUMANA"
       enviar para fila de revisão manual
   SENÃO:
       status = "ATIVO"
       documento_existente.status = "SUPERSEDIDO"
       manter ambos indexados com status diferenciado
```

Campos de metadado obrigatórios para documentos em conflito:
- `data_vigencia`: data a partir da qual o documento entra em vigor
- `status`: ATIVO | SUPERSEDIDO | BLOQUEADO_REVISAO_HUMANA
- `supersede`: referência ao ID do documento que este substitui (se aplicável)
- `area_responsavel`: Operações, Compliance ou Comercial

### Camada 2: Estratégia de retrieval — priorização por vigência

O pipeline de retrieval ordena chunks por: (similaridade semântica × 0.6) + (frescor por data_vigencia × 0.4) para documentos com status ATIVO. Documentos com status SUPERSEDIDO têm score multiplicado por 0.1 — ainda recuperáveis mas despriorizados.

### Camada 3: Instrução no system prompt — transparência ao atendente

Quando o retrieval retornar chunks com mesmo `id_procedimento` e status diferente:

```
INSTRUÇÃO NO SYSTEM PROMPT:
"Quando você receber chunks de duas versões do mesmo procedimento (identificadas pelo campo 
status: ATIVO vs SUPERSEDIDO), apresente AMBAS ao atendente da seguinte forma:
- Indique a versão vigente (status ATIVO, data_vigencia mais recente)
- Indique a versão anterior (status SUPERSEDIDO)
- NUNCA combine ou interpole valores das duas versões
- Recomende que o atendente confirme com o supervisor se houver dúvida sobre a versão aplicável"
```

### Tratamento do PROC-042 vs PROC-042-v2 (caso imediato)

Este conflito específico deve ser resolvido **antes** do go-live através de ação de Discovery:
- Ação de discovery: identificar junto à área de Operações qual versão é vigente
- Se PROC-042-v2 for vigente: marcar PROC-042 como SUPERSEDIDO com data_vigencia da v2
- Se nenhuma for definitivamente vigente: ambas ficam com status BLOQUEADO_REVISAO_HUMANA até decisão formal
- Em nenhum cenário o pipeline vai a produção com ambos os documentos em status ATIVO e sem data_vigencia

## Consequências

**Positivas:**
- Transparência: o atendente sabe quando existe contradição, em vez de receber uma resposta silenciosamente errada
- Rastreabilidade: todo documento contraditório tem registro de quem aprovou e quando
- Prevenção proativa: o bloqueio na ingestão força resolução do conflito antes de contaminar respostas
- Alinhamento com req. do Product Specialist: "documentos contraditórios devem mostrar ambas as versões com indicação de data"

**Negativas:**
- Fila de revisão manual cria dependência humana no pipeline de ingestão — pode ser gargalo se a NovaTech publicar documentos frequentemente com conflitos não resolvidos
- Adiciona campos de metadado que os documentos atuais não possuem — requer enriquecimento manual ou semi-automático durante a fase de discovery
- Risco de underindexing: documentos contraditórios bloqueados ficam fora do sistema até resolução, o que pode ser problemático se for o único documento sobre um tópico

## Alternativas Consideradas

### Alternativa 1: Indexar apenas o documento mais recente por ID
- **Prós:** Implementação simples; sem ambiguidade; sem lógica especial no retrieval
- **Contras:** "Mais recente" por data de modificação de arquivo não corresponde necessariamente à versão de negócio vigente — o PROC-042-v2 pode ter sido criado antes do PROC-042 no sistema; documento "antigo" pode conter seções válidas que a versão nova não cobre; silencia contradições em vez de resolver — a equipe de atendimento continua sem saber que existe uma versão anterior
- **Por que descartada:** Risco silencioso de aplicar regras desatualizadas é pior que expor a contradição explicitamente

### Alternativa 2: Delegar a decisão ao LLM (instrução genérica "use o mais recente")
- **Prós:** Nenhuma lógica adicional no pipeline
- **Contras:** Sem metadados de vigência no documento, o LLM não tem base objetiva para determinar qual é mais recente; o modelo pode interpolar valores (ex: multiplicador médio entre 1.3 e outro valor não documentado); ausência de data no documento é exatamente o problema do PROC-042 vs v2 — o LLM simplesmente não consegue resolver sem metadado externo; gera respostas que parecem confiantes mas são fabricadas
- **Por que descartada:** Delegar julgamento de vigência a um LLM sem dado estruturado de vigência é exatamente o cenário de alucinação que o projeto quer evitar

### Alternativa 3: Excluir documentos contraditórios até resolução formal
- **Prós:** Zero risco de mistura; forçar resolução antes do go-live
- **Contras:** Se o único documento sobre multiplicadores regionais for o PROC-042 em conflito, o assistente ficará sem resposta para 25% das dúvidas (fretes); exclusão total pode ser pior que transparência gerenciada
- **Por que descartada:** Parcialmente adotada (documentos com status BLOQUEADO ficam fora até resolução), mas substituída pela opção de manter documentos SUPERSEDIDOS com baixo score ao invés de exclusão total
