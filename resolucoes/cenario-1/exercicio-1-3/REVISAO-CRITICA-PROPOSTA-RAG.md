# Revisão Crítica — Proposta de Pipeline de RAG (Exercício 1.3 — Tech Lead)

> **Projeto:** NVT-ASSIST — Assistente de IA para Atendimento NovaTech  
> **Autor:** Tech Lead (Jeferson Parckert)  
> **Data:** 10/06/2026  
> **Contexto:** Revisão da proposta técnica submetida pelo desenvolvedor júnior antes de aprovação arquitetural.

---

## A Proposta Original

O desenvolvedor júnior submeteu a seguinte proposta:

> *"Vamos usar Azure AI Search com embeddings do ada-002. Todos os documentos serão indexados num único índice. Chunking fixo de 512 tokens sem overlap. O LLM recebe os 3 chunks mais similares. Usaremos GPT-4o para geração. O pipeline de ingestão roda manualmente quando alguém lembra de atualizar."*

A proposta tecnicamente funciona — no sentido de que um sistema montado assim vai rodar. O problema é que ele vai rodar mal, e a maior parte das falhas será silenciosa: o assistente vai responder com confiança usando informação errada, desatualizada ou incompleta, e ninguém vai perceber imediatamente.

---

## Parte 1 — Minha Revisão Técnica (antes de usar o Claude)

### Problema 1: Chunking fixo sem overlap é garantia de corte no lugar errado

Usar chunks fixos, sem overlap, aumenta muito a chance de quebrar a informação em um ponto que não faz sentido para a leitura. Em vez de respeitar o fim de uma ideia, de uma regra ou de uma exceção, o corte acontece apenas quando o limite técnico é atingido. Isso enfraquece o contexto e faz o modelo trabalhar com trechos incompletos, o que reduz a qualidade da recuperação e da resposta.

O problema fica mais sério quando o conteúdo depende de continuidade entre parágrafos, listas, tabelas ou instruções sequenciais. Sem sobreposição entre os chunks, partes que deveriam ser lidas em conjunto acabam separadas, e o modelo recebe informação fragmentada. O mais adequado é organizar os cortes por seção lógica e manter uma pequena sobreposição entre trechos adjacentes para preservar o contexto.

---

### Problema 2: 3 chunks não cobre perguntas que cruzam domínios

Definir 3 chunks como limite fixo é pouco para perguntas que exigem combinar mais de uma regra ou mais de um tema ao mesmo tempo. Em cenários assim, a resposta depende da reunião de contextos diferentes, e restringir demais a recuperação força o modelo a responder com informação parcial. Quando isso acontece, a tendência é aumentar o risco de omissão ou de inferência indevida.

Esse modelo também falha no extremo oposto. Quando a pergunta é simples, um Top-K fixo pode trazer trechos que não ajudam em nada, apenas para preencher a quantidade definida. O resultado é mais ruído no contexto e menos precisão na resposta. Uma abordagem melhor é ampliar a base de recuperação, combinar busca por domínio quando necessário e aplicar um critério mínimo de similaridade para descartar conteúdo irrelevante.

---

### Problema 3: Pipeline manual não é pipeline, é esperança

Um processo manual de atualização não atende bem um cenário que exige consistência operacional. Quando a atualização depende de alguém lembrar de executar uma etapa, o sistema passa a depender mais de hábito do que de processo. Em pouco tempo, isso abre espaço para atrasos, desalinhamento entre versões e respostas baseadas em informação desatualizada.

O maior problema não é só a chance de erro, mas a falta de previsibilidade. Sem automação, não há garantia de que o conteúdo disponível para busca reflita o estado mais recente da documentação. Se a expectativa é manter o sistema atualizado dentro de uma janela definida, então a indexação precisa ser tratada como parte da operação, com execução agendada ou acionada por evento, e não como atividade eventual.

---

### Problema 4: ada-002 é o modelo errado para português

O ada-002 não parece a melhor escolha para esse caso porque o desempenho semântico tende a ser mais fraco em contextos fortemente dependentes de português e de terminologia específica de negócio. Quando isso acontece, a busca perde sensibilidade para reconhecer variações de expressão que, para um humano, carregam o mesmo significado. O efeito prático é um retrieval menos preciso e uma seleção pior dos trechos que deveriam compor a resposta.

