VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
PYTEST=$(VENV)/bin/pytest

.PHONY: venv install test check ocr-batch

venv:
	python -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

test:
	$(PYTEST) -q

check: test
	$(PYTHON) -m py_compile app/main.py app/api/routes/blockers.py app/services/ocr_service.py

ocr-batch:
	$(PYTHON) scripts/run_ocr_batch.py
