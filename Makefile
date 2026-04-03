.PHONY: install test lint typecheck release-check clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check src/ tests/ benchmarks/ examples/
	python -m ruff format --check src/ tests/ benchmarks/ examples/

typecheck:
	python -m mypy src/broadside_ai/

release-check: test lint typecheck
	python -m build
	python -m twine check dist/*

clean:
	python tools/clean.py