Além da limitação técnica, existe um problema objetivo de decisão arquitetural: o modelo já foi depreciado. Isso significa iniciar uma solução nova sobre uma base que já nasce com prazo de validade encurtado. Se existe uma alternativa mais atual, com suporte multilíngue e melhor aderência ao idioma do conteúdo, faz mais sentido adotá-la desde o início para evitar retrabalho e dívida técnica desnecessária.
---

## Parte 2 — Revisão do Claude

Depois de fazer minha revisão, abri uma sessão nova no Claude e passei a proposta com o seguinte contexto:

> *"Você é um arquiteto de software sênior especializado em sistemas de RAG. Um desenvolvedor júnior propôs a seguinte arquitetura para um assistente de IA que responde perguntas sobre documentação interna de uma empresa de logística com ~1.250 documentos (~12M tokens estimados): [proposta original]. O sistema será integrado ao Microsoft Teams. Identifique problemas técnicos concretos nessa proposta, com foco em falhas que impactariam a qualidade das respostas em produção."*

O Claude confirmou os problemas 1, 2 e 4 com ângulos complementares, e levantou três pontos que eu não tinha listado.

**Sobre chunking** (confirmação, ângulo diferente):
> *"Para documentos com tabelas de 15+ colunas, o chunking fixo não apenas corta no meio — ele destrói a relação espacial entre dados. Uma linha da tabela de multiplicadores regionais sem o cabeçalho da tabela é uma lista de números sem contexto. Isso é especialmente crítico para tabelas de frete e SLA, que são o núcleo da documentação NovaTech."*

**Documentos escaneados sem OCR** (não estava na minha lista):
> *"A proposta diz 'todos os documentos serão indexados', mas ~15% da base do SharePoint são PDFs escaneados — imagens, não texto. O Azure AI Search sem configuração explícita de OCR indexa esses documentos como texto vazio ou ruído. O efeito é silencioso: os documentos aparecem no índice mas produzem zero chunks úteis. Isso significa que ~120 documentos de uma base de ~800 estarão efetivamente ausentes do assistente, sem nenhum aviso."*

**Context rot em sessões longas no Teams** (não estava na minha lista):
> *"A proposta não menciona o que acontece quando a mesma sessão do Teams tem 8 ou 10 perguntas. O histórico da conversa cresce a cada turno. Se o sistema simplesmente concatena histórico + system prompt + 3 chunks + pergunta nova, em poucos turnos o contexto total pode ultrapassar o orçamento disponível para os chunks — e o que é truncado para caber é exatamente o conteúdo de documentação que não deveria ser sacrificado. Sem estratégia de compressão de histórico, o assistente degrada silenciosamente em sessões longas."*

**Ausência de observabilidade** (não estava na minha lista):
> *"Sem logging de quais chunks foram recuperados para cada query, o time não tem como investigar por que uma resposta foi incorreta. Quando um atendente reclamar que o assistente informou o multiplicador errado para o Norte, não haverá evidência de qual chunk foi usado. Isso torna a melhoria iterativa do pipeline quase impossível."*

---

## Parte 3 — Comparação entre as duas revisões

| # | Problema | Minha revisão | Claude | Observação |
|---|---|:---:|:---:|---|
| 1 | Chunking fixo 512 tokens sem overlap | ✅ | ✅ | Ambos identificaram; Claude focou mais na destruição estrutural de tabelas |
| 2 | Top-3 chunks insuficiente para multi-domínio | ✅ | ✅ | Ambos; Claude adicionou que Top-K fixo também inclui lixo quando poucos chunks são relevantes |
| 3 | Pipeline de ingestão manual | ✅ | ✗ | Só eu — o Claude revisou a proposta com olhar técnico de qualidade e ignorou completamente o risco de processo operacional |
| 4 | ada-002 inferior para PT-BR e depreciado | ✅ | ✅ | Ambos, com ênfases complementares |
| 5 | PDFs escaneados sem OCR | ✗ | ✅ | Só Claude — sabia do dado (15% escaneados) mas não conectei isso como falha explícita da proposta |
| 6 | Context rot em sessões longas no Teams | ✗ | ✅ | Só Claude — não pensei na perspectiva do histórico crescendo por sessão, sendo que o ADR-0002 trata exatamente isso |
| 7 | Ausência de observabilidade do retrieval | ✗ | ✅ | Só Claude — omissão minha, qualquer sistema em produção precisa de logging para ser melhorado |

**O que o Claude encontrou que eu não vi:**

