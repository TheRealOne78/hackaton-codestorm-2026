# Agent Memory + Prompts

## 1) Project Memory (read this first)

### Goal
Build a modular-monolith academic document pipeline:
- Input: PDF/image documents (`Fișa Disciplinei`, `Plan de Învățământ`)
- Core flow: OCR -> sanitize -> parse -> validate
- Output: stable internal JSON + deterministic issues for UI

### Constraints
- Backend language: Python
- Current backend stack: FastAPI + Pydantic
- LLM provider strategy: OpenRouter/Groq via config (no hardcoded vendor logic)
- Work according to `TASKS.md` (blockers first)

### Current status (implemented)
- `Task 1 OCR`: implemented with fallback chain
- `Task 2 Parse OCR`: implemented (baseline + structured)
- `Task 3 Validation`: implemented with stable issue contract
- `Task 4 API glue`: implemented
- Sanitizer engine implemented for OCR noise + plan row extraction
- Tests passing in `apps/api` (`make check`, `make ocr-verify`)

### Active branch
- `task-0-pdf-slicing`

### Key files
- [/home/therealone/git/hackaton-codestorm-2026/TASKS.md](/home/therealone/git/hackaton-codestorm-2026/TASKS.md)
- [/home/therealone/git/hackaton-codestorm-2026/OCR_IMPLEMENTATION_RESEARCH.md](/home/therealone/git/hackaton-codestorm-2026/OCR_IMPLEMENTATION_RESEARCH.md)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/app/main.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/app/main.py)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/app/api/routes/blockers.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/app/api/routes/blockers.py)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/ocr_service.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/ocr_service.py)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/sanitizer_service.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/sanitizer_service.py)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/structured_parser_service.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/structured_parser_service.py)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/validation_service.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/app/services/validation_service.py)
- [/home/therealone/git/hackaton-codestorm-2026/apps/api/tests/test_sanitizer_service.py](/home/therealone/git/hackaton-codestorm-2026/apps/api/tests/test_sanitizer_service.py)

### Existing API endpoints
- `POST /ocr`
- `POST /sanitize`
- `POST /parse`
- `POST /parse-structured`
- `POST /validate`
- `POST /pipeline/run-blockers`
- `POST /pipeline/run-structured`

### Response contract notes
- Global envelope: `data`, `errors`, `meta`
- Validation issue contract: `code`, `path`, `message`, `severity`, `suggested_fix`

### Local runbook
```bash
cd apps/api
make install
make ocr-verify
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open docs at `http://localhost:8000/docs`

### Sample docs
- `samples/fisa_disciplina.pdf`
- `samples/plan_invatamant.pdf`
- Sliced fixtures in `samples/sliced/`

### Known gaps
- Plan table extraction is improved but still noisy on hard OCR cases.
- Need stronger schema-driven column mapping and confidence scoring.
- Tasks 5+ from `TASKS.md` are still open.

---

## 2) Copy/Paste Prompts For Other Agents

### Prompt A: Ingestion module (Task 5)
```text
You are implementing Task 5 from TASKS.md in this repo.

Read first:
- TASKS.md
- apps/api/app/main.py
- apps/api/app/api/routes/blockers.py
- apps/api/app/schemas/blockers.py

Goal:
Add upload/type-detection ingestion endpoints for PDF and DOCX.
Return metadata: file_path, mime, pages, extracted_text_length, needs_ocr.

Constraints:
- Python FastAPI modular style.
- Reuse existing OCR service where possible.
- Add/extend Pydantic schemas.
- Add tests in apps/api/tests.
- Add docstrings to all new modules/functions.

Definition of done:
- make check passes
- endpoint appears in /docs
- deterministic JSON response
```

### Prompt B: Text extraction + cleaning hardening (Task 6)
```text
You are improving OCR/text cleaning robustness (Task 6).

Read first:
- apps/api/app/services/ocr_service.py
- apps/api/app/services/sanitizer_service.py
- OCR_IMPLEMENTATION_RESEARCH.md
- apps/api/tests/test_ocr_service.py
- apps/api/tests/test_sanitizer_service.py

Goal:
Improve extraction quality without hardcoded typo dictionaries.

Requirements:
- Keep deterministic behavior.
- Add confidence or quality metadata for parsed rows.
- Avoid lexical hardcoding for specific OCR mistakes.
- Keep existing API contracts backward-compatible.

Deliverables:
- service changes + tests
- docs note in apps/api/README.md with new behavior
- make check passes
```

### Prompt C: Structured plan parser quality pass
```text
You are improving structured Plan parser quality.

Read first:
- apps/api/app/services/structured_parser_service.py
- apps/api/app/services/sanitizer_service.py

Goal:
Extract cleaner course records from noisy OCR:
- index
- name
- code
- category
- verification
- credits_guess

Requirements:
- Prefer section-aware parsing (mandatory vs optional).
- Reject total/footer/admin rows deterministically.
- Keep parser resilient to OCR noise.
- Add unit tests for Romanian sample patterns.

Definition of done:
- tests cover noisy lines and expected filtered output
- no regressions in existing tests
```

### Prompt D: Validation expansion
```text
You are extending validation rules with stable payloads.

Read first:
- apps/api/app/services/validation_service.py
- apps/api/app/schemas/blockers.py
- TASKS.md

Goal:
Add new deterministic checks for parsed plan/fisa payloads.

Rules examples:
- required metadata present
- credits sanity by semester/year
- duplicate course code detection
- inconsistent verification markers

Constraints:
- Preserve issue contract: code/path/message/severity/suggested_fix
- Add tests including snapshot-like stability checks
```

### Prompt E: Docker baseline + DX
```text
You are implementing Docker baseline from TASKS.md.

Goal:
Create dockerized local stack for API and OCR dependencies.

Deliverables:
- Dockerfile for apps/api
- docker-compose.yml with api + optional redis/postgres/minio placeholders
- healthcheck and simple make targets
- README updates with run commands

Constraints:
- Pin image tags
- Keep startup simple for hackathon use
- ensure OCR binaries availability in container
```

### Prompt F: Frontend skeleton (Task 11 start)
```text
You are creating apps/web skeleton for pipeline visualization.

Goal:
Create React + Vite app with pages:
- Upload document
- Run OCR / pipeline
- Show sanitized rows and validation issues

Requirements:
- Typed API client
- clear error rendering
- mobile + desktop usable layout
- avoid changing backend contracts

Definition of done:
- app runs locally
- can call /pipeline/run-structured and render response
```

### Prompt G: AI gateway abstraction (OpenRouter/Groq)
```text
You are implementing AI provider abstraction for OpenRouter/Groq.

Goal:
Add provider-agnostic gateway module with env-based routing:
- LLM_PROVIDER=openrouter|groq
- LLM_BASE_URL
- LLM_API_KEY
- LLM_MODEL

Requirements:
- no provider hardcoding in business modules
- typed request/response wrappers
- unit tests using mocked HTTP calls
- clear error messages for missing env vars
```

---

## 3) Team Rule For All Agents
- Always update `TASKS.md` checkboxes for completed items.
- Always add/maintain docstrings for edited Python files.
- Always run `cd apps/api && make check` before finalizing.
- Do not rewrite API envelopes/contracts without migration note.
- Prefer deterministic parsing first; keep LLM fallback optional and isolated.
