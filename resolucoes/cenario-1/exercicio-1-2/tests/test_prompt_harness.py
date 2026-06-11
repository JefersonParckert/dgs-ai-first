"""
test_prompt_harness.py — NovaTech Assistant Prompt Test Runner

Gerado com apoio do GitHub Copilot (demonstração do conceito).

Objetivo: dado um system prompt, um conjunto de perguntas e critérios de avaliação,
enviar cada pergunta ao LLM e verificar se a resposta atende os critérios definidos.

Uso:
    python test_prompt_harness.py \
        --prompt prompts/NVT-ASSIST-system-v2.0.0.md \
        --cases tests/test-cases-NVT-ASSIST-v1.json \
        --output tests/results/run-{timestamp}.json

Dependências:
    pip install openai>=1.0.0 rich  # openai SDK compatível com Azure OpenAI
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuração de integração com Azure OpenAI (via variáveis de ambiente)
# ---------------------------------------------------------------------------
# AZURE_OPENAI_ENDPOINT=https://{resource}.openai.azure.com/
# AZURE_OPENAI_KEY={chave}
# AZURE_OPENAI_DEPLOYMENT=gpt-4o
#
# Em CI/CD, essas variáveis são injetadas via Azure Key Vault + pipeline secret.
# ---------------------------------------------------------------------------


def load_prompt(prompt_path: str) -> str:
    """Carrega o system prompt de um arquivo .md, extraindo apenas o bloco de código."""
    content = Path(prompt_path).read_text(encoding="utf-8")
    # Extrai o conteúdo entre os delimitadores ```...```
    match = re.search(r"```\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: retorna o conteúdo completo se não houver bloco de código
    return content.strip()


def build_user_message(test_case: dict) -> str:
    """
    Monta a mensagem do usuário com metadados do chamado e chunks,
    simulando o que o pipeline de produção enviaria.
    """
    parts = []

    # Injeta metadados do chamado se presentes
    if "metadados_chamado" in test_case:
        m = test_case["metadados_chamado"]
        parts.append(
            f"<METADADOS_CHAMADO>\n"
            f"  tier_cliente: {m.get('tier_cliente', 'STANDARD')}\n"
            f"  id_chamado: {m.get('id_chamado', 'N/A')}\n"
            f"  atendente: {m.get('atendente', 'N/A')}\n"
            f"  timestamp: {m.get('timestamp', 'N/A')}\n"
            f"</METADADOS_CHAMADO>"
        )

    # Injeta chunks fornecidos
    for chunk in test_case.get("chunks_fornecidos", []):
        parts.append(
            f"<CHUNK id=\"{chunk['id']}\" "
            f"fonte=\"{chunk['fonte']}\" "
            f"secao=\"{chunk['secao']}\" "
            f"versao=\"{chunk['versao']}\" "
            f"data_vigencia=\"{chunk['data_vigencia']}\">\n"
            f"{chunk['conteudo']}\n"
            f"</CHUNK>"
        )

    parts.append(f"Pergunta: {test_case['pergunta']}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Verificações determinísticas (Harness pós-LLM)
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_name: str
    passed: bool
    detail: str


def check_citation_present(response: str, required: bool) -> CheckResult:
    """[DET] Verifica se a resposta contém pelo menos uma citação no formato [Fonte: ...]"""
    if not required:
        return CheckResult("citation_present", True, "Citação não exigida para este caso")
    pattern = r"\[Fonte:\s*\w"
    has_citation = bool(re.search(pattern, response))
    return CheckResult(
        "citation_present",
        has_citation,
        "Citação encontrada" if has_citation else "FALHA: resposta sem [Fonte: ...]"
    )


def check_forbidden_terms(response: str, forbidden: list) -> CheckResult:
    """[DET] Verifica que a resposta não contém termos proibidos."""
    found = [term for term in forbidden if term.lower() in response.lower()]
    if found:
        return CheckResult(
            "forbidden_terms",
            False,
            f"FALHA: termos proibidos encontrados: {found}"
        )
    return CheckResult("forbidden_terms", True, "Nenhum termo proibido detectado")


def check_required_terms(response: str, required: list) -> CheckResult:
    """[DET] Verifica que a resposta contém todos os termos esperados."""
    missing = [term for term in required if term.lower() not in response.lower()]
    if missing:
        return CheckResult(
            "required_terms",
            False,
            f"FALHA: termos esperados não encontrados: {missing}"
        )
    return CheckResult("required_terms", True, "Todos os termos esperados presentes")


def check_minimum_length(response: str, min_chars: int = 50) -> CheckResult:
    """[DET] Verifica que a resposta não é vazia ou trivialmente curta."""
    length = len(response.strip())
    if length < min_chars:
        return CheckResult(
            "minimum_length",
            False,
            f"FALHA: resposta muito curta ({length} chars, mínimo {min_chars})"
        )
    return CheckResult("minimum_length", True, f"Comprimento OK ({length} chars)")


def check_no_hallucinated_tiers(response: str) -> CheckResult:
    """[DET] Verifica que a resposta não menciona tiers inexistentes (Platinum, Diamond, VIP)."""
    hallucinated = ["Platinum", "Diamond", "VIP"]
    found = [t for t in hallucinated if t.lower() in response.lower()]
    if found:
        return CheckResult(
            "no_hallucinated_tiers",
            False,
            f"FALHA: tier inexistente mencionado: {found}"
        )
    return CheckResult("no_hallucinated_tiers", True, "Nenhum tier inexistente detectado")


# ---------------------------------------------------------------------------
# Runner principal
# ---------------------------------------------------------------------------

@dataclass
class TestCaseResult:
    test_case_id: str
    categoria: str
    pergunta: str
    response: str
    checks: list = field(default_factory=list)
    overall_passed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "test_case_id": self.test_case_id,
            "categoria": self.categoria,
            "pergunta": self.pergunta,
            "response_preview": self.response[:300] + "..." if len(self.response) > 300 else self.response,
            "checks": [
                {"check": c.check_name, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
            "overall_passed": self.overall_passed,
            "error": self.error,
        }


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    Chama o Azure OpenAI com o system prompt e a mensagem do usuário.

    Em ambiente de CI/CD, usa variáveis de ambiente para credenciais.
    Em execução local sem credenciais, retorna uma resposta simulada para
    demonstração do conceito.
    """
    import os
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        # Modo de demonstração: retorna stub para mostrar o conceito
        print("  [AVISO] Credenciais Azure OpenAI não configuradas — usando resposta simulada")
        return (
            "Não encontrei esta informação na documentação disponível. "
            "Recomendo escalar para o supervisor. "
            "[Fonte: simulado para demonstração do harness]"
        )

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-15-preview",
        )
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,      # Determinismo máximo para testes
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"ERRO_LLM: {str(e)}"


