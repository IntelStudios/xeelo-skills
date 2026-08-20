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
		-o projects/account-object/output/object-transfer.xml \
		--zip projects/account-object/account-object-transfer.zip

validate-account:
	$(PY) scripts/validate-object-transfer.py \
		projects/account-object/output/object-transfer.xml \
		projects/cars/ObjectSetup_20260811_084036.xml

test:
	$(PY) -m unittest discover -s tests -p 'test_*.py'

extract-cars:
	$(PY) scripts/extract-object-transfer-to-spec.py \
		projects/cars/ObjectSetup_20260811_084036.xml \
		--object-id 6097 \
		-o projects/cars

roundtrip-account: generate-account
	rm -rf /tmp/account-roundtrip /tmp/account-roundtrip2
	$(PY) scripts/extract-object-transfer-to-spec.py \
		projects/account-object/output/object-transfer.xml \
		-o /tmp/account-roundtrip
	$(PY) scripts/generate-object-transfer.py /tmp/account-roundtrip/xeelo-spec.yaml \
		-o /tmp/account-roundtrip-out.xml
	$(PY) scripts/extract-object-transfer-to-spec.py \
		/tmp/account-roundtrip-out.xml \
		-o /tmp/account-roundtrip2
	$(PY) -c "import sys; sys.path.insert(0,'scripts'); from ot_builder.spec_loader import load_spec; a=load_spec(__import__('pathlib').Path('/tmp/account-roundtrip'))['ids']['explicit']; b=load_spec(__import__('pathlib').Path('/tmp/account-roundtrip2'))['ids']['explicit']; sys.exit(0 if a==b else 1)"
	@echo "Round-trip IDs OK"

all: extract generate-account validate-account roundtrip-account
