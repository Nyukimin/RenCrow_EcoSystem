.PHONY: check check-manifest check-workspace test

check: check-manifest test

check-manifest:
	python3 scripts/validate_ecosystem.py ecosystem.yaml

check-workspace:
	python3 scripts/validate_ecosystem.py ecosystem.yaml --check-workspace

test:
	python3 -m unittest discover -s tests -p 'test_*.py'
