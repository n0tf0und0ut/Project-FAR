#!/usr/bin/env python3
"""One-request provider access probe. Not a coding-agent experiment."""
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

MODEL = "gemini-3.1-pro-preview"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"
REQUEST_BODY = {"contents": [{"role": "user", "parts": [{"text": "Respond with exactly READY."}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 64,
                                     "thinkingConfig": {"thinkingLevel": "low"}}}
BODY = json.dumps(REQUEST_BODY, sort_keys=True, separators=(",", ":")).encode()
HASH = hashlib.sha256(BODY).hexdigest()


def contract():
    return {"schema": "far-workflow-access-probe/1.0",
            "experiment": "workflow-efficacy/0.1",
            "model_requested": MODEL, "endpoint": ENDPOINT, "request_sha256": HASH,
            "max_requests": 1, "benchmark_data_sent": False,
            "historical_swe_v2_reexecuted": False, "swe_v3_executed": False}


def probe(key):
    result = contract()
    result["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
    if not key:
        return dict(result, status="NO_CREDENTIAL", http_status=None)
    req = urllib.request.Request(ENDPOINT, BODY,
          headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            status = int(response.status)
            raw = response.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        return dict(result, status="PROVIDER_HTTP_ERROR", http_status=int(exc.code))
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return dict(result, status="PROVIDER_TRANSPORT_ERROR", error_class=type(exc).__name__)
    try:
        data = json.loads(raw)
        parts = data["candidates"][0]["content"]["parts"]
        answer = "".join(p.get("text", "") for p in parts if p.get("thought") is not True)
        version = data.get("modelVersion")
        if not isinstance(version, str) or not version.strip() or not answer.strip():
            raise ValueError("malformed response")
        return dict(result, status="ACCESS_VERIFIED", http_status=status,
                    observed_model_version=version,
                    total_token_count=data.get("usageMetadata", {}).get("totalTokenCount"))
    except (ValueError, TypeError, KeyError, IndexError):
        return dict(result, status="MALFORMED_PROVIDER_RESPONSE", http_status=status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("contract", "probe"))
    args = parser.parse_args()
    result = contract() if args.action == "contract" else probe(os.environ.get("GEMINI_API_KEY", ""))
    print(json.dumps(result, sort_keys=True))
    return 0 if args.action == "contract" or result["status"] == "ACCESS_VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
