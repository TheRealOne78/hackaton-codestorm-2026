"""
UC 1.3 - The Syllabus Diff
Compara doua Fise ale Disciplinei (veche vs noua / template nou)
si evidentiaza diferentele structurale si de continut.
"""
from utils.claude_client import (
    call_claude_with_pdf,
    call_claude_with_text,
    call_claude_with_two_pdfs,
    parse_json_response,
)

SYSTEM_PROMPT = """Esti un sistem de comparatie specializat pentru Fise ale Disciplinei universitare.
Compara doua documente si identifica toate diferentele relevante.
Returneaza EXCLUSIV JSON valid, fara markdown, fara text suplimentar.
"""

USER_PROMPT_TWO_PDFS = """Primul document este Fisa VECHE, al doilea este Fisa NOUA (sau noul template).

Compara-le sectiune cu sectiune si returneaza JSON cu structura EXACTA:
{
  "sectiuni_comparate": [
    {
      "sectiune": "numele sectiunii",
      "status": "identic|modificat|adaugat|eliminat",
      "continut_vechi": "rezumat continut vechi (max 150 chars)",
      "continut_nou": "rezumat continut nou (max 150 chars)",
      "descriere_schimbare": "ce s-a schimbat concret"
    }
  ],
  "campuri_modificate": [
    {
      "camp": "numele campului",
      "valoare_veche": "",
      "valoare_noua": "",
      "tip_schimbare": "numeric|text|structural"
    }
  ],
  "sectiuni_noi": ["lista sectiunilor adaugate in documentul nou"],
  "sectiuni_eliminate": ["lista sectiunilor din documentul vechi care lipsesc din cel nou"],
  "avertizari_importante": [
    {
      "tip": "pondere|ore|competenta|bibliografie|altele",
      "mesaj": "descrierea schimbarii importante",
      "actiune_necesara": "ce trebuie sa faca profesorul"
    }
  ],
  "rezumat_executive": "scurt rezumat pentru profesor (2-3 fraze)",
  "numar_schimbari_totale": 0,
  "nivel_impact": "minor|moderat|major"
}"""

USER_PROMPT_SINGLE = """Analizeaza aceasta Fisa a Disciplinei si compara-o cu structura standard
a unei Fise de Disciplina romanesti (template UBB/format national standard).
Identifica ce lipseste, ce e diferit sau ce e neconventional.

Returneaza JSON cu structura EXACTA:
{
  "sectiuni_comparate": [
    {
      "sectiune": "numele sectiunii standard",
      "status": "prezent|modificat|lipsa",
      "continut_vechi": "N/A - comparatie cu standard",
      "continut_nou": "continut gasit in document",
      "descriere_schimbare": "diferenta fata de standard"
    }
  ],
  "campuri_modificate": [],
  "sectiuni_noi": ["sectiuni prezente dar nestandard"],
  "sectiuni_eliminate": ["sectiuni standard care lipsesc"],
  "avertizari_importante": [],
  "rezumat_executive": "evaluare generala a conformitatii cu standardul",
  "numar_schimbari_totale": 0,
  "nivel_impact": "minor|moderat|major"
}"""


def run(
    pdf_bytes_main: bytes,
    pdf_b64_main: str,
    extracted_text_main: str = "",
    pdf_bytes_compare: bytes = None,
    pdf_b64_compare: str = None,
    extracted_text_compare: str = "",
) -> dict:
    """
    Daca se dau doua PDF-uri: compara-le direct.
    Daca se da unul singur: compara cu standardul.
    """
    if pdf_b64_compare:
        try:
            raw = call_claude_with_two_pdfs(
                SYSTEM_PROMPT,
                USER_PROMPT_TWO_PDFS,
                pdf_b64_main,
                pdf_b64_compare,
            )
        except Exception:
            # fallback text
            combined = (
                f"DOCUMENT VECHI:\n{extracted_text_main}\n\n"
                f"DOCUMENT NOU:\n{extracted_text_compare}"
            )
            raw = call_claude_with_text(SYSTEM_PROMPT, USER_PROMPT_TWO_PDFS, combined)
    else:
        try:
            raw = call_claude_with_pdf(SYSTEM_PROMPT, USER_PROMPT_SINGLE, pdf_b64_main)
        except Exception:
            if extracted_text_main:
                raw = call_claude_with_text(SYSTEM_PROMPT, USER_PROMPT_SINGLE, extracted_text_main)
            else:
                raise

    return parse_json_response(raw)
