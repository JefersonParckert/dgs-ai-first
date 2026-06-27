# Revisão crítica da arquitetura gerada com IA — NovaTech Assistant

> **Cenário 3 — Exercício 3.2 (Tech Lead) · Tópico: Revisão Crítica de Outputs de IA**
> **Ferramenta:** Claude (chat) como co-reviewer.
> **Contexto:** vários artefatos do projeto foram gerados com apoio de IA. Faltam 2 semanas para a demo da diretoria. Esta é a revisão de riscos antes do go-live.

**Artefatos sob revisão:**
- AGENTS.md — gerado pelo Claude, refinado 4×, última versão com 15 páginas.
- 3 skills — a **Foundation** foi refinada após testes; as outras duas (Domain e Artifact) foram usadas **sem refinamento**.
- Pipeline de ingestão e query endpoint — **~60–70% gerados pelo Copilot**.
- System prompt — iterado **6×**, **sem documentar** por que cada mudança foi feita.

---

## Parte 1 — Minha avaliação de riscos (ANTES do Claude)

Avaliação independente, por artefato. Para cada um: **qual o risco de ter sido gerado por IA** e **o que verificar antes do go-live**. Severidade = (probabilidade × impacto no go-live).

### A. AGENTS.md (4 refinos, 15 páginas) — Severidade: **Média**

- **Risco.** 15 páginas é grande demais para um arquivo que o agente lê inteiro antes de cada geração. Quatro refinos sucessivos tendem a **acumular contradições internas** (uma seção diz X, outra adicionada depois diz Y) e *bloat* — regras importantes diluídas no meio (o mesmo *lost-in-the-middle* que afeta o assistente afeta o agente lendo o AGENTS.md). Risco moderado, não existencial: o AGENTS.md **já foi testado** no cenário 2 (aderência ≈13,5/14 na v2).
- **O que verificar.** (1) Varredura de **contradições entre seções** (ex.: budget de contexto vs. exemplos de código; regras de log duplicadas). (2) Reteste de aderência com os 2 prompts canônicos do cenário 2 — confirmar que o crescimento não degradou a aderência. (3) Conferir que o **checklist de geração** no fim ainda cobre as regras críticas (source_document, pino, Zod, context budget).

### B. Skills Domain e Artifact (sem refinamento) — Severidade: **Alta**

- **Risco.** A skill **Foundation foi refinada após testes; as outras duas não**. Skill não testada = padrão de codegen não validado: pode gerar outputs **inconsistentes** com o AGENTS.md (ex.: a skill `create-rag-endpoint` instruindo um layout diferente do `handler/validator/response-builder`, ou a skill de teste gerando `jest` em vez de `Vitest`). Como skills são reaplicadas a cada geração, um defeito se **propaga em escala**. Conecta direto ao incidente já observado: o módulo de feedback gerado pelo Copilot violou o AGENTS.md (console.log, sem Zod, logou PII) — sinal de que a camada de orientação ao codegen não está fechada.
- **O que verificar.** Submeter cada skill não refinada ao **mesmo ciclo de teste da Foundation** (gerar um artefato real com a skill → conferir contra o AGENTS.md e o Anexo C). Priorizar a skill de endpoint RAG e a de testing-patterns, que tocam o caminho de resposta e a rede de testes.

### C. Pipeline de ingestão + query endpoint (60–70% Copilot) — Severidade: **Alta / Crítica**

- **Risco.** Este é o **caminho que produz as respostas** — e os testes internos mostraram **12% de respostas incorretas** (alucinação, doc desatualizado, chunk errado). Código majoritariamente gerado por IA tende a ter bugs sutis em: dedup/ranqueamento de chunks, respeito ao **context budget da ADR-0002**, tratamento dos **documentos contraditórios** (PROC-042 vs v2 — ADR-0003), e preenchimento garantido de `source_document`. Cobertura de testes ~75% — pode estar cobrindo o caminho feliz e não as armadilhas.
- **O que verificar.** (1) Rodar a **eval sobre `golden-queries.json`** (Anexo C, `/prompts/eval/`) para **quantificar** onde os 12% se concentram (retrieval? geração? versão errada do documento?). (2) Code review focado no retrieval multi-domínio e na regra da ADR-0003 (nunca interpolar versões; apresentar ambas marcando vigente). (3) Confirmar que o caminho de resposta sempre emite `source_document` (liga com a função de verificação do Ex. 3.1).

### D. System prompt (6 iterações, sem changelog) — Severidade: **Alta (governança)**

- **Risco.** Seis iterações **sem registrar o porquê** = **impossível rollback informado**. Se a iteração 6 piorou um comportamento que a 3 acertava, ninguém sabe o que mudou nem por quê — não dá para voltar com segurança. Além disso, **viola a própria convenção do projeto**: o Anexo C define `/prompts/prompt-changelog.md` com data, autor, motivo e resultado esperado para *toda* mudança. É risco de governança puro: o artefato mais sensível do sistema não tem rastreabilidade.
- **O que verificar.** (1) **Reconstruir o changelog retroativamente** com quem lembrar das mudanças (mesmo incompleto, melhor que zero) e **congelar** o prompt sob controle de versão a partir de agora. (2) Snapshot da versão atual como baseline de rollback. (3) Daqui pra frente, mudança de prompt entra no HITL do harness (Ex. 3.1, camada 4): aprovação do Tech Lead + registro obrigatório.

### Resumo da minha avaliação

| Artefato | Severidade | Verificação central |
|---|---|---|
| Skills Domain/Artifact sem refino | Alta | Testar como a Foundation foi testada |
| Pipeline + query endpoint (Copilot) | Alta/Crítica | Eval em golden-queries + review do retrieval/ADR-0003 |
| System prompt sem changelog | Alta (governança) | Reconstruir changelog + congelar baseline |
| AGENTS.md 15 páginas | Média | Varrer contradições + reteste de aderência |

