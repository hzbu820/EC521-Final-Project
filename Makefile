SHELL := /bin/bash
.PHONY: all cli extension debug clean

all: cli extension debug

cli:
	@cd slopspotter-cli && \
	if uv -V &>/dev/null; then \
		echo "Using uv to sync dependencies..."; \
		uv sync --native-tls; \
	else \
		echo "uv not found, falling back to pip and venv..."; \
		python3 -m venv .venv --prompt='slopspotter-cli'; \
		source .venv/bin/activate; \
		python3 -m pip install .; \
	fi && \
	echo "Installing Slopspotter manifests for Firefox..."; \
	source .venv/bin/activate && \
	slopspotter -i firefox

extension:
	@cd slopspotter-extension && npm install && npm run build

debug:
	@firefox about:debugging &
