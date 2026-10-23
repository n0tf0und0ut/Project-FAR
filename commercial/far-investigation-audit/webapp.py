"""Local-only research UI; opt-in networking, no user accounts or persistence.

Do not expose to the internet: this prototype has no authentication, user
isolation or security-reviewed production rate limiting.
"""
from __future__ import annotations
import json
import os
import re
import threading
import tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from acquire import AcquisitionError
from engine import InvalidBundle
from workflow import investigate

app = FastAPI(title="FAR Investigation Lab", version="0.4.3", docs_url=None, redoc_url=None)
_GATE = threading.BoundedSemaphore(value=1)


async def _bounded_body(request: Request, limit: int) -> bytearray:
    """Count actual transport bytes before retaining them or invoking a parser."""
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > limit:
            raise HTTPException(413, "request over size limit")
        raw.extend(chunk)
    return raw

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FAR Investigation Lab</title><style>
:root{font-family:system-ui,sans-serif;color:#e1e7ee;background:#0c1119}body{max-width:960px;margin:32px auto;padding:0 18px}
h1{font-size:30px}p{line-height:1.55;color:#aebac9}textarea,input,select{box-sizing:border-box;width:100%;background:#141d29;color:#e1e7ee;border:1px solid #344054;border-radius:7px;padding:12px;font:inherit}button{background:#b6d7ff;color:#111927;border:0;border-radius:7px;padding:13px 18px;font-weight:700;cursor:pointer}button:disabled{opacity:.5}label{display:block;margin:16px 0 6px}pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #293649;padding:20px;background:#111923;border-radius:8px;font-size:13px;line-height:1.45}.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:650px){.cols{grid-template-columns:1fr}}.small{font-size:13px}
</style></head><body><h1>FAR Investigation Lab</h1><p>Analyze an article, transcript, or other plain-text source. The output is a traceable research proposal, <strong>not</strong> an independently verified verdict. Citation presence does not prove source reliability or entailment.</p>
<label for="type">Source</label><select id="type"><option value="text">Paste text / transcript</option><option value="srt">SRT transcript</option><option value="vtt">WebVTT transcript</option><option value="html">HTML snippet</option><option value="url">Public HTTPS article (network opt-in at server)</option><option value="youtube">YouTube captions (optional yt-dlp and server network opt-in)</option></select>
<label for="source">Source text or URL</label><textarea rows="10" id="source" placeholder="Paste a claim-bearing speech, article, or transcript..."></textarea>
<label for="file">Or upload a local document or recording</label><input type="file" id="file" accept=".txt,.md,.html,.srt,.vtt,.pdf,.mp3,.wav,.m4a,.mp4,.mov,.webm,.ogg">
<label for="consent"><input type="checkbox" id="consent" style="width:auto"> I authorize external transcription of an uploaded recording if the local server has model access enabled.</label>
<div class="cols"><div><label for="evidence">Optional evidence excerpt</label><textarea id="evidence" rows="5" placeholder="Paste a source record; it will remain unverified until independently checked."></textarea></div><div><label for="id">Investigation ID</label><input id="id" value="case_001"><p class="small">No input is stored by the application; the server operator may have separate infrastructure logging. External network calls are off by default. No unsupported certainty is generated.</p></div></div>
<button id="run">Run investigation</button><p id="status" role="status"></p><pre id="report" hidden></pre><button id="download" hidden>Download JSON package</button><script>
'use strict'; let last=null;
const e=id=>document.getElementById(id);
e('run').addEventListener('click',async()=>{
 e('run').disabled=true;e('status').textContent='Investigating...';e('report').hidden=true;e('download').hidden=true;
 try{let kind=e('type').value;let field=e('source').value;let source=(kind==='url'||kind==='youtube')?{kind,url:field}:{kind,text:field};
 let evidence=e('evidence').value.trim();let payload={investigation_id:e('id').value,source,evidence_sources:evidence?[{kind:'text',text:evidence}]:[]};
 let result;
 if(e('file').files.length){const data=new FormData();data.set('file',e('file').files[0]);data.set('investigation_id',e('id').value);data.set('evidence_text',evidence);data.set('transcription_consent',e('consent').checked?'yes':'no');result=await fetch('/api/upload',{method:'POST',body:data});}
 else{result=await fetch('/api/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});}
 let data=await result.json();
 if(!result.ok)throw Error(data.detail||'Request failed');last=data;e('status').textContent='Completed with explicit uncertainty; source truth and semantic fidelity not certified.';e('report').textContent=data.report_md;e('report').hidden=false;e('download').hidden=false;
 }catch(err){e('status').textContent='Error: '+String(err.message)}finally{e('run').disabled=false}
});
e('download').addEventListener('click',()=>{if(!last)return;let blob=new Blob([JSON.stringify(last,null,2)],{type:'application/json'});let url=URL.createObjectURL(blob);let a=document.createElement('a');a.href=url;a.download='far-audit.json';a.click();URL.revokeObjectURL(url)});
</script></body></html>'''

@app.middleware("http")
async def security_headers(request: Request, call_next):
    # This research lab is intentionally restricted to local callers.
    # A public multi-user deployment requires a separate, reviewed auth layer.
    client = request.client.host if request.client else None
    if client not in {"127.0.0.1", "::1", "testclient"}:
        return JSONResponse({"detail":"local-only research service"}, status_code=403)
    # Loopback client addresses alone do not stop browser cross-site requests
    # or an attacker hostname resolving to loopback. Check the request's
    # authority and browser origin before parsing uploads or invoking providers.
    authority = request.headers.get("host", "").lower()
    local_host = re.fullmatch(r"(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?", authority)
    synthetic_host = client == "testclient" and re.fullmatch(r"testserver(?::[0-9]{1,5})?", authority)
    if not local_host and not synthetic_host:
        return JSONResponse({"detail":"local host required"}, status_code=403)
    origin = request.headers.get("origin")
    if origin is not None and origin.lower() != f"{request.url.scheme}://{authority}":
        return JSONResponse({"detail":"same-origin request required"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response

@app.get("/", response_class=HTMLResponse)
async def index():
    return PAGE

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "research", "model": "deterministic_heuristic", "external_truth_verified": False}

@app.post("/api/investigate")
async def analyze(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "JSON content type required")
    try:
        announced = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise HTTPException(400, "malformed content length")
    if announced < 0:
        raise HTTPException(400, "malformed content length")
    if announced > 450000:
        raise HTTPException(413, "request over size limit")
    # Content-Length may be absent or understated.
    raw = await _bounded_body(request, 450000)
    if not _GATE.acquire(blocking=False):
        raise HTTPException(429, "local research worker busy")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise InvalidBundle("request must be an object")
        # This prototype does not offer unauthenticated remote-model calls.
        if data.get("proposal_mode", "heuristic") != "heuristic" or data.get("discovery"):
            raise HTTPException(400, "web UI allows deterministic proposal mode only")
        permit_network = os.environ.get("FAR_LAB_NETWORK") == "I_ACCEPT_UNTRUSTED_REMOTE_FETCH"
        result = investigate(data, permit_network=permit_network)
        return JSONResponse(result)
    except (InvalidBundle, AcquisitionError, ValueError, TypeError, RecursionError) as exc:
        raise HTTPException(422, "invalid investigation: " + str(exc)[:250]) from exc
    finally:
        _GATE.release()



@app.post("/api/upload")
async def upload_document(request: Request):
    """Local-only upload; data never persisted after the request completes."""
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise HTTPException(415, "multipart upload required")
    try:
        size=int(request.headers["content-length"])
    except (ValueError, KeyError):
        raise HTTPException(411, "bounded content length required")
    if size < 1 or size > 16_000_000:
        raise HTTPException(413, "upload exceeds 16 MB transport cap")
    if not _GATE.acquire(blocking=False):
        raise HTTPException(429, "local research worker busy")
    form=None
    try:
        from starlette.datastructures import UploadFile
        # Bound the complete transport before multipart parsing can spool an
        # unbounded file to disk. Content-Length is an early check, not evidence
        # of the bytes actually received. Parsing sees only this bounded snapshot.
        body = bytes(await _bounded_body(request, 16_000_000))
        async def captured_body():
            return {"type": "http.request", "body": body, "more_body": False}
        bounded_request = Request(request.scope, captured_body)
        form=await bounded_request.form(max_files=1, max_fields=4)
        file=form.get("file")
        if not isinstance(file, UploadFile):
            raise InvalidBundle("uploaded file missing")
        ext=Path(file.filename or "").suffix.lower()
        kinds={".txt":"text", ".md":"text", ".html":"html", ".srt":"srt", ".vtt":"vtt",
               ".pdf":"pdf_file", ".mp3":"media_file", ".wav":"media_file", ".m4a":"media_file",
               ".mp4":"media_file", ".mov":"media_file", ".webm":"media_file", ".ogg":"media_file"}
        if ext not in kinds:
            raise InvalidBundle("unsupported upload extension")
        raw=await file.read(15_000_001)
        if not raw or len(raw)>15_000_000:
            raise InvalidBundle("upload body exceeds bounded source limit")
        inv_id=form.get("investigation_id", "uploaded_case")
        evidence=form.get("evidence_text", "")
        if not isinstance(inv_id,str) or not isinstance(evidence,str) or len(evidence.encode("utf-8"))>190_000:
            raise InvalidBundle("invalid form field")
        allow_model=(os.environ.get("FAR_LAB_MODEL") == "I_ACCEPT_EXTERNAL_TRANSCRIPTION"
                     and form.get("transcription_consent")=="yes")
        kind=kinds[ext]
        source={"kind":kind}
        request_config={"investigation_id":inv_id,"source":source,
                        "evidence_sources":([{"kind":"text","text":evidence}] if evidence.strip() else [])}
        if kind in {"text","html","srt","vtt"}:
            try:
                source["text"]=raw.decode("utf-8","strict")
            except UnicodeDecodeError as exc:
                raise InvalidBundle("file must be UTF-8") from exc
            outcome=investigate(request_config)
        else:
            if kind == "media_file" and not allow_model:
                raise HTTPException(403, "external transcription requires server enablement and explicit user consent")
            with tempfile.TemporaryDirectory(prefix="far-web-file-") as root:
                path=Path(root)/("source"+ext)
                path.write_bytes(raw)
                source["path"]=str(path)
                outcome=investigate(request_config,permit_files=True,permit_model=allow_model)
        return JSONResponse(outcome)
    except (InvalidBundle, AcquisitionError, OSError, ValueError, TypeError) as exc:
        raise HTTPException(422, "invalid uploaded source: "+str(exc)[:250]) from exc
    finally:
        if form is not None:
            await form.close()
        _GATE.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