Minha revisão ficou concentrada em retrieval e operação — chunking, top-K, ingestão. O Claude cobriu melhor o estágio de pré-processamento (OCR, extração estrutural de tabelas) e trouxe dois problemas de produção que eu deveria ter listado: o context rot em sessões longas do Teams (que está diretamente relacionado ao que definimos no ADR-0002) e a falta de observabilidade. Esses dois são, honestamente, falhas óbvias para qualquer sistema que vai a produção.

**O que eu encontrei que o Claude não viu:**

O Claude ignorou o pipeline de ingestão manual — que é, na minha avaliação, o problema com maior potencial de impacto no curto prazo. Um assistente com retrieval bom mas informação desatualizada vai gerar erros reais no atendimento ao cliente. O Claude revisou a proposta como um exercício técnico de arquitetura; eu revisei pensando no que vai quebrar na segunda semana de operação.

A lição prática: fazer a revisão humana primeiro importa. O domínio de negócio que eu trago — saber que o PROC-042 e o v2 coexistem sem vigência definida, que três áreas atualizam documentos sem processo unificado — não foi capturado pelo Claude sem esse contexto explícito.

---

## Parte 4 — Proposta Reescrita

### Pipeline de RAG para NVT-ASSIST — Versão Revisada

**Versão:** 2.0 | **Data:** 10/06/2026 | **Revisores:** Tech Lead + Claude

---

#### Stack tecnológico

Mantém o decidido no ADR-0004: Azure AI Search como vector store, GPT-4o para geração. As mudanças são no modelo de embedding e na adição do Azure Document Intelligence para pré-processamento.

| Componente | Escolha | Por quê mudou |
|---|---|---|
| Embedding | `text-embedding-3-small` | Substitui ada-002 depreciado; multilingual; melhor PT-BR |
| Pré-processamento | Azure Document Intelligence | OCR para escaneados; extração estruturada de tabelas |
| Geração | GPT-4o (Azure OpenAI) | Sem mudança |
| Vector store | Azure AI Search | Sem mudança |
| Orquestração | Python + wrapper customizado | Sem mudança |

---

#### Pré-processamento antes da indexação

Todo documento passa pelo Azure Document Intelligence antes de entrar no índice:

- PDFs escaneados (~15% da base) recebem OCR com extração de texto estruturado. Sem isso, ~120 documentos entram no índice como texto vazio — silenciosamente ausentes.
- PDFs com tabelas complexas têm suas tabelas extraídas em formato Markdown (`| Região | Multiplicador |`), preservando a relação entre linhas e colunas. O chunk não vai ter "Sul 1.3 Sudeste 1.1" como sequência de tokens sem estrutura — vai ter a tabela legível.
- Planilhas XLSX têm suas abas convertidas para Markdown tabular antes do chunking, com fórmulas expandidas para valores calculados. O índice armazena `1.3`, não `=B2*C2`.

---

#### Estratégia de chunking

| Tipo de documento | Estratégia | Tamanho-alvo | Overlap |
|---|---|---|---|
| Documentos normativos (POL, PROC) | Por seção (título como delimitador) | 300–600 tokens | 60 tokens |
| Tabelas | Tabela completa como unidade; cabeçalho repetido se a tabela exceder 400 tokens | Variável | Cabeçalho sempre presente |
| FAQ | Por par pergunta–resposta | 100–200 tokens | Sem overlap |
| Wiki Confluence | Por seção de nível 2 (`##`) | 400–700 tokens | 80 tokens |

Cada chunk é indexado com metadados que permitem filtrar por vigência:

```json
{
  "documento_id": "PROC-042-v2",
  "versao": "2.0",
  "data_emissao": "2023-11-10",
  "status": "vigente",
  "area_responsavel": "Comercial",
  "tipo_documento": "procedimento"
}
```

Documentos sem indicação de vigência — como o PROC-042 original que ainda coexiste com o v2 no SharePoint — recebem `status: "em_analise"` e aparecem no contexto com uma nota: `[ATENÇÃO: versão sem vigência confirmada — verificar com responsável antes de usar]`.

Se dois chunks do mesmo documento com versões diferentes aparecerem no resultado, ambos são mantidos no contexto, mas com marcação explícita de qual é a versão anterior e qual é a vigente.

---

#### Retrieval

A pergunta passa por uma classificação de domínio antes do retrieval propriamente dito (GPT-4o com prompt leve, custo de ~$0.001/query):

