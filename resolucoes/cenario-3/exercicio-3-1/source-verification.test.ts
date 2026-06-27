// tests/integration/source-verification.test.ts (Vitest — projeto NÃO usa jest)
import { describe, it, expect } from "vitest";
import {
  verifySourceDocument,
  VALID_DOCUMENT_IDS,
} from "./source-verification";

describe("verifySourceDocument", () => {
  it("should accept a valid document id cited as-is", () => {
    // Arrange
    const source = "POL-001";
    // Act
    const result = verifySourceDocument(source);
    // Assert
    expect(result.isValid).toBe(true);
    expect(result.suspicious).toBe(false);
    expect(result.documentId).toBe("POL-001");
  });

  it("should accept every id in the canonical valid list", () => {
    for (const id of VALID_DOCUMENT_IDS) {
      const result = verifySourceDocument(id);
      expect(result.isValid, `expected '${id}' to be valid`).toBe(true);
    }
  });

  it("should strip a section suffix and validate the bare identifier", () => {
    // Arrange — formato real visto em staging (exercício PS 3.1, resposta #1)
    const source = "POL-001, seção 3.2";
    // Act
    const result = verifySourceDocument(source);
    // Assert
    expect(result.documentId).toBe("POL-001");
    expect(result.isValid).toBe(true);
  });

  it("should strip an item suffix from a FAQ citation (case mixed)", () => {
    const result = verifySourceDocument("FAQ-Atendimento, item 32");
    expect(result.documentId).toBe("FAQ-Atendimento");
    expect(result.isValid).toBe(true);
  });

  it("should validate ignoring letter case", () => {
    const result = verifySourceDocument("faq-atendimento");
    expect(result.isValid).toBe(true);
  });

  it("should flag PROC-042-v2 as valid but NOT accept a non-existent variant", () => {
    // Guarda contra validação por prefixo: PROC-042 é prefixo de PROC-042-v2.
    expect(verifySourceDocument("PROC-042-v2").isValid).toBe(true);
    expect(verifySourceDocument("PROC-042").isValid).toBe(true);

    const fake = verifySourceDocument("PROC-042-v9");
    expect(fake.isValid).toBe(false);
    expect(fake.suspicious).toBe(true);
  });

  it("should mark a hallucinated source as suspicious", () => {
    // Resposta #4 do exercício PS 3.1: política de danos inventada, sem fonte real.
    const result = verifySourceDocument("POL-DANOS-2024");
    expect(result.isValid).toBe(false);
    expect(result.suspicious).toBe(true);
    expect(result.reason).toContain("não consta");
  });

  it("should mark a missing source (null) as suspicious", () => {
    const result = verifySourceDocument(null);
    expect(result.isValid).toBe(false);
    expect(result.suspicious).toBe(true);
    expect(result.documentId).toBeNull();
    expect(result.reason).toContain("ausente");
  });

  it("should mark an empty / whitespace source as suspicious", () => {
    expect(verifySourceDocument("").suspicious).toBe(true);
    expect(verifySourceDocument("   ").suspicious).toBe(true);
  });

  it("should treat the literal 'Nenhuma' citation as suspicious", () => {
    // Resposta #4 citou "Nenhuma" como fonte — não é um documento válido.
    const result = verifySourceDocument("Nenhuma");
    expect(result.isValid).toBe(false);
    expect(result.suspicious).toBe(true);
  });

  it("should preserve the raw input for auditing", () => {
    const result = verifySourceDocument("  POL-001, seção 3.2  ");
    expect(result.raw).toBe("  POL-001, seção 3.2  ");
  });
});