---

## Parte 2 — Complementação do Claude (co-reviewer)

Usei o Claude como segundo revisor, pedindo explicitamente: *"que riscos eu (humano) deixei passar nesta lista?"*. Riscos **adicionais** que ele levantou e eu não tinha registrado:

1. **Meta-risco do dataset de avaliação.** Eu propus usar `golden-queries.json` como régua — mas **quem validou o golden dataset?** Se ele também foi gerado por IA (provável), as "respostas esperadas" podem estar erradas, e eu estaria medindo qualidade contra um gabarito furado. → *Validar uma amostra do golden contra o Anexo A (fonte de verdade) antes de confiar na eval.* **Risco que eu não tinha visto.**
2. **Interação entre artefatos, não só cada um isolado.** Eu avaliei artefato por artefato. O Claude apontou que o risco real está na **composição**: skill não testada + código Copilot + prompt sem changelog se reforçam — uma regra fraca no AGENTS.md vira skill ruim, que vira código ruim. A revisão deveria seguir o **caminho de uma query de ponta a ponta**, não silos.
3. **Risco de automation bias na própria revisão.** As 4 refinações do AGENTS.md e as 6 do prompt foram aceitas progressivamente sem critério de parada documentado — sinal de que o time pode estar **aceitando outputs de IA acriticamente** ("mais uma iteração e fica bom"). É um risco de *processo*, não só de artefato.
4. **PII e segurança no código Copilot.** O Claude reforçou que o incidente do módulo de feedback (logou e-mail do atendente) pode **não ser isolado** — varrer o pipeline/endpoint por `console.log`, `require` dinâmico e log de dados pessoais, não só por bugs funcionais.

---

## Parte 3 — Comparação honesta (humano × Claude)

| | Eu identifiquei | Claude identificou | Avaliação |
|---|:--:|:--:|---|
| Skills sem refino = inconsistência | ✅ | ✅ | Concordância — era o risco mais óbvio. |
| Prompt sem changelog = sem rollback | ✅ | ✅ | Concordância; eu já liguei à convenção do Anexo C. |
| Código Copilot no caminho de resposta | ✅ | ✅ | Concordância; Claude **acrescentou** o ângulo de PII/segurança (#4). |
| AGENTS.md bloat/contradição | ✅ | ✅ (parcial) | Concordância. |
| **Golden dataset não validado** | ❌ | ✅ | **Claude pegou um furo meu** — eu confiei na régua sem questioná-la. |
| **Risco de composição (fim-a-fim)** | ❌ | ✅ | **Claude melhorou meu método** — eu avaliei em silos. |
| **Automation bias no processo** | ❌ | ✅ | Risco de processo que eu não tinha enquadrado. |

**Conclusão honesta:** convergimos nos 4 riscos de artefato. O Claude **não** apenas confirmou minha lista — ele acrescentou um risco que invalidaria minha própria estratégia de medição (o golden dataset) e corrigiu meu método (avaliar o fluxo, não cada peça isolada). Não foi "eu já sabia tudo": incorporei os pontos 1 e 2 na priorização abaixo.

---

## Parte 4 — Priorização (2 semanas) e risco residual

Critério: **maior redução de risco no go-live por unidade de tempo**. O que mata a demo é o assistente **responder errado com confiança** (os 12%). Tudo que ataca isso vem primeiro.

### Semana 1 — o que reduz mais risco

1. **Validar o golden dataset (1 dia).** Conferir uma amostra de `golden-queries.json` contra o Anexo A. *Vem antes de tudo* porque é a régua das outras verificações (risco que o Claude levantou).
2. **Eval do caminho de resposta sobre o golden validado (2 dias).** Quantificar onde estão os 12% (retrieval × geração × versão de documento). Ataca o risco Crítico (artefato C) com dado, não achismo.
3. **Testar as 2 skills sem refinamento (1–2 dias).** Gerar artefato real com cada uma e conferir contra AGENTS.md + Anexo C. Ataca o risco Alto (B) e a causa-raiz do incidente de feedback.
4. **Reconstruir o changelog do prompt + congelar baseline (0,5 dia).** Ataca o risco de governança (D); barato e destrava rollback informado.

### Semana 2 — fechar gaps e validar

5. **Code review focado** do pipeline/endpoint: ADR-0003 (versões contraditórias), context budget (ADR-0002), e varredura de PII/`console.log`/`require` dinâmico (ponto #4 do Claude).
6. **Varredura de contradições no AGENTS.md** + reteste de aderência (artefato A).
7. **Plugar o HITL** (Ex. 3.1): respostas suspeitas/baixa confiança em tema sensível na fila de revisão para a demo rodar com rede de segurança mesmo com 12% residual.

### Risco residual aceito explicitamente

- **AGENTS.md 15 páginas:** aceito como risco **Médio** para a demo — já validado a ≈13,5/14 no cenário 2; refatorar/enxugar fica para **pós-go-live**. Mitigação: o checklist final do arquivo cobre as regras críticas.
- **Refatorar os 30–40% de código Copilot fora do caminho de resposta** (ex.: detalhes do indexer não ligados à qualidade da resposta): aceito como residual; entra no backlog pós-demo.
- **Automation bias no processo (ponto #3 do Claude):** não dá para "consertar" em 2 semanas; mitigação imediata é institucionalizar o **HITL para mudanças de prompt/base** (Ex. 3.1) como critério de parada. Tratamento de fundo fica para depois.

**Postura de go-live:** a demo pode acontecer **com o HITL ativo** como rede para o residual de 12%, desde que os itens 1–4 da Semana 1 estejam verdes. Sem isso, não recomendo expor o assistente à diretoria.
