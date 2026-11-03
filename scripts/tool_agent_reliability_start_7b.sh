#!/usr/bin/env bash
# Exact larger local backend; no provider keys or inference outside localhost.
set -euo pipefail
OLLAMA_RELEASE="v0.34.0"
ARCHIVE_SHA256="cf95886728959aa09910bb34de5cca1cc5a8f68003b5597197d3f2c2d57c0804"
MODEL="qwen2.5-coder:7b"
ARCHIVE="${RUNNER_TEMP:-/tmp}/ollama-linux-amd64.tar.zst"
free -m
nproc
curl -fL --retry 3 --connect-timeout 30 \
  "https://github.com/ollama/ollama/releases/download/${OLLAMA_RELEASE}/ollama-linux-amd64.tar.zst" \
  -o "$ARCHIVE"
echo "${ARCHIVE_SHA256}  $ARCHIVE" | sha256sum --check --status
sudo tar --zstd -xf "$ARCHIVE" -C /usr
test -x /usr/bin/ollama
export OLLAMA_HOST="127.0.0.1:11434"
export OLLAMA_NUM_PARALLEL="1"
export OLLAMA_CONTEXT_LENGTH="8192"
export OLLAMA_MAX_LOADED_MODELS="1"
ollama serve > "${RUNNER_TEMP:-/tmp}/tool-agent-7b-ollama.log" 2>&1 &
echo "Ollama PID $! (CPU-local)"
ready=0
for attempt in $(seq 1 40); do
  if curl -fsS --connect-timeout 2 http://127.0.0.1:11434/api/tags >/dev/null; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1 || { echo "Ollama local server failed to start" >&2; exit 1; }
ollama pull "$MODEL"
python - <<'PY'
from tools.tool_agent_reliability import installed_digest, load_protocol
p=load_protocol()
print("model:",p['model']['name'],"sha256:",installed_digest(p['model']))
PY
