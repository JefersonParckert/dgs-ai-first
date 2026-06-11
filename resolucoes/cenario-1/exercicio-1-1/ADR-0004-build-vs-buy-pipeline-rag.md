# ADR-0004: Build vs Buy para o Pipeline de RAG

## Status: Aceito

## Contexto

O pipeline de RAG precisa ingerir documentos de três fontes heterogêneas: SharePoint (~800 PDFs/DOCXs, atualização mensal), Confluence (~400 páginas wiki, atualização semanal) e pasta de rede (~50 planilhas XLSX, atualização mensal). Algumas fontes apresentam desafios técnicos específicos: PDFs com tabelas complexas (15+ colunas), documentos escaneados (~15% da base, requerem OCR), wiki com links internos e macros customizadas, planilhas com fórmulas interdependentes.

**Restrições do projeto:**
- Prazo: 3 meses (discovery + desenvolvimento + go-live)
- NovaTech já possui Microsoft 365 E3 + Azure AI Services provisionado
- Equipe do projeto: time DB1 + atendimento NovaTech (sem equipe de MLOps dedicada)
- Requisito de atualização: novos documentos disponíveis em até 24h após publicação
- Integração com Teams + SharePoint (ecossistema Microsoft)

**Opções em avaliação:**
1. **Build:** LangChain/LlamaIndex + ChromaDB ou FAISS (open-source, controle total)
2. **Buy:** Azure AI Search + Azure OpenAI + conectores nativos Microsoft (managed, integrado)

## Versão Inicial da Decisão (antes do devil's advocate)

Build com LangChain + ChromaDB para manter controle total sobre chunking, retrieval e reranking, evitando vendor lock-in no ecossistema Microsoft.

## Devil's Advocate — Argumento contra o Build

> "Você tem 3 meses de prazo total — discovery, desenvolvimento e go-live. Só o conector SharePoint Online exige registro de aplicativo OAuth e gestão de permissões (~2 semanas). OCR para os ~120 documentos escaneados exige integração adicional. Uptime do ChromaDB em produção é responsabilidade do time DB1, que não tem MLOps. Isso é 4–5 semanas gastas antes de escrever uma linha de lógica de domínio — classificação de domínio, compressão de histórico, tratamento de contradições. O 'controle total' que o Build oferece é sobre a infraestrutura de dados, não sobre o produto que a NovaTech está comprando. Qual o risco de chegar ao mês 3 com os conectores prontos mas a qualidade do RAG ainda não testada em produção?"

**Revisão incorporada:** O argumento redefiniu o critério de decisão: de "controle técnico" para "entrega do produto dentro do prazo". A decisão passou a ser Buy + wrapper de orquestração customizado — o Azure AI Search resolve conectores e OCR, enquanto a camada Python implementa a lógica proprietária das ADR-0002 e ADR-0003 que não existe nativamente na plataforma. O build completo foi descartado não por razões técnicas, mas por incompatibilidade com as restrições reais do projeto.

## Decisão

**Azure AI Search + Azure OpenAI (opção Buy)**, com wrapper de orquestração customizado para a lógica de negócio específica (tratamento de documentos contraditórios, retrieval multi-domínio definido na ADR-0002, instruções de vigência da ADR-0003).

**Justificativa pelos constraints do projeto:**

| Fator | Build (LangChain + ChromaDB) | Buy (Azure AI Search) |
|-------|-----------------------------|-----------------------|
| Conector SharePoint Online | Implementar do zero (~2 semanas) | Nativo, configuração de 1–2 dias |
| Conector Confluence | Implementar do zero (~1 semana) | Conector disponível via Azure Data Factory |
| OCR para PDFs escaneados | Implementar com Azure Document Intelligence ou Tesseract | Azure Document Intelligence nativo no Azure AI Search |
| Manutenção do vector store | Time DB1 responsável por uptime do ChromaDB | SLA 99.9% gerenciado pela Microsoft |
| Integração com Teams | Requer desenvolvimento de bot separado | Azure Bot Service integrado nativo |
| Atualização em 24h | Pipeline de ingestão custom + agendamento | Indexer incremental nativo com schedule por fonte |
| Expertise necessária | LangChain, ChromaDB, DevOps | Azure AI Search, configuração declarativa |
| Custo de infra (sem token) | VM para ChromaDB ~$150/mês + desenvolvimento | Incluído no Azure AI Services provisionado |