- Perguntas de domínio único → Top-5 chunks com threshold mínimo de similaridade 0.72.
- Perguntas multi-domínio (ex: devolução + frete + SLA) → retrieval paralelo por categoria, 3 chunks por domínio, máximo 9 chunks no contexto.

O threshold de similaridade 0.72 serve para duas coisas: não incluir chunks irrelevantes quando a pergunta é simples, e sinalizar "pergunta sem cobertura" quando nenhum chunk passa do limiar — o que leva o assistente a dizer explicitamente que não encontrou a informação, em vez de inventar uma resposta.

---

#### Orçamento de contexto por query

| Componente | Tokens estimados | Tipo |
|---|---|---|
| System prompt + guardrails | ~1.800 | Estático |
| Metadados do cliente (tier, contrato) | ~200 | Dinâmico por sessão |
| Chunks recuperados (máx. 5 × 600 tokens) | ~3.000 | Dinâmico por query |
| Histórico da conversa | ~1.500 máx | Dinâmico crescente |
| Pergunta atual | ~200 | Dinâmico por query |
| **Total por query** | **~6.700** | — |

O histórico é monitorado token a token. Quando ultrapassar 5.000 tokens acumulados, os turnos mais antigos são comprimidos: mantém os últimos 3 turnos completos e substitui os anteriores por um resumo gerado via GPT-3.5-turbo (mais barato para essa tarefa). O resumo entra no contexto marcado como `[HISTÓRICO COMPRIMIDO]` para o LLM saber que aquela seção é um resumo, não a conversa literal.

---

#### Ingestão automatizada

| Fonte | Mecanismo | Frequência |
|---|---|---|
| SharePoint Online | Azure AI Search Indexer nativo | A cada 6 horas |
| Confluence | Azure AI Search Indexer via conector | A cada 6 horas |
| Pasta de rede (XLSX) | Azure Data Factory — trigger por modificação de arquivo | Em tempo real |

SLA de ingestão: novo documento disponível no assistente em até 12 horas após publicação. Se um indexer falhar 2 execuções consecutivas, alerta automático no canal de operações do Teams.

---

#### Observabilidade

Cada query registra em Azure Storage:

```
query_id | timestamp | pergunta | chunks_recuperados[] | scores[] | resposta | latencia_ms
```

Um dashboard básico no Azure Monitor mostra: taxa de queries abaixo do threshold de similaridade (pergunta sem cobertura), frequência de chunks `em_analise` no Top-3 (documentos que precisam de curadoria), e distribuição de domínios (informa prioridade de manutenção da base).

Sem isso, a única forma de investigar uma resposta errada é reproduzir manualmente a query e adivinhar o que aconteceu. Com isso, investigação é lookup na tabela de logs.

---

#### Comparativo: proposta original vs revisada

| Aspecto | Original | Revisada |
|---|---|---|
| Embedding | ada-002 (depreciado, EN-focused) | text-embedding-3-small (multilingual, vigente) |
| Chunking | 512 tokens fixos, sem overlap | Por seção, 300–600 tokens, 60 tokens de overlap |
| Top-K | 3 chunks fixos | 5 (domínio único) / até 9 (multi-domínio) + threshold |
| Tabelas | Estrutura perdida na extração | Markdown estruturado via Document Intelligence |
| PDFs escaneados | Texto vazio / ruído | OCR antes da indexação |
| Documentos contraditórios | LLM decide sem informação de vigência | Metadados de vigência + marcação explícita no contexto |
| Ingestão | Manual, sem responsável | Automática a cada 6h, SLA 12h, alerta em falha |
| Sessões longas no Teams | Sem estratégia — context rot garantido | Compressão de histórico após 5.000 tokens |
| Observabilidade | Zero | Logging por query + dashboard de qualidade |

---

#### O que não foi adicionado

A proposta revisada resolve os problemas identificados sem adicionar complexidade que o projeto não justifica:

- **Sem reranking com Cross-Encoder** — threshold de similaridade e classificação de domínio são suficientes para 192 queries/dia. Reranking faria sentido se a base crescesse para 10.000+ documentos.
- **Sem Vector DB separado** — Azure AI Search cobre o caso de uso; adicionar ChromaDB seria infraestrutura sem ganho proporcional.
- **Sem embeddings fine-tuned** — exigiria dataset de 1.000+ pares pergunta-documento que não existe. text-embedding-3-small resolve sem esse custo.
- **Sem LLM-judge para avaliação automática** — útil a médio prazo, mas o logging + avaliação manual cobre o go-live dentro do prazo de 3 meses.