def run_tests(prompt_path: str, cases_path: str) -> list:
    """Executa todos os casos de teste e retorna os resultados."""
    system_prompt = load_prompt(prompt_path)
    with open(cases_path, encoding="utf-8") as f:
        suite = json.load(f)

    results = []
    total = len(suite["test_cases"])

    print(f"\n{'='*60}")
    print(f"NovaTech Prompt Test Harness")
    print(f"Prompt: {suite['prompt_under_test']}")
    print(f"Casos:  {cases_path} ({total} testes)")
    print(f"{'='*60}\n")

    for tc in suite["test_cases"]:
        print(f"[{tc['id']}] {tc['descricao'][:60]}...")
        user_message = build_user_message(tc)
        response = call_llm(system_prompt, user_message)

        result = TestCaseResult(
            test_case_id=tc["id"],
            categoria=tc["categoria"],
            pergunta=tc["pergunta"],
            response=response,
        )

        # Aplicar verificações determinísticas
        result.checks.append(
            check_citation_present(response, tc.get("criterio_citacao", True))
        )
        result.checks.append(
            check_forbidden_terms(response, tc.get("resposta_nao_deve_conter", []))
        )
        result.checks.append(
            check_required_terms(response, tc.get("resposta_esperada_contem", []))
        )
        result.checks.append(check_minimum_length(response))
        result.checks.append(check_no_hallucinated_tiers(response))

        result.overall_passed = all(c.passed for c in result.checks)
        status = "✓ PASS" if result.overall_passed else "✗ FAIL"
        print(f"  {status}")

        for check in result.checks:
            if not check.passed:
                print(f"    → {check.detail}")

        results.append(result)

    # Resumo
    passed = sum(1 for r in results if r.overall_passed)
    print(f"\n{'='*60}")
    print(f"RESULTADO: {passed}/{total} casos passaram")
    if passed == total:
        print("STATUS: APROVADO — prompt pronto para merge")
    else:
        print("STATUS: REPROVADO — corrigir prompt antes de merge")
    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="NovaTech Prompt Test Harness")
    parser.add_argument("--prompt", required=True, help="Caminho para o arquivo de system prompt")
    parser.add_argument("--cases", required=True, help="Caminho para o arquivo de casos de teste JSON")
    parser.add_argument("--output", help="Caminho para salvar resultados em JSON (opcional)")
    args = parser.parse_args()

    results = run_tests(args.prompt, args.cases)

    if args.output:
        output_data = {
            "prompt": args.prompt,
            "cases": args.cases,
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.overall_passed),
                "failed": sum(1 for r in results if not r.overall_passed),
            },
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Resultados salvos em: {args.output}")

    # Exit code 1 se algum teste falhou — permite pipeline de CI/CD barrar o merge
    failed = sum(1 for r in results if not r.overall_passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
