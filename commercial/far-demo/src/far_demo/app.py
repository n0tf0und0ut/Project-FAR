from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response

from far_decision_integrity.adjudicate import adjudicate
from far_decision_integrity.model import DecisionPackage, PackageValidationError
from far_decision_integrity.report import report_payload

from .formats import ACCEPT_ATTRIBUTE, parse_package_file
from .augmentation import router as augmentation_router
from .semantic import router as semantic_router

MAX_BYTES = 10_000_000
app = FastAPI(title="Project FAR Demo", version="0.8.0")
app.include_router(augmentation_router)
app.include_router(semantic_router)


def _package(payload: dict[str, Any]) -> DecisionPackage:
    return DecisionPackage.from_dict(payload)


def _sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _nodes(package: DecisionPackage) -> dict[str, dict[str, Any]]:
    return {
        node.node_id: {
            "id": node.node_id,
            "kind": node.kind,
            "statement": node.statement,
            "attributes": node.attributes,
        }
        for node in package.nodes
    }


def _dependencies(package: DecisionPackage) -> list[dict[str, str]]:
    return [
        {"source_id": item.source_id, "target_id": item.target_id, "relation": item.relation}
        for item in package.dependencies
    ]


def _generic_narrative(
    *,
    baseline: DecisionPackage,
    candidate: DecisionPackage,
    status: str,
    removed: list[str],
    added: list[str],
    baseline_nodes: dict[str, dict[str, Any]],
) -> dict[str, str]:
    headline = {
        "unsupported": "The candidate decision lost required support recorded in the baseline.",
        "unverifiable": "The supplied evidence is insufficient to verify the candidate decision.",
        "underdetermined": "The supplied evidence supports more than one admissible conclusion.",
        "justified": "The supplied evidence supports the candidate decision.",
    }[status]
    decision_type = candidate.decision_type or baseline.decision_type or "decision"
    removed_statements = [
        baseline_nodes.get(node_id, {"statement": node_id})["statement"] for node_id in removed
    ]
    if removed_statements:
        noun = "dependency" if len(removed_statements) == 1 else "dependencies"
        summary = (
            f"FAR compared the baseline and candidate {decision_type} packages. "
            f"The candidate no longer records {len(removed_statements)} {noun} that supported "
            "the baseline decision: " + "; ".join(removed_statements)
        )
    elif added:
        noun = "dependency" if len(added) == 1 else "dependencies"
        summary = (
            f"FAR compared the baseline and candidate {decision_type} packages. "
            f"The candidate records {len(added)} additional decision {noun}."
        )
    else:
        summary = (
            f"FAR compared the baseline and candidate {decision_type} packages. "
            "No direct decision-root dependency additions or removals were recorded."
        )
    return {
        "headline": headline,
        "plain_summary": summary,
        "why_it_matters": (
            "FAR evaluates only supplied nodes, dependencies, requirements, and declared unknowns. "
            "It does not infer hidden reasoning, external truth, safety, or regulatory compliance."
        ),
    }


