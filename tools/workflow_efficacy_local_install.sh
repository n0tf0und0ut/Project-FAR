#!/usr/bin/env bash
set -euo pipefail
export OLLAMA_HOST=127.0.0.1:11434
sudo apt-get update -qq
sudo apt-get install -y zstd
curl -fsSL https://ollama.com/install.sh -o "$RUNNER_TEMP/ollama-install.sh"
OLLAMA_VERSION=0.12.7 sh "$RUNNER_TEMP/ollama-install.sh"
ollama --version
ollama serve > "$RUNNER_TEMP/ollama.log" 2>&1 &
for i in $(seq 1 45); do
  curl --silent --fail http://127.0.0.1:11434/api/version && break
  sleep 2
done
ollama pull qwen2.5-coder:1.5b
docker pull python:3.12-slim
python -c "from tools.workflow_efficacy_local_ollama import model_sha; print(model_sha())"
