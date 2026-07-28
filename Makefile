.PHONY: check check-manifest check-workspace test

PYTHON ?= python3

check: check-manifest test

check-manifest:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml

check-workspace:
	$(PYTHON) scripts/validate_ecosystem.py ecosystem.yaml --check-workspace

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
