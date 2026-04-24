# AcadCheck — Nivel 1: Validare Structurală

Platformă Python/Streamlit pentru validarea automată a Fișelor de Disciplină universitare.

## Setup

```bash
pip install -r requirements.txt
```

## Configurare API Key

Setează variabila de mediu ANTHROPIC_API_KEY:

```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows
set ANTHROPIC_API_KEY=sk-ant-...

# Sau creează un fișier .env (necesită python-dotenv)
```

## Rulare

```bash
cd acadcheck
streamlit run app.py
```

Deschide http://localhost:8501 în browser.

## Arhitectură

```
acadcheck/
├── app.py                    # UI Streamlit principal
├── requirements.txt
├── utils/
│   ├── pdf_utils.py          # Extracție PDF, base64
│   └── claude_client.py      # Claude API (PDF direct + fallback text)
└── modules/
    ├── uc11_integrity.py     # UC 1.1 Integrity Guard
    ├── uc12_math.py          # UC 1.2 Math Checker
    ├── uc13_diff.py          # UC 1.3 Syllabus Diff
    └── uc14_injector.py      # UC 1.4 Competency Injector
```

## Metoda de procesare PDF

1. **Direct (preferred):** PDF-ul este trimis ca base64 direct la Claude API.
   Claude îl citește nativ — fără extracție intermediară.

2. **Fallback:** Dacă API-ul eșuează, `pdfplumber` extrage textul și îl trimite ca text simplu.

## UC-uri implementate

| ID | Nume | Descriere |
|----|------|-----------|
| 1.1 | Integrity Guard | Verifică prezența secțiunilor, câmpurilor, semnăturilor, bibliografiei |
| 1.2 | Math Checker | Validează sume ore, ponderi evaluare, credite × 30h |
| 1.3 | Syllabus Diff | Compară două versiuni de fișe sau fișa cu standardul |
| 1.4 | Competency Injector | Generează schelet (draft) pentru fișa nouă |
