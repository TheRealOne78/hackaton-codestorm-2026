VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
PYTEST=$(VENV)/bin/pytest

.PHONY: venv install test docstrings-check check ocr-env ocr-batch ocr-verify

venv:
	python -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

test:
	$(PYTEST) -q

docstrings-check:
	$(PYTHON) scripts/check_docstrings.py

check: docstrings-check test
	$(PYTHON) -m py_compile app/main.py app/api/routes/blockers.py app/services/ocr_service.py

ocr-env:
	$(PYTHON) scripts/check_ocr_env.py

ocr-batch:
	$(PYTHON) scripts/run_ocr_batch.py

ocr-verify: ocr-env check ocr-batch
