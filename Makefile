# Regenerate machine-readable data and account-object sample packages.

PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
PY := $(shell test -x $(VENV_PYTHON) && echo $(VENV_PYTHON) || echo $(PYTHON))

.PHONY: extract generate-account validate-account extract-cars roundtrip-account test all

extract:
	$(PY) scripts/extract-schemas.py
	$(PY) scripts/extract-enums.py
	$(PY) scripts/extract-hints.py
	$(PY) scripts/extract-labels.py
	$(PY) scripts/extract-transfer-tables.py
	$(PY) scripts/extract-object-transfer-map.py
	$(PY) scripts/extract-fa-icons.py

generate-account:
	$(PY) scripts/generate-object-transfer.py projects/account-object/xeelo-spec.yaml \
		-o projects/account-object/output/object-transfer.json

validate-account:
	$(PY) scripts/validate-object-transfer.py \
		projects/cars/ObjectSetup_20260811_084036.xml

test:
	$(PY) -m unittest discover -s tests -p 'test_*.py'

extract-cars:
	$(PY) scripts/extract-object-transfer-to-spec.py \
		projects/cars/ObjectSetup_20260811_084036.xml \
		--object-id 6097 \
		-o projects/cars

roundtrip-account: extract-cars
	@echo "Legacy XML extract OK (cars). GraphQL Object Transfer packages are JSON."

all: extract generate-account validate-account test
