# NVT-ASSIST-system-v1.0.0

> **Status:** Depreciado — substituído por v2.0.0
> **Origem:** Prompt inicial fornecido pelo desenvolvedor como base para melhoria (exercício 1.2)
> **Tamanho estimado:** ~80 tokens

---

## Prompt

```
Você é o assistente de atendimento da NovaTech, empresa de logística.
Responda perguntas sobre procedimentos, SLAs e regras de frete.
Use apenas as informações dos documentos fornecidos.
Cite a fonte. Se não souber, diga que não sabe.
```

---

## Problemas identificados nesta versão

Os problemas abaixo foram identificados durante a iteração com o Claude (ver `HISTORICO-ITERACAO-PROMPT.md`):

1. **Identidade vaga:** "assistente de atendimento" não define escopo — o modelo pode interpretar que deve ajudar com qualquer assunto relacionado a atendimento, incluindo reclamações, triagem emocional, etc.

2. **Guardrail (2) ausente:** Não há instrução explícita para nunca inventar prazos ou valores numéricos. "Cite a fonte" não é suficiente — o modelo pode citar uma fonte existente com um valor fabricado.

3. **Guardrail (3) impreciso:** "Se não souber, diga que não sabe" é ambíguo. O modelo pode interpretar que "não sabe" significa usar conhecimento geral. A instrução correta é: "se não encontrar a informação nos documentos fornecidos, diga explicitamente e oriente a escalar para o supervisor".

4. **Sem instrução de prioridade entre fontes conflitantes:** Quando dois chunks de versões diferentes do mesmo procedimento estão no contexto (PROC-042 vs PROC-042-v2), o modelo não sabe qual priorizar. Isso é um risco concreto dado que a NovaTech tem documentos contraditórios identificados.

5. **Sem formato de resposta definido:** A resposta pode vir em qualquer estrutura — parágrafo, lista, tabela — dificultando a verificação determinística do harness e a leitura pelo atendente.

6. **Sem instrução sobre metadados do chamado:** O modelo não sabe que receberá informações sobre o tier do cliente e que deve usá-las para contextualizar a resposta (ex: SLA específico para o tier do cliente).

7. **Sem delimitador de chunks:** O prompt não instrui o modelo sobre como os documentos são fornecidos (formato, delimitadores), tornando o parsing implícito e frágil.

8. **Custo de tokens desperdiçado:** 80 tokens de prompt deixam ~9.720 tokens não utilizados do budget de 9.800. Mas o problema real é o oposto: a brevidade vem ao custo de não especificar comportamentos críticos — o modelo preenche a ambiguidade com comportamento default que pode não ser o desejado.
