# Hackathon Execution Tasks (Modular Monolith, Python Backend + Web UI + Docker)

## Status
- [x] Requirements extracted from `Sisteme Inteligente pentru Managementul Academic.pdf`
- [x] Existing prompts reviewed from `some_prompts.txt`
- [x] Plan revised for Python backend + OpenRouter/Groq provider strategy

## Working Architecture (target)
- [ ] `apps/api` Python FastAPI backend (modular monolith)
- [ ] `apps/web` React + Vite frontend
- [ ] `backend/modules` domain modules (ocr, parsing, validation, diff, sync, migration, reporting, ai)
- [ ] `backend/schemas` shared Pydantic models (internal JSON contracts)
- [ ] `backend/ai_gateway` provider abstraction (`OpenRouter`/`Groq`)
- [ ] Docker Compose for local infra (Postgres, Redis, MinIO, OCR sidecar)

## Priority Order (first obstacles)
- [ ] **Task 1: OCR**
- [ ] **Task 2: Parse OCR**
- [ ] **Task 3: Validation**
- [ ] **Task 4: API glue for first 3 tasks**

## Blocker Acceptance Criteria
- [ ] End-to-end flow works: upload scanned PDF/image -> OCR -> parse -> validate
- [ ] At least 3 golden fixtures (clean PDF, scanned PDF, noisy OCR text)
- [ ] Validation output is deterministic and stable for UI
- [ ] Error payload format stable: `code`, `path`, `message`, `severity`, `suggested_fix`
- [ ] No hardcoded LLM vendor; provider chosen by env

---

## Task Board (assign to agents)

### 1) OCR (FIRST)
- [ ] Implement OCR pipeline for PDF/image input.

Prompt:
```text
You are implementing Task 1: OCR.

Goal:
Input: PDF/image.
Output: text extraction with structure hints.

Requirements:
- Detect digital PDF vs scanned PDF/image.
- For scanned content run OCR (OCRmyPDF or Tesseract-based pipeline).
- Return structured OCR result:
  - full_text
  - pages[]
  - blocks[] with bbox where available
  - tables[] where available
- Persist OCR status and artifacts.
- Include robust timeout and failure handling.

Deliverables:
- OCR service interface + implementation
- Pydantic response schema
- Tests with 3 fixtures: digital PDF, scanned PDF, image-only
```

### 2) Parse OCR -> Internal Struct (SECOND)
- [ ] Parse OCR/mock text into canonical JSON.

Prompt:
```text
You are implementing Task 2: Parse OCR.

Goal:
Input: OCR/mock text.
Output: internal canonical JSON (for Fișa Disciplinei pipeline).

Required fields:
- title
- credits
- objectives
- bibliography
- evaluation
- competencies

Rules:
- Deterministic parser first (regex/section rules).
- Optional LLM fallback only for unresolved fields.
- Missing values must be explicit null.
- Keep evidence metadata when possible (source_span, confidence).

Deliverables:
- Canonical Pydantic model
- Parser implementation
- Fixtures: OCR text -> JSON
- Unit tests
```

### 3) Validation (THIRD)
- [ ] Validate parser JSON and return deterministic issues.

Prompt:
```text
You are implementing Task 3: Validation.

Goal:
Input: parser JSON.
Output: errors + warnings.

Checks:
- Mandatory sections present
- Bibliography non-empty
- Evaluation weights sum to 100
- Individual weight max threshold from config

Error contract:
- code
- path
- message
- severity
- suggested_fix

Deliverables:
- validate_fd(fd, rules)
- Validation result schema
- Valid/invalid fixture tests
- Snapshot tests for payload stability
```

### 4) API glue for blocker pipeline
- [ ] Expose blocker endpoints and one chained endpoint.

Prompt:
```text
You are implementing Task 4: API glue.

Goal:
Build FastAPI routes:
- POST /ocr
- POST /parse
- POST /validate
- POST /pipeline/run-blockers (ocr -> parse -> validate)

Requirements:
- Consistent response envelope
- Pydantic request/response schemas
- OpenAPI docs

Deliverables:
- Route modules
- Shared response model
- API examples
```

### 5) Ingestion (upload + type detection)
- [ ] Upload handling and document type metadata.

Prompt:
```text
You are implementing Task 5: Ingestion.

Goal:
Create upload + detect endpoints for PDF and DOCX.

Return metadata:
- file_path
- mime
- pages
- extracted_text_length
- needs_ocr

Deliverables:
- FastAPI module
- Pydantic models
- Tests for type detection
```

### 6) Text extraction + cleaning
- [ ] Extract text for digital docs and normalize content.

### 7) Diff module (structured JSON diff)
- [ ] Added/removed/modified with fuzzy heading match.

### 8) Sync module (FD vs Plan)
- [ ] Plan is source of truth, report conflicts + aligned values.

### 9) Template migration module
- [ ] Deterministic mapping old template -> new template.

### 10) Human-readable delta report
- [ ] Convert technical diff + validation to teacher-friendly report.

### 11) Frontend web app
- [ ] React UI: upload, run pipeline, visualize errors and diff.

### 12) AI copilot module (guarded)
- [ ] Contextual suggestions with accept/reject flow.

Prompt addition:
```text
Provider routing must support OpenRouter and Groq via env configuration.
```

### 13) Stack ADR (Python + Docker)
- [ ] Produce ADR with final package/image decisions.

Must evaluate at least:
- FastAPI + Pydantic stack
- OCR libs/services
- Parsing approach (rule-based + fallback)
- Validation rules engine
- Queue/background jobs
- Docker image pinning

### 14) CI/CD baseline
- [ ] Type checks/lint/tests/build/compose validation.

---

## Suggested Parallel Execution Order
- [ ] Wave 1 (critical): Tasks 1, 2, 3, 4
- [ ] Wave 2: Tasks 5, 6
- [ ] Wave 3: Tasks 7, 8, 9, 10
- [ ] Wave 4: Tasks 11, 12, 13, 14

## Python/Infra Candidate Stack
- [ ] Backend API: `fastapi`, `uvicorn`, `pydantic`
- [ ] OCR: `ocrmypdf`, `pytesseract`, `opencv-python` (optional preproc)
- [ ] PDF/DOCX parsing: `pymupdf`, `pdfplumber`, `python-docx`
- [ ] Matching/diff: `rapidfuzz`, `deepdiff`
- [ ] Validation/rules: `pydantic`, `jsonschema`
- [ ] Background jobs: `celery` or `rq` + `redis`
- [ ] Storage: `postgresql`, `minio`

## LLM Provider Config (OpenRouter/Groq)
- [ ] `LLM_PROVIDER=openrouter|groq`
- [ ] `LLM_BASE_URL`
- [ ] `LLM_API_KEY`
- [ ] `LLM_MODEL`
- [ ] Use OpenAI-compatible client interface for provider swap by config only

## Done Definition (per task)
- [ ] Tests pass locally
- [ ] API/schema contracts documented
- [ ] Error handling explicit
- [ ] Realistic fixtures included
- [ ] Short handoff note in PR/commit
