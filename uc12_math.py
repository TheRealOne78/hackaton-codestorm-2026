"""
UC 1.2 - The Math Checker
Verifica:
- Suma orelor (curs + seminar = total din plan)
- Total ore pe semestru (ore didactice + studiu individual)
- Ponderi evaluare sumeaza 100%
- Numarul de credite vs ore totale (1 credit = 30h)
- Alte inconsistente numerice
"""
from utils.claude_client import call_claude_with_pdf, call_claude_with_text, parse_json_response

SYSTEM_PROMPT = """Esti un validator numeric specializat pentru Fise ale Disciplinei universitare romanesti.
Extrage toate valorile numerice si verifica consistenta matematica.
Returneaza EXCLUSIV JSON valid, fara markdown, fara explicatii suplimentare.
"""

USER_PROMPT = """Analizeaza valorile numerice din aceasta Fisa a Disciplinei.

Returneaza JSON cu structura EXACTA:
{
  "valori_extrase": {
    "ore_curs_saptamana": null,
    "ore_seminar_saptamana": null,
    "ore_total_saptamana": null,
    "ore_curs_total": null,
    "ore_seminar_total": null,
    "ore_didactice_total": null,
    "ore_studiu_manual": null,
    "ore_documentare": null,
    "ore_pregatire_seminar": null,
    "ore_tutoriat": null,
    "ore_examinari": null,
    "ore_alte": null,
    "ore_studiu_individual_total": null,
    "ore_total_semestru": null,
    "numar_credite": null,
    "pondere_curs_procent": null,
    "pondere_seminar_procent": null
  },
  "verificari": [
    {
      "id": "v1",
      "descriere": "Ore/sapt curs + seminar = total/sapt",
      "valoare_calculata": null,
      "valoare_declarata": null,
      "status": "ok|error|warn|na",
      "mesaj": ""
    }
  ],
  "alerte": [
    {
      "severitate": "error|warn|info",
      "camp": "numele campului",
      "mesaj": "descrierea problemei",
      "valoare_gasita": null,
      "valoare_asteptata": null
    }
  ],
  "scor_consistenta": 0,
  "rezumat": ""
}

Verificarile obligatorii:
- v1: ore_curs_saptamana + ore_seminar_saptamana == ore_total_saptamana
- v2: ore_curs_total == ore_curs_saptamana * 14 (saptamani standard)
- v3: ore_seminar_total == ore_seminar_saptamana * 14
- v4: ore_didactice_total == ore_curs_total + ore_seminar_total
- v5: ore_studiu_individual_total == suma componentelor individuale
- v6: ore_total_semestru == ore_didactice_total + ore_studiu_individual_total  
- v7: numar_credite * 30 == ore_total_semestru (1 credit = 30 ore)
- v8: pondere_curs + pondere_seminar == 100%

scor_consistenta: 0-100."""


def run(pdf_bytes: bytes, pdf_b64: str, extracted_text: str = "") -> dict:
    try:
        raw = call_claude_with_pdf(SYSTEM_PROMPT, USER_PROMPT, pdf_b64)
    except Exception as e:
        if extracted_text:
            raw = call_claude_with_text(SYSTEM_PROMPT, USER_PROMPT, extracted_text)
        else:
            raise e

    return parse_json_response(raw)
