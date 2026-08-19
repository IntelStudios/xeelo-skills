# Regenerate machine-readable data, project packages, and ovnet env.

PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
PY := $(shell test -x $(VENV_PYTHON) && echo $(VENV_PYTHON) || echo $(PYTHON))

.PHONY: extract generate-account validate-account extract-cars roundtrip-account test \
	download-ovnet extract-ovnet loop-init generate-loop all

extract:
	$(PY) scripts/extract-schemas.py
	$(PY) scripts/extract-enums.py
	$(PY) scripts/extract-hints.py
	$(PY) scripts/extract-labels.py
	$(PY) scripts/extract-transfer-tables.py
	$(PY) scripts/extract-object-transfer-map.py

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

# --- Project change-loop (ovnet sample) ---

download-ovnet:
	$(PY) scripts/download-db-transfer.py \
		--connection projects/ovnet/.xeelo-connection.json

extract-ovnet:
	@snap=$$(ls -1d projects/ovnet/snapshots/*/ 2>/dev/null | sort | tail -1); \
	test -n "$$snap" || (echo "No snapshots under projects/ovnet/snapshots"; exit 1); \
	zip=$$(ls -1 "$$snap"*.zip | head -1); \
	$(PY) scripts/extract-db-transfer-to-env.py "$$zip" -o projects/ovnet/env

# Usage: make loop-init SLUG=20260811-loop-01-name OBJECTS="ov-net-customer ov-net-account"
loop-init:
	@test -n "$(SLUG)" || (echo "Set SLUG=..."; exit 1)
	$(PY) scripts/init-change-loop.py --project projects/ovnet --slug $(SLUG) $(if $(OBJECTS),--objects $(OBJECTS),)

# Usage: make generate-loop LOOP=projects/ovnet/changes/20260811-loop-01-name
generate-loop:
	@test -n "$(LOOP)" || (echo "Set LOOP=projects/ovnet/changes/<slug>"; exit 1)
	$(PY) scripts/generate-change-loop.py $(LOOP)

all: extract generate-account validate-account roundtrip-account
