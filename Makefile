.PHONY: setup run test clean

VENV = .venv
VENV_PYTHON = $(VENV)/bin/python
VENV_PIP = $(VENV)/bin/pip
VENV_PYTEST = $(VENV)/bin/pytest

setup:
	@if [ ! -d "$(VENV)" ]; then \
		PYTHON_BIN=$$(which /opt/homebrew/bin/python3 || which python3.12 || which python3.11 || which python3.10 || which python3); \
		$$PYTHON_BIN -m venv $(VENV); \
	fi
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e ".[dev]"

run:
	@if [ ! -f "$(VENV_PYTHON)" ]; then \
		echo "Virtual environment not found. Please run 'make setup' first." >&2; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTHON) -m harness.main

test:
	@if [ ! -f "$(VENV_PYTEST)" ]; then \
		echo "Pytest not found in virtual environment. Please run 'make setup' first." >&2; \
		exit 1; \
	fi
	PYTHONPATH=src $(VENV_PYTEST) tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf build dist .coverage htmlcov $(VENV)
