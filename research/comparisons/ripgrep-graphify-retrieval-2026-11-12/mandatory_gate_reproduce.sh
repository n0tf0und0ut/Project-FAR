#!/usr/bin/env bash
# Research-only local reproduction of the 24x3 Graphify-hook counterfactual.
# No FAR repository writes, agent hooks, git hooks or model-provider credentials.
# Linux x86_64, Python3.12, curl, tar, unzip, and network to GitHub/HuggingFace.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SHA=8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe
SOURCE_ARCHIVE_SHA=2ac7d3b0fe05bfadc97199e9fcbf6cfc6c74627f9039878532bfd12a943d9d3c
GRAPH_SHA=44684f162f115b4193d09b49ec42d0bee2e30751e0f2de662cfd55ac22f59625
MODEL_SHA=f530705d447660a4336c329981af164b471b60b974b1d808d57e8ec9fe23b239
RG_SHA=f401154e2393f9002ac77e419f9ee5521c18f4f8cd3e32293972f493ba06fce7
ORIGINAL_RUNNER_SHA=18748249368ae6f905fddfdd1b3268191e77b6cf89a93e8aad96e975aabd6b9c
PROTOCOL_SHA=64b58b30c274867d36844350de2836f6b382ed09a71471370eae8162129ec43c
ORACLE_SHA=abb4f420e829748de5c3932e7dfc277a4067c561d0ceca88ef26921459856fdc

hash_file() {
 local target="$1" expected="$2"
 printf '%s  %s\n' "$expected" "$target" | sha256sum -c --status || {
   echo "HASH MISMATCH: $target" >&2;exit 1; }
}
verify_frozen() {
 hash_file "$HERE/mandatory_gate_protocol.json" "$PROTOCOL_SHA"
 hash_file "$HERE/mandatory_gate_oracle.json" "$ORACLE_SHA"
 hash_file "$HERE/mandatory_gate_run.py" "$ORIGINAL_RUNNER_SHA"
}
verify_frozen

if [[ "${1:-}" == "--verify-receipts" ]]; then
 python3 - "$HERE" <<'PY'
import json,pathlib,sys,hashlib
d=pathlib.Path(sys.argv[1]);raw=d/'mandatory_gate_raw.jsonl'
if raw.is_file():
    text=raw.read_text()
else:
    import gzip
    zipped=d/'mandatory_gate_raw.jsonl.gz'
    if not zipped.is_file():raise SystemExit('Missing raw receipts: expected .jsonl or .jsonl.gz.')
    compressed=zipped.read_bytes()
    expected='310de9914bdfc140f972920db2e25c1288c225121200f160de5765863043265a'
    assert hashlib.sha256(compressed).hexdigest()==expected,'compressed receipts hash mismatch'
    text=gzip.decompress(compressed).decode()
assert hashlib.sha256(text.encode()).hexdigest()=='be8903fab02fc4ba94c41f51491331575c9f7e0ca279cc88f9ecbd4daad3d519'
r=[json.loads(x) for x in text.splitlines() if x.strip()]
assert len(r)==72,('incomplete',len(r))
assert len({(x['task_id'],x['arm']) for x in r})==72,'duplicate receipts'
p=json.loads((d/'mandatory_gate_protocol.json').read_text())
assert set(x['arm'] for x in r)==set(p['arms'])
for x in r:assert x.get('error') is None,x
print('PASS 72 completed unique task/arm receipts; independent scoring may now run')
PY
 exit 0
fi

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
 echo 'Requires Linux x86_64 for the pinned ripgrep binary.' >&2;exit 2
fi
RUNROOT="${1:-$(mktemp -d /tmp/far-graphify-mandatory-replay.XXXXXXXX)}"
mkdir -p "$RUNROOT/far" "$RUNROOT/agent_compare" "$RUNROOT/models" "$RUNROOT/rg"
for file in mandatory_gate_protocol.json mandatory_gate_oracle.json mandatory_gate_run.py mandatory_gate_resume.py mandatory_gate_analyze.py mandatory_gate_render.py mandatory_gate_coverage.py; do
 cp "$HERE/$file" "$RUNROOT/agent_compare/$file"
done
cp "$HERE"/{graphify_initial_extraction,graphify_repeat_extraction}.json "$RUNROOT/agent_compare/"

