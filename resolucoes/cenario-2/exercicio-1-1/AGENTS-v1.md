# AGENTS.md — NovaTech Assistant

> **Versão:** v1 (primeira iteração — antes do teste com Copilot)
> **Mantenedor:** Tech Lead
> **Escopo deste arquivo:** Este é o documento-constituição do projeto. Todo agente de IA (GitHub Copilot, Claude Code) DEVE ler este arquivo antes de gerar qualquer artefato. Contém decisões duráveis derivadas das ADRs da fase de discovery (ADR-0001 a ADR-0004).

---

## Project Overview

O **NovaTech Assistant** é um assistente de IA que responde perguntas do time de atendimento da NovaTech (transportadora/logística) sobre **SLAs, frete e devoluções**, usando RAG sobre a documentação interna da empresa.

- **Usuário primário:** atendente de suporte da NovaTech (responde a clientes via chamado).
- **Restrição central de produto:** o assistente **nunca inventa informações**, **sempre cita a fonte** e, quando não encontra resposta, **diz explicitamente**.
- **Base documental:** 847 documentos válidos consolidados (12 com contradições pendentes de resolução pelo Compliance).
- **Volume estimado:** ~192 consultas/dia que envolvem documentação (320 chamados/dia × 60%).

As decisões de produto detalhadas (guardrails, glossário de domínio) ficam na seção **Product Rules & Guardrails** (escrita pelo Product Specialist).

---

## Tech Stack & Architecture

### Stack autorizada

| Camada | Tecnologia | Observação |
|--------|-----------|-----------|
| Backend / API | TypeScript + Azure Functions v4 (HTTP triggers) | `strict: true` no tsconfig |
| Bot | TypeScript + Bot Framework | Interface no Microsoft Teams |
| Painel web | React | Dashboard de métricas e histórico |
| Validação | Zod | Input e output de todos os endpoints |
| Logging | pino | Nunca usar `console.log` |
| Testes | Vitest | Unit + integração |
| Infra como código | Bicep | `infra/` (estado narrativo nesta fase) |
| LLM | Azure OpenAI GPT-4o | ADR-0001 |
| Retrieval | Azure AI Search | ADR-0004 |

### Arquitetura (4 componentes)

1. **Pipeline de ingestão** (`src/pipeline/`) — extração, chunking, embedding e indexação.
2. **API do assistente** (`src/functions/`) — Azure Functions + Azure AI Search + Azure OpenAI.
3. **Bot do Teams** (`src/bot/`) — interface conversacional via Bot Framework.
4. **Painel web** (`src/web/`) — React.

Código de negócio compartilhado fica em `src/services/` e tipos/config/erros em `src/shared/`.

### Gerenciamento de contexto (ADR-0002)

Toda chamada ao LLM deve respeitar o **orçamento de contexto**:

- System prompt: ~4K tokens.
- Chunks recuperados: ~8K tokens (até 8 chunks de ~500 tokens cada).
- Histórico de sessão: comprimido, limitado a ~3 turnos.
- A janela de 128K do GPT-4o é capacidade de emergência, não budget padrão.

Retrieval multi-domínio: perguntas que cruzam 2+ domínios (SLA, Frete, Devolução) devem trazer chunks de cada domínio, não só os mais similares globalmente.

### Documentos contraditórios (ADR-0003)

Documentos com mesmo identificador de procedimento têm metadado de vigência (`data_vigencia`, `status`). O assistente prioriza a versão ATIVA mais recente e informa quando existe versão anterior. Nunca interpola valores entre versões.

---

## Coding Standards

- TypeScript com `strict: true`.
- Validar input e output com Zod.
- Usar pino para logs (nunca `console.log`).
- Tratar erros adequadamente.
- Seguir a estrutura de pastas do Anexo C.
- Mensagens de commit no formato Conventional Commits.

---

## Product Rules & Guardrails (Product Specialist)

> _A ser escrito pelo Product Specialist (exercício PS 2.3)._

## Testing Standards (QA)

> _A ser escrito pelo QA (exercício QA 2.1)._

## Project Management Rules (Delivery Manager)

> _A ser escrito pelo Delivery Manager (exercício DM 2.3)._

---

## Build & Deploy

- **Branch strategy:** feature branches **locais** (não há remoto nesta fase).
- **"Abrir PR":** criar a branch e escrever a descrição do PR como arquivo markdown em `docs/pull-requests/PR-NNNN.md` (objetivo, mudanças, checklist de validation gates). Revisão é simulada localmente.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- **CI:** `.github/workflows/ci.yml` roda lint + test + build.
- **Deploy:** estado narrativo nesta fase — nenhum recurso Azure real é provisionado.
