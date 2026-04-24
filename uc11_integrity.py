"""
UC 1.1 - The Integrity Guard
Verifica prezenta sectiunilor obligatorii, campurilor completate,
semnaturii, bibliografiei, etc.
"""
import json
from utils.claude_client import call_claude_with_pdf, call_claude_with_text, parse_json_response

SYSTEM_PROMPT = """Esti un validator automat de Fise ale Disciplinei din universitati romanesti.
Analizeaza documentul si returneaza EXCLUSIV un JSON valid, fara alte explicatii, fara markdown.
"""

USER_PROMPT = """Analizeaza aceasta Fisa a Disciplinei si verifica integritatea structurala.

Returneaza un JSON cu urmatoarea structura EXACTA:
{
  "sectiuni": [
    {
      "id": "1",
      "nume": "Date despre program",
      "status": "ok|warn|error",
      "detalii": "descriere scurta"
    }
  ],
  "campuri_lipsa": ["lista campurilor goale sau incomplete"],
  "campuri_ok": ["lista campurilor corect completate"],
  "semnaturi": {
    "decan": "prezent|absent|partial",
    "director_departament": "prezent|absent|partial",
    "titular_curs": "prezent|absent|partial",
    "titular_seminar": "prezent|absent|partial"
  },
  "bibliografie": {
    "curs_prezenta": true,
    "seminar_prezenta": true,
    "numar_surse_curs": 0,
    "numar_surse_seminar": 0
  },
  "metadata": {
    "institutie": "",
    "facultate": "",
    "departament": "",
    "disciplina": "",
    "titular": "",
    "an_studiu": "",
    "semestru": "",
    "credite": ""
  },
  "scor_integritate": 0,
  "rezumat": "descriere generala a starii documentului"
}

Sectiunile standard ale unei Fise de Disciplina sunt:
1. Date despre program, 2. Date despre disciplina, 3. Timp total estimat,
4. Preconditii, 5. Conditii, 6. Competente specifice, 7. Obiective,
8. Continuturi (curs + seminar/laborator), 9. Coroborarea continuturilor,
10. Evaluare (cu ponderi), Semnaturi.

scor_integritate: 0-100 (100 = perfect complet)."""


def run(pdf_bytes: bytes, pdf_b64: str, extracted_text: str = "") -> dict:
    """
    Ruleaza UC 1.1.
    Incearca direct cu PDF, fallback la text extras.
    """
    try:
        raw = call_claude_with_pdf(SYSTEM_PROMPT, USER_PROMPT, pdf_b64)
    except Exception as e:
        if extracted_text:
            raw = call_claude_with_text(SYSTEM_PROMPT, USER_PROMPT, extracted_text)
        else:
            raise e

    return parse_json_response(raw)
