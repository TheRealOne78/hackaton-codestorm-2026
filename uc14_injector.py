"""
UC 1.4 - The Competency Injector
Citeste o Fisa existenta si genereaza un schelet (draft) pentru noua fisa,
completand automat campurile fixe si marcand clar ce trebuie completat manual.
"""
from utils.claude_client import call_claude_with_pdf, call_claude_with_text, parse_json_response

SYSTEM_PROMPT = """Esti un asistent academic specializat in generarea de schite (draft-uri)
pentru Fise ale Disciplinei din universitati romanesti.
Extrage informatiile existente si genereaza un draft structurat.
Returneaza EXCLUSIV JSON valid, fara markdown, fara text suplimentar.
"""

USER_PROMPT = """Analizeaza aceasta Fisa a Disciplinei si genereaza un schelet (draft) 
pentru o noua versiune actualizata.

Returneaza JSON cu structura EXACTA:
{
  "draft": {
    "sectiunea_1": {
      "titlu": "Date despre program",
      "campuri": {
        "institutia": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "facultatea": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "departamentul": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "domeniu_studii": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ciclu_studii": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "program_studii": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""}
      }
    },
    "sectiunea_2": {
      "titlu": "Date despre disciplina",
      "campuri": {
        "denumire_disciplina": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "titular_curs": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "titular_seminar": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "an_studiu": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "semestru": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "tip_evaluare": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "regim_continut": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "regim_obligativitate": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""}
      }
    },
    "sectiunea_3": {
      "titlu": "Timp total estimat",
      "campuri": {
        "ore_saptamana": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_curs_saptamana": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_seminar_saptamana": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "total_ore_plan": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_curs_total": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_seminar_total": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_studiu_manual": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_documentare": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_pregatire": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_tutoriat": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_examinari": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_student_total": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "ore_total_semestru": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""},
        "numar_credite": {"valoare": "", "sursa": "extras|lipsa|de_completat", "nota": ""}
      }
    },
    "sectiunea_4_preconditii": {
      "titlu": "Preconditii",
      "curriculum": {"valoare": [], "sursa": "extras|lipsa|de_completat"},
      "competente": {"valoare": [], "sursa": "extras|lipsa|de_completat"}
    },
    "sectiunea_5_conditii": {
      "titlu": "Conditii",
      "curs": {"valoare": "", "sursa": "extras|lipsa|de_completat"},
      "seminar": {"valoare": "", "sursa": "extras|lipsa|de_completat"}
    },
    "sectiunea_6_competente": {
      "titlu": "Competente specifice",
      "profesionale": {"valoare": [], "sursa": "extras|lipsa|de_completat", "nota": "Verifica cu Planul de Invatamant"},
      "transversale": {"valoare": [], "sursa": "extras|lipsa|de_completat", "nota": "Verifica cu Planul de Invatamant"}
    },
    "sectiunea_7_obiective": {
      "titlu": "Obiective",
      "obiectiv_general": {"valoare": "", "sursa": "extras|lipsa|de_completat"},
      "obiective_specifice": {"valoare": [], "sursa": "extras|lipsa|de_completat"}
    },
    "sectiunea_8_continuturi": {
      "titlu": "Continuturi",
      "curs": {"valoare": [], "sursa": "extras|lipsa|de_completat", "nota": ""},
      "seminar": {"valoare": [], "sursa": "extras|lipsa|de_completat", "nota": ""},
      "bibliografie_curs": {"valoare": [], "sursa": "extras|lipsa|de_completat"},
      "bibliografie_seminar": {"valoare": [], "sursa": "extras|lipsa|de_completat"}
    },
    "sectiunea_10_evaluare": {
      "titlu": "Evaluare",
      "pondere_curs": {"valoare": "", "sursa": "extras|lipsa|de_completat"},
      "pondere_seminar": {"valoare": "", "sursa": "extras|lipsa|de_completat"},
      "metode_curs": {"valoare": "", "sursa": "extras|lipsa|de_completat"},
      "metode_seminar": {"valoare": "", "sursa": "extras|lipsa|de_completat"},
      "standard_minim": {"valoare": "", "sursa": "extras|lipsa|de_completat"}
    }
  },
  "campuri_de_completat": ["lista campurilor cu sursa=de_completat sau lipsa"],
  "campuri_preluate": ["lista campurilor cu sursa=extras"],
  "recomandari": ["lista de recomandari pentru completarea draftului"],
  "completitudine_procent": 0,
  "nota_an_universitar": "Actualizeaza la noul an universitar inainte de depunere"
}

sursa:
- "extras" = valoarea a fost gasita in document si preluata
- "lipsa" = campul nu exista in document  
- "de_completat" = campul exista dar e gol sau vag"""


def run(pdf_bytes: bytes, pdf_b64: str, extracted_text: str = "") -> dict:
    try:
        raw = call_claude_with_pdf(SYSTEM_PROMPT, USER_PROMPT, pdf_b64)
    except Exception as e:
        if extracted_text:
            raw = call_claude_with_text(SYSTEM_PROMPT, USER_PROMPT, extracted_text)
        else:
            raise e

    return parse_json_response(raw)
