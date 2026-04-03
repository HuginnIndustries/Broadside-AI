.PHONY: install test lint typecheck smoke-dist release-check clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check src/ tests/ benchmarks/ examples/
	python -m ruff format --check src/ tests/ benchmarks/ examples/

typecheck:
	python -m mypy src/broadside_ai/

smoke-dist:
	python tools/smoke_dist_install.py

release-check: test lint typecheck
	python -m build
	python -m twine check dist/*
	python tools/smoke_dist_install.py

clean:
	python tools/clean.py
