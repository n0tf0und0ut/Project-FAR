"""Bounded inspection report; neither generated prose nor markdown is an authority."""
from __future__ import annotations
import json
import html
import re


def _plain(value: object) -> str:
    """Escape untrusted HTML and Markdown without interpreting its contents."""
    escaped = html.escape(str(value), quote=False).replace(chr(13), " ").replace(chr(10), " ")
    for symbol in (chr(92), chr(96), "*", "_", "[", "]", "(", ")", "!", "#", ">", "|", "~"):
        escaped = escaped.replace(symbol, chr(92) + symbol)
    return escaped

from engine import canonical, digest


def render_markdown(bundle: dict, audit: dict, *, acquisition: list[dict],
                    discovery: dict | None = None, questions: list[dict] | None = None) -> str:
    assert audit["input_sha256"] == digest(canonical(bundle))
    claims = {x["id"]: x for x in bundle["claims"]}
    sources = {x["id"]: x for x in bundle["sources"]}
    lines = ["# FAR Investigation: " + bundle["investigation_id"], "",
             "> Research/prototype output; not certified factual truth. Semantic mappings are not independently verified.", "",
             "## Scope and input", "",
             f"- As-of/capture time: `{bundle['as_of']}`",
             f"- Input SHA-256: `{audit['input_sha256']}`",
             f"- Report SHA-256: `{audit['report_sha256']}`",
             f"- Source snapshots: {len(sources)}; claim candidates: {len(claims)}; candidate readings: {len(bundle['interpretations'])}",
             "- Retrieval completeness and external source authenticity: **not established**", "",
             "## Attributed claims", ""]
    for cid, claim in claims.items():
        state = audit["claims"][cid]
        quote = claim["span"]["quote"]
        # A fence longer than every embedded run of backticks preserves the
        # exact untrusted quotation without allowing it to terminate its code
        # block or activate HTML/Markdown markup.
        fence = "`" * max(3, 1 + max((len(m.group()) for m in re.finditer(r"`+", quote)), default=0))
        lines += [f"### {cid}", "", f"Source: `{claim['source_id']}`; exact span: "
                  f"`{claim['span']['start']}:{claim['span']['end']}`", "",
                  "Source quotation:", "", fence + "text", quote, fence, "",
                  f"- Evidential/conditional status: **{state['status']}**",
                  f"- Numerical status: **{state['structured_value_checks']['status']}**",
                  f"- Semantic mapping: **{state['mapping_status']}** (not independent validation)",
                  f"- Evidence relations tested: {len(state['evidence'])}", ""]
        for ev in state["evidence"]:
            extra = ev.get("structured_check", {}).get("status")
            lines.append(f"  - Evidence `{ev['evidence_id']}`: {ev['formal_relation']}" + (f" / {extra}" if extra else ""))
        lines.append("")
    lines += ["## Proposed arguments and formal countermodels", ""]
    if not audit["interpretations"]:
        lines += ["No explicit argument was identified. No inference verdict was issued.", ""]
    for r in audit["interpretations"]:
        p = r["formal_inference"]
        lines += [f"### {r['id']}", "", f"- Premises: {', '.join(r['premises'])}; conclusion: {r['conclusion']}",
                  f"- Formal result: **{p['status']}**", "- Natural-language fidelity: **unverified**"]
        if r.get("interpretation_notes"):
            lines.append("- Interpretation: " + _plain(r["interpretation_notes"]))
        if r.get("interpretation_card"):
            for dimension, spec in sorted(r["interpretation_card"].items()):
                lines.append(f"- {dimension}: {_plain(spec['value'])} ({spec['origin']}, unverified)")
        if p.get("countermodel") is not None:
            lines.append("- Formal countermodel: `" + json.dumps(p["countermodel"], sort_keys=True) + "`")
        if r["premises_without_uncontested_formal_evidence"]:
            lines.append("- Unestablished premises: " + ", ".join(r["premises_without_uncontested_formal_evidence"]))
        lines.append("")
    if audit.get("interpretation_cards_differ"):
        lines += ["Candidate interpretation cards differ; no semantic-effect inference is made from card differences alone.", ""]
    lines += ["## Acquisition history", ""]
    for entry in acquisition:
        label = entry.get("url") or entry.get("label") or entry.get("source_id", "unknown")
        lines.append(f"- {_plain(entry.get('source_id', 'unknown'))}: {_plain(label)}; "
                     f"method={_plain(entry.get('extraction', 'provided'))}; "
                     f"raw SHA-256={_plain(entry.get('raw_sha256', '?'))}; authenticity=unverified")
    lines.append("")
    if discovery:
        lines += ["## Discovery (leads only)", "", f"- Searches: {len(discovery.get('queries', []))}; leads: {len(discovery.get('results', []))}",
                  "- Returned URLs and snippets have no authenticated content/evidence status.", ""]
    if questions:
        lines += ["## Argument-scheme critical questions (unadjudicated)", "",
                  "These are hypothesis/checklist triggers, NOT findings that an argument is invalid.", ""]
        for question in questions:
            lines += [f"- {_plain(question['claim_id'])} / {_plain(question['scheme'])}: "
                      f"{_plain(question['critical_question'])}"]
        lines.append("")
    lines += ["## Unknowns and blockers", ""]
    lines.extend("- " + _plain(x) for x in audit["unknowns"])
    lines += ["", "## Assurance boundaries", ""]
    lines.extend("- " + k.replace("_", " ") + ": " + v for k,v in audit["assurance_boundary"].items())
    return "\n".join(lines) + "\n"
