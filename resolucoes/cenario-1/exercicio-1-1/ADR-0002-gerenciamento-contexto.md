# ADR-0002: Estratégia de Gerenciamento de Contexto

## Status: Aceito

## Contexto

O assistente rodará integrado ao Microsoft Teams. Atendentes farão múltiplas perguntas em uma mesma sessão (ex: abrir um chamado e fazer 5–8 perguntas sequenciais sobre SLA, frete e política de devolução para o mesmo cliente). O modelo GPT-4o possui janela de 128K tokens, mas **janela grande não significa contexto ilimitado de qualidade**: informação no meio de contextos longos é menos processada que nas extremidades (efeito *lost in the middle*), e sessões longas acumulam informação irrelevante que degrada a qualidade das respostas subsequentes (*context rot*).

Perguntas do domínio NovaTech frequentemente cruzam múltiplos temas simultaneamente (ex: "Qual o SLA de resolução para um cliente Gold que quer devolver uma carga perigosa que veio da região Norte?"). Essas perguntas multi-domínio exigem chunks de categorias distintas (SLA-2024, POL-001, PROC-042-v2), e uma estratégia ingênua de "top-N por similaridade global" pode trazer chunks redundantes do mesmo documento, deixando outros domínios sem representação.

## Versão Inicial da Decisão (antes do devil's advocate)

5 chunks de 500 tokens por query; reset de sessão a cada 10 turnos.

## Devil's Advocate — Argumento contra a versão inicial

> "5 chunks de 500 tokens = 2.500 tokens de contexto documentado. Para uma pergunta como 'Qual o prazo, o multiplicador de frete e o SLA para cliente Gold na região Norte pedindo devolução de carga especial?', você precisa de chunks de TRÊS documentos diferentes (POL-001, PROC-042-v2, SLA-2024). Com 5 chunks totais e busca por similaridade, há alta probabilidade de trazer 3–4 chunks do documento mais similar e apenas 1 do resto — você vai perder cobertura de algum domínio. Além disso, 'reset a cada 10 turnos' é arbitrário: context rot começa antes, especialmente se o atendente fizer perguntas muito diferentes dentro da mesma sessão. O que você faz quando o turno 6 é sobre um cliente completamente diferente?"

**Revisão incorporada:** O argumento forçou a adição de recuperação multi-domínio explícita (até 3 chunks por categoria) e uma estratégia de compressão de histórico baseada em relevância, não em contagem de turnos.

## Decisão

### 1. Orçamento de contexto por query

| Componente | Tipo | Tokens reservados |
|-----------|------|------------------|
| System prompt | Estático | 2.000 |
| Metadados do chamado (tier do cliente, ID do atendente, timestamp) | Dinâmico | 500 |
| Chunks recuperados (ver estratégia abaixo) | Dinâmico | 4.000 (máx 8 chunks × 500) |
| Histórico comprimido da sessão | Dinâmico, crescente | 1.500 (máx) |
| Pergunta atual | Dinâmico | 300 |
| Buffer para geração da resposta | — | 1.500 |
| **Total máximo** | | **~9.800 tokens/query** |

A janela de 128K é mantida como capacidade de emergência, não como budget padrão. Operar com budget controlado previne degradação silenciosa de qualidade.

### 2. Estratégia de recuperação multi-domínio

Classificação automática da pergunta em domínios antes do retrieval:
- **Domínio SLA:** palavras-chave como "prazo", "tempo de resposta", "resolução", tier de cliente
- **Domínio Frete:** palavras-chave como "frete", "custo", "multiplicador", "kg", região
- **Domínio Devolução:** palavras-chave como "devolução", "devolver", "retorno", "prazo de devolução"

**Regra de retrieval:**
- Se pergunta detectada em 1 domínio: top 5 chunks por similaridade semântica global
- Se pergunta detectada em 2+ domínios: top 3 chunks por domínio identificado (até 8 chunks totais, priorizando diversidade de fonte sobre similaridade)
- Reranking final por score composto: (similaridade × 0.7) + (frescor do documento × 0.3)

### 3. Gerenciamento do histórico de sessão (context rot)

O histórico de conversa Teams será gerenciado pela regra de **janela deslizante com compressão semântica**:

- **Turnos 1–3:** incluir full text no contexto
- **A partir do turno 4:** comprimir turnos antigos com instrução "Resuma em 1 frase o que foi perguntado e respondido em cada turno anterior"
- **Gatilho de reset por relevância:** se a pergunta atual tem similaridade cossenoidal < 0.3 com o histórico comprimido, descartar histórico completamente e iniciar contexto limpo (indicativo de mudança de assunto/cliente)
- **Gatilho de reset por volume:** se histórico comprimido ultrapassar 1.500 tokens, forçar reset e informar o atendente: "Iniciando nova sessão — histórico anterior não está disponível"

### 4. Tratamento do efeito *lost in the middle*

Posicionamento dos chunks no contexto:
```
[system prompt]
[metadados do chamado]
[CHUNKS MAIS RELEVANTES — posição inicial, alta atenção]
[chunks de suporte — meio do contexto]
[histórico comprimido da sessão]
[pergunta atual — posição final, alta atenção]
```

Chunks ranqueados por relevância são injetados no início do bloco de contexto, não no meio.

## Consequências

**Positivas:**
- Budget controlado previne context rot silencioso
- Retrieval multi-domínio garante cobertura em perguntas complexas
- Compressão semântica preserva contexto útil sem degradação progressiva
- Reset por relevância resolve o caso do atendente que troca de chamado sem iniciar nova conversa

**Negativas:**
- Lógica de classificação de domínio adiciona latência (~50ms estimados)
- Compressão de histórico consome tokens adicionais (~200 tokens/rodada de compressão)
- Reset automático por baixa similaridade pode frustrar atendente se falso positivo (ex: pergunta reformulada sobre o mesmo tema)
- Complexidade de implementação maior que abordagem simples de "top-5 global"

## Alternativas Consideradas

### Alternativa 1: Top-N global sem classificação de domínio (abordagem simples)
- **Prós:** Implementação trivial, latência mínima
- **Contras:** Perguntas multi-domínio invariavelmente sub-representam categorias menos similares lexicalmente; risco operacional alto dado que 35% das dúvidas são sobre prazos, 25% frete e 20% devolução — frequentemente combinados no mesmo chamado
- **Por que descartada:** Baixa cobertura em perguntas compostas é inaceitável para o SLA de qualidade

### Alternativa 2: Usar toda a janela de 128K sem budget
- **Prós:** Nenhuma lógica adicional, zero risco de truncamento
- **Contras:** Context rot progressivo confirmado em pesquisas (Liu et al., 2023, "Lost in the Middle"); custo linear com volume de histórico; sem previsibilidade de qualidade; ingestão de 12M tokens de documentação impossibilita "jogar tudo" — o retrieval continua sendo necessário
- **Por que descartada:** Janela grande não previne degradação; orçamento de contexto explícito é prática de engenharia necessária

### Alternativa 3: Resetar sessão a cada pergunta (stateless)
- **Prós:** Zero context rot; implementação simples; cada resposta independente
- **Contras:** Atendente perde capacidade de fazer perguntas de follow-up ("e para o mesmo cliente, qual o frete?"); experiência degradada; 15% dos chamados são escalados justamente por perguntas complexas que precisam de contexto acumulado
- **Por que descartada:** Elimina utilidade do assistente para chamados complexos