def _present(
    baseline: DecisionPackage,
    candidate: DecisionPackage,
    *,
    narrative: dict[str, str] | None = None,
) -> dict[str, Any]:
    baseline_adjudication = adjudicate(baseline)
    candidate_adjudication = adjudicate(candidate)
    baseline_report = report_payload(baseline_adjudication)
    candidate_report = report_payload(candidate_adjudication)
    baseline_nodes = _nodes(baseline)
    candidate_nodes = _nodes(candidate)

    baseline_incoming = {
        item.source_id for item in baseline.dependencies if item.target_id == baseline.decision_root
    }
    candidate_incoming = {
        item.source_id for item in candidate.dependencies if item.target_id == candidate.decision_root
    }
    removed = sorted(baseline_incoming - candidate_incoming)
    added = sorted(candidate_incoming - baseline_incoming)

    structural_changes: list[dict[str, Any]] = []
    for node_id in removed:
        required = node_id in baseline.authorization_requirements
        structural_changes.append(
            {
                "type": "authorization_dependency_removed" if required else "decision_dependency_removed",
                "severity": "critical" if required else "high",
                "title": "Required authorization removed" if required else "Decision support removed",
                "description": baseline_nodes.get(node_id, {"statement": node_id})["statement"],
                "node_id": node_id,
            }
        )
    for node_id in added:
        structural_changes.append(
            {
                "type": "decision_dependency_added",
                "severity": "review",
                "title": "New decision support introduced",
                "description": candidate_nodes.get(node_id, {"statement": node_id})["statement"],
                "node_id": node_id,
            }
        )

    rule_findings: list[dict[str, Any]] = []
    baseline_rule_ids = {finding["rule_id"] for finding in baseline_report["findings"]}
    for finding in candidate_report["findings"]:
        if finding["rule_id"] not in baseline_rule_ids:
            rule_findings.append(
                {
                    "type": finding["rule_id"],
                    "severity": "critical" if finding["severity"] == "error" else "review",
                    "title": "Missing authorization dependency"
                    if finding["rule_id"] == "authorization-dependency-missing"
                    else finding["rule_id"].replace("-", " ").title(),
                    "description": finding["message"],
                    "node_id": finding.get("node_id"),
                }
            )

    status = candidate_adjudication.status.value
    presentation = narrative or _generic_narrative(
        baseline=baseline,
        candidate=candidate,
        status=status,
        removed=removed,
        added=added,
        baseline_nodes=baseline_nodes,
    )
    release_decision = {
        "justified": "PASS",
        "unsupported": "BLOCKED",
        "unverifiable": "REVIEW_REQUIRED",
        "underdetermined": "REVIEW_REQUIRED",
    }[status]
    if release_decision == "PASS" and removed:
        release_decision = "REVIEW_REQUIRED"

    artifact = {
        "schema": "far-demo-report/0.8",
        "engine": "far-decision-integrity/1.0.0",
        "release_decision": release_decision,
        "baseline": baseline_report,
        "candidate": candidate_report,
        "comparison": {
            "removed_decision_dependencies": removed,
            "added_decision_dependencies": added,
            "status_transition": [
                baseline_adjudication.status.value,
                candidate_adjudication.status.value,
            ],
        },
        "claim_boundary": "FAR evaluates only supplied packages and recorded dependencies. It does not infer hidden reasoning, external truth, safety, or regulatory compliance.",
    }
    artifact["sha256"] = _sha(artifact)

    return {
        "status": status,
        "release_decision": release_decision,
        "headline": presentation["headline"],
        "plain_summary": presentation["plain_summary"],
        "why_it_matters": presentation["why_it_matters"],
        "status_transition": [
            baseline_adjudication.status.value,
            candidate_adjudication.status.value,
        ],
        "structural_changes": structural_changes,
        "rule_findings": rule_findings,
        "changes": structural_changes + rule_findings,
        "unknowns": list(candidate.unknowns),
        "trace_completeness": candidate.trace_completeness,
        "baseline": {
            "nodes": list(baseline_nodes.values()),
            "dependencies": _dependencies(baseline),
            "root": baseline.decision_root,
        },
        "candidate": {
            "nodes": list(candidate_nodes.values()),
            "dependencies": _dependencies(candidate),
            "root": candidate.decision_root,
        },
        "artifact": artifact,
    }


SAMPLE_BASELINE = {
    "schema_version": "far-decision-package/0.1",
    "decision_id": "treasury-wire-baseline-741",
    "decision_type": "autonomous-cross-border-treasury-payment",
    "policy_version": "treasury-control-plane-v12",
    "decision_root": "execute-wire",
    "proposed_action": {
        "type": "execute_cross_border_wire",
        "amount_usd": 2400000,
        "beneficiary": "NovaGrid Systems GmbH",
        "destination": "DE",
    },
    "nodes": [
        {"node_id": "invoice-match", "kind": "evidence", "statement": "Invoice NG-8821 matches the executed master services agreement and purchase order.", "attributes": {"valid": True}},
        {"node_id": "vendor-identity", "kind": "evidence", "statement": "Beneficiary identity and bank ownership were verified against the approved vendor registry.", "attributes": {"valid": True}},
        {"node_id": "budget-envelope", "kind": "rule", "statement": "The payment remains inside the Q3 infrastructure capital allocation.", "attributes": {"valid": True}},
        {"node_id": "sanctions-clearance", "kind": "authorization", "statement": "The compliance service cleared the beneficiary and destination against current sanctions controls.", "attributes": {"valid": True}},
        {"node_id": "treasury-approval", "kind": "authorization", "statement": "A treasury controller approved wires above the autonomous execution threshold.", "attributes": {"valid": True}},
        {"node_id": "account-attestation", "kind": "evidence", "statement": "The destination account fingerprint matches the previously attested supplier account.", "attributes": {"valid": True}},
        {"node_id": "anomaly-screen", "kind": "evidence", "statement": "The transaction passed velocity, geography, amount, and beneficiary anomaly screening.", "attributes": {"valid": True}},
        {"node_id": "execute-wire", "kind": "decision", "statement": "Execute the $2.4M cross-border supplier wire.", "attributes": {"valid": True}},
    ],
    "dependencies": [
        {"source_id": "invoice-match", "target_id": "execute-wire", "relation": "supports"},
        {"source_id": "vendor-identity", "target_id": "execute-wire", "relation": "supports"},
        {"source_id": "budget-envelope", "target_id": "execute-wire", "relation": "constrains"},
        {"source_id": "sanctions-clearance", "target_id": "execute-wire", "relation": "authorizes"},
        {"source_id": "treasury-approval", "target_id": "execute-wire", "relation": "authorizes"},
        {"source_id": "account-attestation", "target_id": "execute-wire", "relation": "supports"},
        {"source_id": "anomaly-screen", "target_id": "execute-wire", "relation": "supports"},
    ],
    "authorization_requirements": ["sanctions-clearance", "treasury-approval"],
    "unknowns": [],
    "trace_completeness": 1.0,
    "metadata": {"release": "7.4.0", "environment": "production-shadow"},
}