curl -fsSL --retry 3 --max-time 300 \
 "https://codeload.github.com/n0tf0und0ut/Project-FAR/tar.gz/$SOURCE_SHA" -o "$RUNROOT/far.tar.gz"
hash_file "$RUNROOT/far.tar.gz" "$SOURCE_ARCHIVE_SHA"
tar -xzf "$RUNROOT/far.tar.gz" -C "$RUNROOT/far" --strip-components=1

GRAPH_PATH="${FAR_GRAPH_PATH:-}"
if [[ -n "$GRAPH_PATH" ]]; then
 cp "$GRAPH_PATH" "$RUNROOT/graph.json"
else
 # Pinned Graphify output archive from the preceding 2026-11-12 study.
 curl -fsSL --retry 3 --max-time 300 \
   'https://d2ol7oe51mr4n9.cloudfront.net/user_3IVsV5OQ41U43FV2Cnr4dHkvb3g/82494e28-e248-4ef1-bcaf-c5f06cf3c3ba.zip' \
   -o "$RUNROOT/graphify-evidence.zip"
 unzip -p "$RUNROOT/graphify-evidence.zip" '*/graph.json' >"$RUNROOT/graph.json"
fi
hash_file "$RUNROOT/graph.json" "$GRAPH_SHA"

MODEL_PATH="${FAR_MODEL_PATH:-}"
if [[ -n "$MODEL_PATH" ]]; then
 cp "$MODEL_PATH" "$RUNROOT/models/model.gguf"
else
 curl -fsSL --retry 3 --max-time 1200 \
 'https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf' \
 -o "$RUNROOT/models/model.gguf"
fi
hash_file "$RUNROOT/models/model.gguf" "$MODEL_SHA"

curl -fsSL --retry 3 --max-time 300 \
 'https://github.com/BurntSushi/ripgrep/releases/download/14.1.1/ripgrep-14.1.1-x86_64-unknown-linux-musl.tar.gz' \
 -o "$RUNROOT/rg/rg.tgz"
tar -xzf "$RUNROOT/rg/rg.tgz" -C "$RUNROOT/rg"
RG="$RUNROOT/rg/ripgrep-14.1.1-x86_64-unknown-linux-musl/rg"
hash_file "$RG" "$RG_SHA"

python3 -m venv "$RUNROOT/.agentvenv"
PYTHONPATH= "$RUNROOT/.agentvenv/bin/python" -m pip install --disable-pip-version-check -q \
 --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu llama-cpp-python==0.3.36

# Only adapt two paths inside an isolated COPY of the frozen, SHA-verified original.
# This intentionally invalidates the script's original hash, so the new manifest
# declares its modified runner hash. No frozen evidence is rewritten.
python3 - "$RUNROOT/agent_compare/mandatory_gate_run.py" "$RUNROOT/models/model.gguf" "$RG" "$RUNROOT/agent_compare/mandatory_gate_resume.py" <<'PY'
from pathlib import Path
import sys,hashlib
p=Path(sys.argv[1]);s=p.read_text()
old_model="MODEL=pathlib.Path('/home/user/far-graphify-eval-20261112/agent_compare/models/Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf')"
old_rg="RG=pathlib.Path('/home/user/far-graphify-eval-20261112/ripgrep-14.1.1-x86_64-unknown-linux-musl/rg')"
assert s.count(old_model)==s.count(old_rg)==1
s=s.replace(old_model,'MODEL=pathlib.Path('+repr(sys.argv[2])+')')
s=s.replace(old_rg,'RG=pathlib.Path('+repr(sys.argv[3])+')')
p.write_text(s)
q=Path(sys.argv[4]);v=q.read_text()
old="EXPECTED='18748249368ae6f905fddfdd1b3268191e77b6cf89a93e8aad96e975aabd6b9c'"
assert v.count(old)==1
v=v.replace(old,"EXPECTED="+repr(hashlib.sha256(p.read_bytes()).hexdigest()))
q.write_text(v)
PY
cd "$RUNROOT/agent_compare"
PYTHONPATH= "$RUNROOT/.agentvenv/bin/python" mandatory_gate_run.py
python3 mandatory_gate_analyze.py
echo "REPRODUCED_IN=$RUNROOT"
echo 'Scores and hashes may vary across local inference runtimes; report any changes instead of altering frozen original receipts.'
