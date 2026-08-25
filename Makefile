# Regenerate machine-readable data.

PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
PY := $(shell test -x $(VENV_PYTHON) && echo $(VENV_PYTHON) || echo $(PYTHON))

.PHONY: extract test all

extract:
	$(PY) scripts/extract-schemas.py
	$(PY) scripts/extract-enums.py
	$(PY) scripts/extract-hints.py
	$(PY) scripts/extract-labels.py
	$(PY) scripts/extract-transfer-tables.py
	$(PY) scripts/extract-object-transfer-map.py
	$(PY) scripts/extract-fa-icons.py

test:
	$(PY) -m unittest discover -s tests -p 'test_*.py'

all: extract test