SAMPLE_CANDIDATE = {
    **SAMPLE_BASELINE,
    "decision_id": "treasury-wire-candidate-742",
    "dependencies": [
        {"source_id": "invoice-match", "target_id": "execute-wire", "relation": "supports"},
        {"source_id": "vendor-identity", "target_id": "execute-wire", "relation": "supports"},
        {"source_id": "budget-envelope", "target_id": "execute-wire", "relation": "constrains"},
        {"source_id": "account-attestation", "target_id": "execute-wire", "relation": "supports"},
        {"source_id": "anomaly-screen", "target_id": "execute-wire", "relation": "supports"},
    ],
    "unknowns": [
        "Whether sanctions clearance occurred outside the captured execution graph.",
        "Whether treasury approval was bypassed by an undocumented emergency path.",
        "Whether the release optimization altered other high-value payment routes.",
    ],
    "trace_completeness": 0.76,
    "metadata": {"release": "7.4.1", "environment": "production-shadow"},
}

SAMPLE_NARRATIVE = {
    "headline": "Release 7.4.1 executed the same $2.4M wire after losing two required controls.",
    "plain_summary": "Outcome-based evaluation reports success in both releases: the supplier was paid. FAR reconstructed the admissibility path and found that the candidate no longer connects sanctions clearance or treasury-controller authorization to the payment decision.",
    "why_it_matters": "The visible business result did not change. The control structure did. FAR treats that as a release-blocking integrity regression and preserves the remaining uncertainty instead of converting missing evidence into confidence.",
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "far-demo", "engine": "far-decision-integrity"}


@app.get("/api/example")
def example() -> dict[str, Any]:
    return _present(
        _package(SAMPLE_BASELINE),
        _package(SAMPLE_CANDIDATE),
        narrative=SAMPLE_NARRATIVE,
    )


@app.get("/api/example/report")
def example_report() -> Response:
    payload = example()["artifact"]
    return Response(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=far-verification-report.json"},
    )


