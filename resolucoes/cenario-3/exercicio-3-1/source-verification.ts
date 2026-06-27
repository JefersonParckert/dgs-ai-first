// src/services/source-verification.ts
//
// Verification loop (camada 2 do harness) — verificação determinística da fonte.
//
// Recebe a resposta estruturada do modelo e confirma se o `source_document`
// citado existe na lista de documentos válidos da NovaTech. Documentos são
// identificados pelos seus IDENTIFICADORES CURTOS (POL-001, PROC-042, ...),
// não pelo título completo. Se a fonte não estiver na lista, a resposta é
// marcada como SUSPEITA e deve ser roteada para revisão humana (HITL).
//
// Esta função é PURA e DETERMINÍSTICA: não loga, não tem efeitos colaterais.
// O logging (pino) e o roteamento HITL acontecem no call site — ver harness-design.md.
// Isso a torna trivialmente testável e é a contraparte determinística do que
// o prompt faz de forma probabilística.

/**
 * Identificadores curtos dos documentos válidos da NovaTech (fonte: Anexo A).
 * Fonte de verdade única — se um documento entra/sai da base, muda-se aqui.
 */
export const VALID_DOCUMENT_IDS = [
  "POL-001",
  "PROC-042",
  "PROC-042-v2",
  "SLA-2024",
  "FAQ-Atendimento",
] as const;

export type ValidDocumentId = (typeof VALID_DOCUMENT_IDS)[number];

/**
 * Conjunto normalizado (uppercase) para lookup O(1) e comparação case-insensitive.
 * `FAQ-Atendimento` tem case misto; normalizar evita falso-negativo por caixa.
 */
const VALID_IDS_UPPER: ReadonlySet<string> = new Set(
  VALID_DOCUMENT_IDS.map((id) => id.toUpperCase()),
);

export interface SourceVerificationResult {
  /** Entrada original recebida do modelo (para auditoria/log). */
  raw: string | null;
  /** Identificador extraído e normalizado da citação (ou null se não houver). */
  documentId: string | null;
  /** true quando o identificador pertence à lista de documentos válidos. */
  isValid: boolean;
  /** true quando a resposta NÃO pode ser confiada sem revisão (→ HITL). */
  suspicious: boolean;
  /** Motivo legível — vira mensagem de log e justificativa do roteamento. */
  reason: string;
}

/**
 * Extrai o identificador do documento de uma citação livre.
 *
 * Aceita formatos como:
 *   "POL-001"               → "POL-001"
 *   "POL-001, seção 3.2"    → "POL-001"
 *   "FAQ-Atendimento, item 32" → "FAQ-Atendimento"
 *
 * Pega o primeiro token antes de vírgula ou espaço — os IDs válidos não contêm
 * espaços, então o que vier depois é seção/sufixo descritivo.
 */
function extractDocumentId(raw: string): string | null {
  const token = raw.trim().split(/[\s,]+/)[0];
  return token.length > 0 ? token : null;
}

/**
 * Verifica se a fonte citada na resposta existe na lista de documentos válidos.
 *
 * @param sourceDocument valor do campo `source_document` da resposta estruturada.
 *   Pode ser string, vazio, ou ausente (null/undefined) — todos tratados.
 * @returns veredito estruturado; `suspicious === true` deve disparar HITL.
 */
export function verifySourceDocument(
  sourceDocument: string | null | undefined,
): SourceVerificationResult {
  // Fonte ausente — guardrail determinístico: nenhuma resposta segue sem fonte.
  if (sourceDocument == null || sourceDocument.trim().length === 0) {
    return {
      raw: sourceDocument ?? null,
      documentId: null,
      isValid: false,
      suspicious: true,
      reason: "source_document ausente ou vazio",
    };
  }

  const documentId = extractDocumentId(sourceDocument);

  if (documentId == null) {
    return {
      raw: sourceDocument,
      documentId: null,
      isValid: false,
      suspicious: true,
      reason: "não foi possível extrair um identificador de documento da citação",
    };
  }

  // Comparação por igualdade EXATA (case-insensitive), nunca por prefixo:
  // "PROC-042" é prefixo de "PROC-042-v2"; um startsWith aceitaria
  // "PROC-042-v9" inexistente. O Set garante membership estrita.
  const isValid = VALID_IDS_UPPER.has(documentId.toUpperCase());

  return {
    raw: sourceDocument,
    documentId,
    isValid,
    suspicious: !isValid,
    reason: isValid
      ? `fonte '${documentId}' validada contra a lista de documentos da NovaTech`
      : `fonte '${documentId}' não consta na lista de documentos válidos`,
  };
}
