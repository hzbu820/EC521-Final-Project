#!/bin/bash

cd slopspotter-cli
uv sync --native-tls
uv run slopspotter -i firefox
cd ../slopspotter-extension
npm run build