**Onde customizar (wrapper sobre o Buy):**
A lógica proprietária definida nas ADRs anteriores não existe nativamente no Azure AI Search e será implementada como camada de orquestração Python:
- Classificação de domínio da pergunta antes do retrieval (ADR-0002)
- Priorização por `data_vigencia` e `status` no reranking (ADR-0003)
- Compressão semântica do histórico de sessão (ADR-0002)
- Validação de guardrails na resposta (determinístico, camada pós-LLM)

## Consequências

**Positivas:**
- Conectores nativos para SharePoint e Confluence reduzem de ~3 semanas para ~3 dias o trabalho de ingestão
- Azure Document Intelligence resolve OCR sem implementação adicional
- SLA gerenciado: sem responsabilidade de uptime do vector store para a equipe DB1
- Requisito de atualização em 24h: indexer incremental do Azure AI Search suporta agendamento horário nativamente
- Sem novo processo de procurement: NovaTech já provisionará Azure AI Services
- Equipe não precisa aprender LangChain/ChromaDB — tecnologias que não existirão no stack pós-projeto

**Negativas:**
- Menor controle sobre algoritmo de chunking interno do Azure AI Search (mitigado pela possibilidade de pré-processar e ingerir texto já chunkado via API)
- Vendor lock-in: migração futura para outra solução exige reindexação completa
- Custo por query de Azure AI Search ao escalar além de 192 queries/dia — se volume triplicar, custo escala proporcionalmente
- Debugging de comportamento do retrieval mais difícil que em ChromaDB (caixa menos transparente)

## Alternativas Consideradas

### Alternativa 1: LangChain + ChromaDB (Build completo)
- **Prós:** Controle total sobre chunking, retrieval, reranking; open-source com zero custo de licença; portabilidade (não fica preso ao Azure)
- **Contras para este projeto específico:**
  - Conector SharePoint Online: Microsoft exige OAuth com permissões de aplicativo registrado — implementação não trivial (~2 semanas)
  - OCR para ~120 documentos escaneados: integrar Tesseract ou Azure Document Intelligence por conta própria
  - Uptime do ChromaDB: DB1 responsável por alta disponibilidade do vector store em produção
  - Requisito de 24h: pipeline de ingestão incremental exige lógica de detecção de mudanças no SharePoint e Confluence
  - Com 3 meses de prazo, as semanas gastas nesses conectores e na infraestrutura são diretamente subtraídas do tempo de refinamento de qualidade do RAG
- **Por que descartada:** O custo de build dos conectores e da infraestrutura inviabiliza o prazo de 3 meses. A NovaTech não está contratando infraestrutura de dados — está contratando um assistente de IA funcional.

### Alternativa 2: Buy completo sem customização (Azure AI Search out-of-the-box)
- **Prós:** Tempo de entrega mínimo; zero código de orquestração
- **Contras:** Não implementa retrieval multi-domínio (ADR-0002), tratamento de contradições (ADR-0003), ou compressão semântica de histórico — todos requisitos definidos pelo Product Specialist
- **Por que descartada:** Buy sem customização não atende os requisitos funcionais do produto. A camada de orquestração customizada é necessária independentemente do vector store escolhido.

### Alternativa 3: FAISS + código manual (build mais simples)
- **Prós:** Mais leve que ChromaDB; código de retrieval completamente transparente
- **Contras:** FAISS é biblioteca, não servidor — requer implementação de persistência, API, e atualização incremental do índice do zero; os mesmos problemas de conectores e OCR da Alternativa 1 se aplicam
- **Por que descartada:** Mesmas objeções da Alternativa 1, com complexidade adicional de implementar persistência do índice
