.PHONY: check check-manifest check-pins sync-pins check-workspace check-governance test

PYTHON ?= python3

check: check-manifest test

check-manifest:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml

check-pins:
	$(PYTHON) scripts/sync_workspace_pins.py ecosystem.yaml --json

sync-pins:
	$(PYTHON) scripts/sync_workspace_pins.py ecosystem.yaml --apply --json

check-workspace:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml --check-workspace

check-governance:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml --check-workspace --check-governance

test:
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-local.ps1 -Step python
else
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
endif
