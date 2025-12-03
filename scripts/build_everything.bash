#!/bin/bash
#
## @file scripts/build_everything.bash
## @author Victor Mercola
## @date 2025-12-02
## @brief Build the entire project on Linux

## Build Slopspotter CLI, install manifests

cd slopspotter-cli

if uv -V &>/dev/null; then
	# Build with `uv` if it's available
	uv sync --native-tls
else
	# Build with `pip` & `venv` as a fallback
	python3 -m venv .venv --prompt='slopspotter-cli'
	source .venv/bin/activate
	python3 -m pip install .
fi

source .venv/bin/activate
slopspotter -i firefox

cd ..

## Build Slopspotter extension, install dependencies, build

cd slopspotter-extension
npm install
npm run build

## Open Firefox to about:debugging

firefox about:debugging
