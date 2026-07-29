.PHONY: check check-manifest check-workspace test

PYTHON ?= python3

check: check-manifest test

check-manifest:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml

check-workspace:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml --check-workspace

test:
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-local.ps1 -Step python
else
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
endif
