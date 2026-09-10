.DEFAULT_GOAL := help
VENV          := .venv
PYTHON        := $(VENV)/bin/python
PIP           := $(VENV)/bin/pip
DECK          := docs/presentacion-expo-carreras.html

.PHONY: help install run test test-firmware lint security venv clean config present

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment (uses pyenv Python version from .python-version)
	pyenv exec python -m venv $(VENV)

install: venv ## Install Python dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: ## Run the hand controller
	$(PYTHON) main.py

test: ## Run unit tests
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

# Separate from `test` on purpose: PlatformIO is its own toolchain, not part
# of the .venv, and its first run downloads the Unity framework. CI runs both.
test-firmware: ## Run the ESP32 drive-logic tests natively (needs PlatformIO)
	$(MAKE) -C _esp32 test

lint: ## Run flake8 linter
	$(VENV)/bin/flake8 . --count --max-complexity=10 --max-line-length=127 \
		--statistics --exclude=__pycache__,_esp32,$(VENV)

security: ## Run bandit and pip-audit security checks
	$(VENV)/bin/bandit -r . --exclude=./_esp32,./tests,./$(VENV)
	# PYSEC-2026-1805: protobuf fix conflicts with mediapipe's protobuf<5 pin (see ci.yml)
	$(VENV)/bin/pip-audit --requirement requirements.txt --ignore-vuln PYSEC-2026-1805

config: ## Create config.json from example (skips if already exists)
	@test -f config.json && echo "config.json already exists, skipping." || \
		(cp config.example.json config.json && echo "Created config.json from config.example.json")

# Deliberately not xdg-open: it follows the text/html MIME default, which
# desktop apps (Electron ones especially) tend to hijack. Ask for a browser.
present: ## Open the Expo Carreras presentation in a browser
	@for b in "$$BROWSER" sensible-browser x-www-browser firefox google-chrome chromium open; do \
		if [ -n "$$b" ] && command -v "$$b" >/dev/null 2>&1; then \
			echo "Opening $(DECK) with $$b"; \
			nohup "$$b" "file://$(CURDIR)/$(DECK)" >/dev/null 2>&1 & \
			exit 0; \
		fi; \
	done; \
	echo "No browser found. Open $(DECK) manually (self-contained, no server needed)."

clean: ## Remove virtual environment and cache files
	rm -rf $(VENV) __pycache__ .pytest_cache htmlcov .coverage coverage.xml bandit-report.json
	find . -name "*.pyc" -delete