@app.post("/api/analyze")
async def analyze(
    baseline: UploadFile = File(...), candidate: UploadFile = File(...)
) -> JSONResponse:
    try:
        baseline_bytes = await baseline.read(MAX_BYTES + 1)
        candidate_bytes = await candidate.read(MAX_BYTES + 1)
        if len(baseline_bytes) > MAX_BYTES or len(candidate_bytes) > MAX_BYTES:
            raise ValueError("Each upload must be 10 MB or smaller.")
        baseline_package = _package(parse_package_file(baseline.filename or "", baseline_bytes))
        candidate_package = _package(parse_package_file(candidate.filename or "", candidate_bytes))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        PackageValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(400, str(exc)) from exc
    return JSONResponse(_present(baseline_package, candidate_package))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE.replace("__ACCEPT__", ACCEPT_ATTRIBUTE)


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#07090d">
<title>FAR — Decision integrity infrastructure</title>
<style>
:root{--bg:#07090d;--panel:#0c1017;--panel2:#111722;--panel3:#161d2a;--ink:#f5f7fb;--muted:#8d98aa;--line:rgba(255,255,255,.09);--line2:rgba(255,255,255,.16);--blue:#6ea8fe;--blue2:#377dff;--red:#ff746c;--redsoft:rgba(255,116,108,.1);--green:#52d39a;--amber:#f7c86b;--white:#f8fafc;--shadow:0 50px 140px rgba(0,0,0,.45);font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 76% 0%,rgba(55,125,255,.14),transparent 28%),linear-gradient(180deg,#080a0f 0%,#07090d 42%,#090c12 100%);color:var(--ink);overflow-x:hidden}button,input{font:inherit}.shell{width:min(1360px,calc(100% - 40px));margin:auto}.nav{height:78px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);position:relative;z-index:5}.brand{display:flex;align-items:center;gap:12px;font-weight:760;letter-spacing:-.03em}.sigil{width:30px;height:30px;border:1px solid var(--line2);border-radius:9px;position:relative;background:linear-gradient(145deg,#151c29,#090c12)}.sigil:before,.sigil:after{content:"";position:absolute;background:var(--blue)}.sigil:before{width:12px;height:1px;left:8px;top:9px;box-shadow:0 5px 0 rgba(110,168,254,.7),0 10px 0 rgba(110,168,254,.35)}.sigil:after{width:1px;height:12px;left:14px;top:8px;opacity:.5}.navmeta{display:flex;gap:22px;align-items:center;color:var(--muted);font-size:13px}.live{display:inline-flex;align-items:center;gap:8px}.dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 18px rgba(82,211,154,.7)}.hero{min-height:760px;padding:88px 0 70px;display:grid;grid-template-columns:minmax(0,1.1fr) minmax(390px,.9fr);gap:76px;align-items:center}.kicker{font-size:12px;letter-spacing:.15em;text-transform:uppercase;color:var(--blue);margin-bottom:24px}.hero h1{font-size:clamp(60px,7.5vw,108px);line-height:.9;letter-spacing:-.075em;font-weight:560;margin:0;max-width:900px}.hero h1 span{color:#7f8da4}.hero p{font-size:clamp(19px,2vw,27px);line-height:1.4;color:#aeb7c6;max-width:790px;margin:34px 0}.heroactions{display:flex;gap:12px;flex-wrap:wrap}.primary,.ghost{border-radius:11px;padding:15px 20px;font-weight:690;cursor:pointer;transition:.22s ease}.primary{border:1px solid var(--white);background:var(--white);color:#080a0f}.primary:hover{transform:translateY(-1px);box-shadow:0 10px 30px rgba(255,255,255,.13)}.ghost{border:1px solid var(--line2);background:transparent;color:var(--ink)}.ghost:hover{background:rgba(255,255,255,.05)}.heroPanel{background:linear-gradient(180deg,rgba(17,23,34,.92),rgba(10,14,21,.96));border:1px solid var(--line2);border-radius:24px;box-shadow:var(--shadow);overflow:hidden;position:relative}.heroPanel:before{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 28%,rgba(110,168,254,.07) 50%,transparent 72%);transform:translateX(-100%);animation:sweep 6s infinite}@keyframes sweep{60%,100%{transform:translateX(100%)}}.terminalHead{height:48px;display:flex;align-items:center;justify-content:space-between;padding:0 17px;border-bottom:1px solid var(--line);font-size:12px;color:var(--muted)}.windowDots{display:flex;gap:6px}.windowDots i{width:7px;height:7px;border-radius:50%;background:#30394a}.terminalBody{padding:24px}.releaseRow{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding:17px 0;border-bottom:1px solid var(--line)}.releaseRow:last-child{border:0}.releaseRow small{display:block;color:var(--muted);margin-bottom:7px}.releaseRow strong{font-size:15px}.mono{font-family:"SFMono-Regular",Consolas,monospace}.badge{font-size:11px;padding:6px 9px;border-radius:999px;border:1px solid var(--line2);white-space:nowrap}.badge.red{color:#ffaaa5;border-color:rgba(255,116,108,.3);background:var(--redsoft)}.badge.green{color:#86e3b9;border-color:rgba(82,211,154,.28);background:rgba(82,211,154,.08)}.heroStat{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border-top:1px solid var(--line)}.heroStat div{background:#0b0f16;padding:18px}.heroStat b{display:block;font-size:21px;margin-bottom:5px}.heroStat span{font-size:11px;color:var(--muted)}.section{padding:100px 0;border-top:1px solid var(--line)}.sectionHead{display:grid;grid-template-columns:190px 1fr;gap:50px;margin-bottom:46px}.sectionLabel{font-size:12px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted)}.section h2{font-size:clamp(40px,4.7vw,70px);line-height:1;letter-spacing:-.055em;font-weight:560;margin:0;max-width:970px}.sectionLead{font-size:19px;line-height:1.58;color:#9da8b9;max-width:850px;margin:25px 0 0}.scenarioBar{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:16px;overflow:hidden;margin-bottom:18px}.scenarioBar div{background:var(--panel);padding:20px}.scenarioBar span{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:9px}.scenarioBar strong{font-size:16px}.workspace{display:grid;grid-template-columns:1fr 88px 1fr;gap:0;align-items:stretch}.release{background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:26px;min-width:0}.releaseHead{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:28px}.releaseHead span{color:var(--muted);font-size:12px}.releaseHead h3{font-size:27px;margin:7px 0 0;letter-spacing:-.035em}.bridge{display:flex;align-items:center;justify-content:center;position:relative}.bridge:before{content:"";width:100%;height:1px;background:linear-gradient(90deg,var(--line2),var(--blue),var(--line2))}.bridge b{position:absolute;width:42px;height:42px;border-radius:50%;display:grid;place-items:center;background:#0a0d13;border:1px solid var(--line2);color:var(--blue)}.graph{display:grid;gap:10px}.node{display:grid;grid-template-columns:12px 1fr auto;gap:12px;align-items:center;padding:14px 15px;border:1px solid var(--line);border-radius:12px;background:#0a0e15;transition:.25s}.node:hover{border-color:var(--line2);transform:translateX(2px)}.node i{width:8px;height:8px;border-radius:50%;background:#718096}.node.auth i{background:var(--blue)}.node.rule i{background:var(--amber)}.node.decision i{background:var(--green)}.node.removed{border-color:rgba(255,116,108,.32);background:rgba(255,116,108,.055)}.node.removed i{background:var(--red)}.node b{font-size:13px}.node em{font-style:normal;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}.node.removed em{color:#ffaaa5}.decisionLine{margin-top:14px;padding:17px;border-radius:13px;border:1px solid rgba(82,211,154,.2);background:rgba(82,211,154,.055);display:flex;justify-content:space-between;align-items:center;gap:20px}.decisionLine b{font-size:14px}.decisionLine span{font-family:"SFMono-Regular",Consolas,monospace;font-size:12px;color:#86e3b9}.auditAction{display:flex;justify-content:center;margin-top:30px}.auditAction .primary{min-width:250px}.statusRail{display:none;margin-top:22px;border:1px solid var(--line);background:var(--panel);border-radius:16px;padding:16px}.statusRail.show{display:block}.statusRailTop{display:flex;justify-content:space-between;gap:20px;align-items:center}.progress{height:3px;background:#202735;border-radius:99px;overflow:hidden;margin-top:13px}.progress i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--blue2),#8bb8ff);transition:width .5s ease}.result{display:none;background:linear-gradient(180deg,#101620,#0b0f16);border:1px solid var(--line2);border-radius:26px;overflow:hidden;box-shadow:var(--shadow)}.result.show{display:block}.resultTop{padding:30px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:1fr auto;gap:30px;align-items:start}.resultEyebrow{font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);margin-bottom:16px}.result h2{font-size:clamp(38px,5vw,68px);max-width:1000px}.decisionBadge{padding:14px 16px;border-radius:12px;background:var(--redsoft);border:1px solid rgba(255,116,108,.3);color:#ffaaa5;font-weight:760;letter-spacing:.05em}.resultBody{display:grid;grid-template-columns:1.25fr .75fr}.resultNarrative{padding:30px;border-right:1px solid var(--line)}.resultNarrative p{font-size:18px;line-height:1.6;color:#aab4c3;margin:0 0 20px}.findings{display:grid;gap:10px;margin-top:25px}.finding{padding:16px;border-radius:12px;border:1px solid rgba(255,116,108,.22);background:rgba(255,116,108,.055)}.finding b{display:block;color:#ffaaa5;margin-bottom:6px}.finding span{color:#aeb7c6;font-size:14px;line-height:1.45}.resultSide{padding:30px}.metric{padding:18px 0;border-bottom:1px solid var(--line)}.metric:first-child{padding-top:0}.metric:last-child{border:0}.metric span{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.09em;margin-bottom:8px}.metric b{font-size:24px;letter-spacing:-.03em}.unknowns{margin-top:22px;padding:16px;border:1px solid rgba(247,200,107,.2);background:rgba(247,200,107,.055);border-radius:12px;color:#c7b98e;font-size:14px;line-height:1.5}.resultActions{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}.resultActions a{color:var(--blue);font-weight:650;text-decoration:none}.uploadShell{display:grid;grid-template-columns:.8fr 1.2fr;gap:40px}.uploadCopy{font-size:18px;line-height:1.6;color:#9da8b9}.formatCloud{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}.formatCloud span{padding:7px 9px;border:1px solid var(--line);border-radius:8px;font-size:11px;color:#b5bfce;background:var(--panel)}.uploadPanel{background:var(--panel);border:1px solid var(--line2);border-radius:20px;padding:22px}.upload{display:grid;grid-template-columns:1fr 1fr;gap:12px}.file{border:1px dashed rgba(255,255,255,.18);background:#0a0e15;border-radius:14px;padding:18px;font-size:13px;color:#c2cad6}.file input{display:block;margin-top:13px;max-width:100%;color:var(--muted)}.support{color:var(--muted);font-size:12px;line-height:1.5;margin-top:13px}.error{color:var(--red);font-size:13px}details{margin-top:17px;color:#aeb7c6}summary{cursor:pointer;color:#d7dce5}pre{white-space:pre-wrap;max-height:440px;overflow:auto;background:#05070a;border:1px solid var(--line);border-radius:13px;padding:18px;color:#c4d5ef;font-size:11px}footer{padding:36px 0 60px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:24px;color:var(--muted);font-size:12px}.mobileOnly{display:none}@media(max-width:980px){.hero{grid-template-columns:1fr;min-height:auto}.heroPanel{max-width:760px}.sectionHead{grid-template-columns:1fr;gap:14px}.workspace{grid-template-columns:1fr}.bridge{height:70px}.bridge:before{width:1px;height:100%;background:linear-gradient(180deg,var(--line2),var(--blue),var(--line2))}.scenarioBar{grid-template-columns:1fr 1fr}.resultBody,.uploadShell{grid-template-columns:1fr}.resultNarrative{border-right:0;border-bottom:1px solid var(--line)}}@media(max-width:620px){.shell{width:min(100% - 28px,1360px)}.nav{height:66px}.navmeta span:not(.live){display:none}.hero{padding:58px 0}.hero h1{font-size:clamp(50px,15vw,72px)}.hero p{font-size:18px}.heroStat{grid-template-columns:1fr}.section{padding:72px 0}.scenarioBar{grid-template-columns:1fr}.release{padding:18px}.resultTop{grid-template-columns:1fr;padding:22px}.resultNarrative,.resultSide{padding:22px}.result h2{font-size:38px;line-height:1.03}.upload{grid-template-columns:1fr}.primary,.ghost{width:100%}.heroactions{display:grid}.mobileOnly{display:block}footer{flex-direction:column}}
</style>
</head>
<body>
<main class="shell">
<nav class="nav"><div class="brand"><span class="sigil"></span>FAR</div><div class="navmeta"><span>Decision integrity infrastructure</span><span class="live"><i class="dot"></i>Verifier online</span></div></nav>
<header class="hero">
<div><div class="kicker">Release assurance for autonomous systems</div><h1>Your eval says <span>pass.</span><br>FAR asks why.</h1><p>AI systems can preserve the visible outcome while silently dropping the evidence, policy, and authorization that made the decision admissible.</p><div class="heroactions"><button class="primary" onclick="document.getElementById('case').scrollIntoView()">Investigate release 7.4.1</button><button class="ghost" onclick="document.getElementById('upload').scrollIntoView()">Analyze your own evidence</button></div></div>
<aside class="heroPanel"><div class="terminalHead"><span class="windowDots"><i></i><i></i><i></i></span><span class="mono">production-shadow / treasury-agent</span></div><div class="terminalBody"><div class="releaseRow"><div><small>Observed action</small><strong>$2.4M supplier wire executed</strong></div><span class="badge green">OUTPUT MATCH</span></div><div class="releaseRow"><div><small>Candidate release</small><strong class="mono">7.4.1+latency-opt</strong></div><span class="badge red">CONTROL DRIFT</span></div><div class="releaseRow"><div><small>FAR hypothesis</small><strong>Same result. Different admissibility.</strong></div><span class="badge">READY</span></div></div><div class="heroStat"><div><b>2</b><span>required controls at risk</span></div><div><b>76%</b><span>trace completeness</span></div><div><b>0</b><span>output-test failures</span></div></div></aside>
</header>
<section class="section" id="case"><div class="sectionHead"><div class="sectionLabel">Case 01 / Treasury</div><div><h2>The wire succeeded. The release still failed.</h2><p class="sectionLead">A production-shadow treasury agent approves a cross-border infrastructure payment. Release 7.4.1 improves latency and produces the exact same external result—but its recorded decision path no longer depends on sanctions clearance or treasury-controller approval.</p></div></div>
<div class="scenarioBar"><div><span>Action</span><strong>$2.4M cross-border wire</strong></div><div><span>Beneficiary</span><strong>NovaGrid Systems GmbH</strong></div><div><span>Output evaluation</span><strong>Pass in both releases</strong></div><div><span>Integrity question</span><strong>Were required controls preserved?</strong></div></div>
<div class="workspace"><article class="release"><div class="releaseHead"><div><span>Approved baseline</span><h3>Release 7.4.0</h3></div><span class="badge green">JUSTIFIED</span></div><div class="graph"><div class="node"><i></i><b>Invoice + contract match</b><em>evidence</em></div><div class="node"><i></i><b>Vendor identity verified</b><em>evidence</em></div><div class="node rule"><i></i><b>Inside Q3 capital envelope</b><em>policy</em></div><div class="node auth"><i></i><b>Sanctions clearance</b><em>authorization</em></div><div class="node auth"><i></i><b>Treasury controller approval</b><em>authorization</em></div><div class="node"><i></i><b>Account attestation + anomaly screen</b><em>evidence</em></div></div><div class="decisionLine"><b>Execute supplier wire</b><span>AUTHORIZED</span></div></article>
<div class="bridge"><b>→</b></div>
<article class="release"><div class="releaseHead"><div><span>Candidate</span><h3>Release 7.4.1</h3></div><span class="badge red">UNSUPPORTED</span></div><div class="graph"><div class="node"><i></i><b>Invoice + contract match</b><em>evidence</em></div><div class="node"><i></i><b>Vendor identity verified</b><em>evidence</em></div><div class="node rule"><i></i><b>Inside Q3 capital envelope</b><em>policy</em></div><div class="node removed"><i></i><b>Sanctions clearance</b><em>disconnected</em></div><div class="node removed"><i></i><b>Treasury controller approval</b><em>disconnected</em></div><div class="node"><i></i><b>Account attestation + anomaly screen</b><em>evidence</em></div></div><div class="decisionLine"><b>Execute supplier wire</b><span>OUTPUT MATCH</span></div></article></div>
<div class="auditAction"><button class="primary" onclick="runExample()">Run release-integrity audit</button></div><div class="statusRail" id="statusRail"><div class="statusRailTop"><span id="phase" role="status">Initializing canonical comparison…</span><span class="mono" id="phasePct">0%</span></div><div class="progress"><i id="progress"></i></div></div>
</section>
<section class="section"><div id="result" class="result"><div class="resultTop"><div><div class="resultEyebrow">FAR release decision</div><h2 id="headline"></h2></div><div class="decisionBadge" id="releaseDecision">—</div></div><div class="resultBody"><div class="resultNarrative"><p id="summary"></p><p id="why"></p><div class="findings" id="structural"></div><div class="unknowns" id="unknowns"></div><details id="rules"><summary>Inspect additional FAR rule findings</summary><div id="ruleList"></div></details><div class="resultActions"><a id="downloadReport" download="far-verification-report.json">Download evidence report</a><a href="#" onclick="document.getElementById('rawWrap').open=true;return false">Inspect canonical artifact</a></div><details id="rawWrap"><summary>Canonical FAR artifact</summary><pre id="raw"></pre></details></div><aside class="resultSide"><div class="metric"><span>Status transition</span><b id="transition">—</b></div><div class="metric"><span>Structural regressions</span><b id="changeCount">—</b></div><div class="metric"><span>Trace completeness</span><b id="completeness">—</b></div><div class="metric"><span>Evidence fingerprint</span><b class="mono" id="fingerprint">—</b></div></aside></div></div></section>
<section class="section" id="upload"><div class="sectionHead"><div class="sectionLabel">Your system</div><div><h2>Bring the evidence your stack already produces.</h2><p class="sectionLead">FAR accepts common structured, document, and spreadsheet containers while preserving one hard boundary: the content must resolve to a valid FAR decision package. No silent inference. No pretending arbitrary prose is a trace.</p></div></div><div class="uploadShell"><div><p class="uploadCopy">Compare two releases, two policy states, or two executions. Mix formats between baseline and candidate. Document containers can carry embedded JSON, YAML, or TOML; tabular files use the documented FAR table layout.</p><div class="formatCloud"><span>JSON</span><span>JSONL</span><span>YAML</span><span>TOML</span><span>XML</span><span>CSV</span><span>XLSX</span><span>Markdown</span><span>TXT</span><span>DOCX</span><span>PDF</span></div></div><form id="form" class="uploadPanel"><div class="upload"><label class="file">Baseline evidence<input name="baseline" type="file" accept="__ACCEPT__" required></label><label class="file">Candidate evidence<input name="candidate" type="file" accept="__ACCEPT__" required></label></div><p class="support">Maximum 10 MB per file. Uploaded containers are parsed in memory and must validate as FAR decision packages.</p><button class="primary" type="submit">Analyze supplied evidence</button><p id="error" class="error"></p></form></div></section>
<footer><span>FAR evaluates supplied packages and recorded dependencies only.</span><span>It does not infer hidden reasoning, external truth, safety, or regulatory compliance.</span></footer>
</main>
<script>
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
let reportUrl=null;
let analysisEpoch=0;
function updateReportDownload(artifact){const next=URL.createObjectURL(new Blob([JSON.stringify(artifact,null,2)+'\n'],{type:'application/json'}));document.getElementById('downloadReport').href=next;if(reportUrl)URL.revokeObjectURL(reportUrl);reportUrl=next;}
function render(d){updateReportDownload(d.artifact);document.getElementById('headline').textContent=d.headline;document.getElementById('releaseDecision').textContent=d.release_decision;document.getElementById('summary').textContent=d.plain_summary;document.getElementById('why').textContent=d.why_it_matters;document.getElementById('transition').textContent=d.status_transition.join(' → ');document.getElementById('changeCount').textContent=d.structural_changes.length;document.getElementById('completeness').textContent=Math.round(d.trace_completeness*100)+'%';document.getElementById('fingerprint').textContent=d.artifact.sha256.slice(0,12)+'…';document.getElementById('structural').innerHTML=d.structural_changes.map(x=>'<div class="finding"><b>'+esc(x.title)+'</b><span>'+esc(x.description)+'</span></div>').join('');document.getElementById('unknowns').innerHTML=d.unknowns.length?'<b>Declared unknowns</b><br>'+d.unknowns.map(esc).join('<br>'):'';document.getElementById('unknowns').style.display=d.unknowns.length?'block':'none';document.getElementById('ruleList').innerHTML=d.rule_findings.map(x=>'<p><b>'+esc(x.title)+':</b> '+esc(x.description)+'</p>').join('');document.getElementById('rules').style.display=d.rule_findings.length?'block':'none';document.getElementById('raw').textContent=JSON.stringify(d.artifact,null,2);document.getElementById('result').classList.add('show');document.getElementById('result').scrollIntoView({behavior:'smooth',block:'start'});}
function setExampleProgress(message, progress) {
  document.getElementById('phase').textContent=message;
  document.getElementById('phasePct').textContent=progress;
  document.getElementById('progress').style.width=progress;
}
async function runAnalysis(form) {
  const epoch=++analysisEpoch;
  const error=document.getElementById('error');
  error.textContent='';
  document.getElementById('statusRail').classList.toggle('show',!form);
  if (!form) setExampleProgress('Running canonical comparison…','0%');
  try {
    const response=form
      ? await fetch('/api/analyze',{method:'POST',body:new FormData(form)})
      : await fetch('/api/example');
    const result=await response.json();
    if (epoch!==analysisEpoch) return;
    if (!response.ok) throw new Error(result.detail||'Analysis failed');
    render(result);
    if (!form) setExampleProgress('Canonical comparison complete.','100%');
  } catch (err) {
    if (epoch!==analysisEpoch) return;
    if (form) error.textContent=err.message;
    else setExampleProgress(err.message,'0%');
  }
}
function runExample() { return runAnalysis(); }
document.getElementById('form').addEventListener('submit',event=>{
  event.preventDefault();
  return runAnalysis(event.target);
});
</script>
</body></html>'''
