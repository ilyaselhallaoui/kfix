.PHONY: help install install-dev format lint type-check test test-cov clean build publish

help:
	@echo "Available commands:"
	@echo "  make install      - Install package dependencies"
	@echo "  make install-dev  - Install package with dev dependencies"
	@echo "  make format       - Format code with black and isort"
	@echo "  make lint         - Lint code with ruff"
	@echo "  make type-check   - Type check with mypy"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make build        - Build distribution packages"
	@echo "  make publish      - Publish to PyPI"
	@echo "  make all          - Run format, lint, type-check, and test"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

format:
	@echo "Running isort..."
	isort kfix tests
	@echo "Running black..."
	black kfix tests
	@echo "✓ Code formatted!"

lint:
	@echo "Running ruff..."
	ruff check kfix tests
	@echo "✓ Linting complete!"

type-check:
	@echo "Running mypy..."
	mypy kfix
	@echo "✓ Type checking complete!"

test:
	pytest

test-cov:
	pytest --cov=kfix --cov-report=term-missing --cov-report=html

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	twine upload dist/*

all: format lint type-check test
	@echo "✓ All checks passed!"
