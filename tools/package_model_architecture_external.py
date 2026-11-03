#!/usr/bin/env python3
"""Deterministically package the completed, preserved MAS v0.3 evidence archive."""
from __future__ import annotations
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import model_architecture_external as ex
from tools import check_model_architecture_external_archive as audit

ROOT=Path(__file__).resolve().parents[1]
SOURCE={
 "RESULTS-V0.3.json":"research/model-architecture-search/RESULTS-V0.3.json",
 "RESULTS-V0.3.json.journal.jsonl":"research/model-architecture-search/RESULTS-V0.3.json.journal.jsonl",
 "model_architecture_external.py":"tools/model_architecture_external.py",
 "protocol-v0.3.json":"research/model-architecture-search/protocol-v0.3.json",
 "preregistration-v0.3.md":"research/model-architecture-search/preregistration-v0.3.md",
 "test_model_architecture_external.py":"tests/test_model_architecture_external.py",
 "v0.3-execution.stdout.log":"research/model-architecture-search/v0.3-execution.stdout.log",
 "v0.3-exit-code.txt":"research/model-architecture-search/v0.3-exit-code.txt",
 "v0.3-replay-preflight-import-failure.txt":"research/model-architecture-search/v0.3-replay-preflight-import-failure.txt",
 "v0.3-replay-preflight.json":"research/model-architecture-search/v0.3-replay-preflight.json",
 "v0.3-replay-full.json":"research/model-architecture-search/v0.3-replay-full.json",
 "v0.3-replay.stdout.log":"research/model-architecture-search/v0.3-replay.stdout.log",
 "v0.3-replay-exit.txt":"research/model-architecture-search/v0.3-replay-exit.txt",
 "model_architecture_external_replay.py":"tools/model_architecture_external_replay.py",
 "check_model_architecture_external_archive.py":"tools/check_model_architecture_external_archive.py",
 "test_model_architecture_external_evidence.py":"tests/test_model_architecture_external_evidence.py",
 "RESULTS-V0.3.md":"research/model-architecture-search/RESULTS-V0.3.md",
}

def main():
    contents={name:(ROOT/path).read_bytes() for name,path in SOURCE.items()}
    if set(contents)!=audit.REQUIRED:
        raise ValueError("evidence set and independent auditor requirements diverged")
    manifest={name:ex.sha(data) for name,data in contents.items()}
    contents["manifest.json"]=ex.canonical(manifest)+b"\n"
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(contents):
            meta=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            meta.compress_type=zipfile.ZIP_DEFLATED
            meta.external_attr=0o644<<16
            z.writestr(meta,contents[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    raw=buf.getvalue()
    validated=audit.parse_archive(raw)
    out=ROOT/'research/model-architecture-search/archive-v0.3.zip.b64'
    if out.exists():
        raise FileExistsError("original archive cannot be overwritten")
    with out.open('xb') as h:
        h.write(base64.encodebytes(raw))
    print(json.dumps({"archive_path":str(out.relative_to(ROOT)),"archive_sha256":ex.sha(raw),
                      "archive_bytes":len(raw),"archive_base64_bytes":out.stat().st_size,
                      "members":len(contents),"validation":validated},indent=2))

if __name__=='__main__':
    main()
