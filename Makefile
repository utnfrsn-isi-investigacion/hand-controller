.DEFAULT_GOAL := help
VENV          := .venv
PYTHON        := $(VENV)/bin/python
PIP           := $(VENV)/bin/pip

.PHONY: help install run test lint security venv clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	python -m venv $(VENV)

install: venv ## Install Python dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: ## Run the hand controller
	$(PYTHON) main.py

test: ## Run unit tests
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

lint: ## Run flake8 linter
	$(VENV)/bin/flake8 . --count --max-complexity=10 --max-line-length=127 \
		--statistics --exclude=__pycache__,_esp32,$(VENV)

security: ## Run bandit and pip-audit security checks
	$(VENV)/bin/bandit -r . --exclude=./_esp32,./tests
	$(VENV)/bin/pip-audit --requirement requirements.txt

config: ## Create config.json from example (skips if already exists)
	@test -f config.json && echo "config.json already exists, skipping." || \
		(cp config.example.json config.json && echo "Created config.json from config.example.json")

clean: ## Remove virtual environment and cache files
	rm -rf $(VENV) __pycache__ .pytest_cache htmlcov .coverage coverage.xml bandit-report.json
	find . -name "*.pyc" -delete
