.PHONY: help setup install-uv sync run test

help:
	@echo "Targets:"
	@echo "  setup       - Install uv (if needed) and ensure local virtualenv is up to date"
	@echo "  install-uv  - Install Astral's uv package manager if not present"
	@echo "  sync        - Create/update a local virtualenv using uv and uv.lock (reproducible)"
	@echo "  run         - Run the BusyBuddy agent via uv"

setup: install-uv sync

install-uv:
	@if command -v uv >/dev/null 2>&1; then \
		echo "uv already installed: $$(uv --version)"; \
	else \
		echo "Installing uv..."; \
		curl -LsSf "https://astral.sh/uv/install.sh" | sh; \
		echo "uv installed to $$HOME/.local/bin"; \
	fi

# This ensures a consistent environment for the agent
sync:
	uv sync --frozen

run:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "uv is not installed. It is required for running the agent. Please install it with 'make install-uv' or follow the instructions on https://docs.astral.sh/uv/getting-started/installation/."; \
		exit 1; \
	fi
	@if [ ! -d .venv ]; then \
		echo "Note: .venv not found. The agent may fail to run. If it does, run 'make sync' and then try again."; \
	fi
	@if [ ! -f .env ] && [ -z "$$GEMINI_API_KEY" ]; then \
		echo "Note: GEMINI_API_KEY not set and no .env found; the agent may fail to authenticate."; \
	fi
	uv run python -m src.code_explorer.main

test:
	uv run pytest -q
