#!/usr/bin/env python3
"""Validate FAR-CORE v1.1 formalization alignment and generate its inventory/views."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import jsonschema  # noqa: E402

LEDGER_PATH = "theory/evaluation/far-core-formalization-ledger-v1.0.json"
STATEMENT_LOCK_PATH = "tools/far_core_v11_statement_lock.json"
ASSURANCE_PATH = "theory/evaluation/far-core-assurance-v1.0.json"
CORE_PATH = "theory/terminal/project-far-core-theory-v1.1.json"
INVENTORY_PATH = "artifacts/mechanization/lean-inventory-v1.0.json"
REPORT_PATH = "docs/mechanization/far-core-v1.1-formalization.md"
INVENTORY_SCHEMA = "schemas/far-lean-inventory-v1.schema.json"
W2_MODULES = {
    "mechanization/lean/FARCoreV11Substrate.lean",
    "mechanization/lean/FARCoreV11Claims001To012.lean",
    "mechanization/lean/FARCoreV11Omega.lean",
    "mechanization/lean/FARCoreV11SSS.lean",
    "mechanization/lean/FARCoreV11Mutations.lean",
    "mechanization/lean/FARCoreV11AxiomAudit.lean",
}
EXPECTED_KERNEL_AXIOMS = {
    "FAR-CORE-001": ["Classical.choice"],
    "FAR-CORE-002": ["Classical.choice", "Quot.sound"],
    "FAR-CORE-003": ["Quot.sound"],
    "FAR-CORE-004": ["Classical.choice", "Quot.sound"],
    "FAR-CORE-005": ["none"],
    "FAR-CORE-006": ["Classical.choice", "Quot.sound", "propext"],
    "FAR-CORE-007": ["none"],
    "FAR-CORE-008": ["Quot.sound"],
    "FAR-CORE-009": ["none"],
    "FAR-CORE-010": ["Quot.sound", "propext"],
    "FAR-CORE-011": ["none"],
    "FAR-CORE-012": ["none"],
    "FAR-CORE-013": ["none"],
    "FAR-CORE-014": ["Quot.sound", "propext"],
}
EXPECTED_DECLARATION_AXIOMS = {
    "FARCoreV11.exact_factorization_criterion": frozenset({"Classical.choice"}),
    "FARCoreV11.collision_refutes_sufficiency": frozenset(),
    "FARCoreV11.quotient_is_sufficient": frozenset(),
    "FARCoreV11.observational_quotient_universal": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.factorToQuotient_surjective": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.leastInformativeImageEquiv": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.leastInformativeSufficient_iff_kernelEqual": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.quotient_is_least_informative_sufficient": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.action_preserves_observational_equivalence": frozenset(),
    "FARCoreV11.descendAction": frozenset({"Quot.sound"}),
    "FARCoreV11.no_contract_free_simultaneous_minimum": frozenset(),
    "FARCoreV11.no_simultaneous_least_informative_sufficient": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.identity_is_universally_sufficient": frozenset(),
    "FARCoreV11.invariants_antitone": frozenset(),
    "FARCoreV11.embeddingRangeEquiv": frozenset({"Classical.choice"}),
    "FARCoreV11.transport_operation_commutes": frozenset({"Classical.choice", "Quot.sound"}),
    "FARCoreV11.transport_relation_commutes": frozenset({"Classical.choice", "Quot.sound", "propext"}),
    "FARCoreV11.reification_recovers_relation": frozenset(),
    "FARCoreV11.primitive_vocabulary_count_noninvariant": frozenset(),
    "FARCoreV11.combine_split_operator_family": frozenset({"Quot.sound"}),
    "FARCoreV11.split_combine_operator": frozenset({"Quot.sound"}),
    "FARCoreV11.finite_operator_count_noninvariant": frozenset({"Quot.sound"}),
    "FARCoreV11.finite_panel_two_completions": frozenset(),
    "FARCoreV11.commonTheory_frame_independent": frozenset(),
    "FARCoreV11.commonTheory_invariant_under_truth_equivalence": frozenset({"Quot.sound", "propext"}),
    "FARCoreV11.residue_can_change_with_frame": frozenset(),
    "FARCoreV11.omitted_parameter_refutes_sufficiency": frozenset(),
    "FARCoreV11.absent_unknown_must_separate": frozenset(),
    "FARCoreV11.Omega.omega_elimination": frozenset(),
    "FARCoreV11.Omega.resolve_is_composition": frozenset(),
    "FARCoreV11.SSS.four_monotone_decoders": frozenset({"propext"}),
    "FARCoreV11.SSS.projected_successor_decoder_failure": frozenset({"propext"}),
    "FARCoreV11.SSS.hyperedge_factorization": frozenset({"propext"}),
    "FARCoreV11.SSS.frontier_factorization": frozenset({"propext"}),
    "FARCoreV11.SSS.MLL.derivable_atom_balance": frozenset({"Quot.sound", "propext"}),
    "FARCoreV11.SSS.MLL.sOr_witness_certified": frozenset({"Quot.sound", "propext"}),
    "FARCoreV11.SSS.MLL.sAnd_witness_certified": frozenset({"Quot.sound", "propext"}),
    "FARCoreV11.SSS.MLL.bounded_projected_decoder_failure": frozenset({"Quot.sound", "propext"}),
    "FARCoreV11.SSS.MLL.summaries_match_mll_witnesses": frozenset({"Quot.sound", "propext"}),
    "FARCoreV11.SSS.MLL.mll_projected_decoder_failure": frozenset({"Quot.sound", "propext"}),
}
# Placeholders and trust escapes are forbidden anywhere in code. Declarations may carry attributes
# and modifiers; `sorryAx` is what `sorry` elaborates to and compiles with only a warning.
FORBIDDEN = re.compile(
    r"(?m)(?<![A-Za-z0-9_'])(?:sorry|sorryAx|admit|native_decide)(?![A-Za-z0-9_'])"
    r"|^\s*(?:@\[[^\]]*\]\s*)*(?:(?:private|protected|noncomputable|partial|nonrec)\s+)*(?:axiom|constant|unsafe)\b"
    r"|@\[\s*(?:implemented_by|extern)\b"
)
IDENTIFIER_CHAR = re.compile(r"[A-Za-z0-9_'!?\u0080-\uffff]")
CHAR_LITERAL = re.compile(r"'(?:\\(?:x[0-9A-Fa-f]{2}|u\{[0-9A-Fa-f]+\}|[^\n])|[^'\\\n])'")
RAW_STRING_OPEN = re.compile(r'r(#*)"')


def lean_code(text: str) -> str:
    """Blank Lean comments (line and nested block), string, raw-string, and character literals.

    A placeholder mentioned in prose or data is then not counted, while one anywhere in code is.
    Newlines are kept. The text inside an interpolated string (`s!"..."`) is kept, because its
    `{...}` parts are code. An unterminated comment or literal is left as code, so a scanner
    mismatch can only over-report.
    """
    out = list(text)
    n = len(text)

    def blank(start: int, end: int) -> None:
        for k in range(start, end):
            if out[k] != "\n":
                out[k] = " "

    i = 0
    while i < n:
        after_code = i == 0 or not IDENTIFIER_CHAR.match(text[i - 1])
        if text.startswith("--", i):
            end = text.find("\n", i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
        elif text.startswith("/-", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/-", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("-/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            if depth:
                i += 2
                continue
            blank(i, j)
            i = j
        elif text[i] == "r" and after_code and RAW_STRING_OPEN.match(text, i):
            opener = RAW_STRING_OPEN.match(text, i)
            close = text.find('"' + opener.group(1), opener.end())
            if close < 0:
                i += 1
                continue
            blank(opener.end(), close)
            i = close + 1 + len(opener.group(1))
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                i += 1
                continue
            if not (i > 0 and text[i - 1] == "!"):
                blank(i + 1, j)
            i = j + 1
        elif text[i] == "'" and after_code and CHAR_LITERAL.match(text, i):
            end = CHAR_LITERAL.match(text, i).end()
            blank(i + 1, end - 1)
            i = end
        else:
            i += 1
    return "".join(out)


DECLARATION = re.compile(
    r"(?m)^\s*(?:(?:noncomputable|protected)\s+)?"
    r"(?:def|theorem|structure|inductive|abbrev)\s+([A-Za-z_][A-Za-z0-9_']*)"
)
AXIOM_DEPENDS = re.compile(r"^'([^']+)' depends on axioms: \[([^\]]*)\]$")
AXIOM_NONE = re.compile(r"^'([^']+)' does not depend on any axioms$")


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declared(text: str, qualified: str) -> bool:
    terminal = qualified.rsplit(".", 1)[-1]
    return bool(re.search(
        rf"(?m)^\s*(?:(?:noncomputable|protected)\s+)?"
        rf"(?:def|theorem|structure|inductive|abbrev)\s+{re.escape(terminal)}\b",
        text,
    ))


def render_axiom_audit() -> str:
    lines = [
        "import FARCoreV11Claims001To012",
        "import FARCoreV11Omega",
        "import FARCoreV11SSS",
        "",
    ]
    lines.extend(f"#print axioms {declaration}" for declaration in sorted(EXPECTED_DECLARATION_AXIOMS))
    return "\n".join(lines) + "\n"


def axiom_audit_source_errors(text: str) -> list[str]:
    if text != render_axiom_audit():
        return ["kernel-assumption audit source is not the deterministic generated command set"]
    return []


def parse_axiom_output(text: str) -> tuple[dict[str, frozenset[str]], list[str]]:
    observed: dict[str, frozenset[str]] = {}
    errors: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        match = AXIOM_DEPENDS.fullmatch(line)
        if match:
            declaration = match.group(1)
            axioms = frozenset(value.strip() for value in match.group(2).split(",") if value.strip())
        else:
            match = AXIOM_NONE.fullmatch(line)
            if not match:
                continue
            declaration = match.group(1)
            axioms = frozenset()
        if declaration in observed:
            errors.append(f"duplicate #print axioms output for {declaration}")
        observed[declaration] = axioms
    return observed, errors


def axiom_contract_errors(ledger: dict) -> list[str]:
    errors: list[str] = []
    declarations = [declaration for claim in ledger["claims"] for declaration in claim["lean_declarations"]]
    if len(declarations) != len(set(declarations)):
        errors.append("formalization ledger repeats a Lean declaration")
    expected = set(EXPECTED_DECLARATION_AXIOMS)
    actual = set(declarations)
    if actual != expected:
        errors.append(
            f"declaration-level axiom contract coverage drift: missing={sorted(expected-actual)} "
            f"unexpected={sorted(actual-expected)}"
        )
    for claim in ledger["claims"]:
        mapped = [EXPECTED_DECLARATION_AXIOMS[name] for name in claim["lean_declarations"] if name in EXPECTED_DECLARATION_AXIOMS]
        union = frozenset().union(*mapped) if mapped else frozenset()
        recorded = frozenset() if claim["kernel_axioms"] == ["none"] else frozenset(claim["kernel_axioms"])
        if union != recorded:
            errors.append(
                f"{claim['id']}: declaration-level axiom union {sorted(union)} "
                f"does not equal ledger {sorted(recorded)}"
            )
    return sorted(set(errors))


def axiom_output_errors(text: str, ledger: dict) -> list[str]:
    observed, errors = parse_axiom_output(text)
    errors.extend(axiom_contract_errors(ledger))
    expected = set(EXPECTED_DECLARATION_AXIOMS)
    actual = set(observed)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        errors.append(f"runtime #print axioms coverage drift: missing={missing} unexpected={unexpected}")
    for declaration in sorted(expected & actual):
        if observed[declaration] != EXPECTED_DECLARATION_AXIOMS[declaration]:
            errors.append(
                f"{declaration}: actual axiom set {sorted(observed[declaration])} "
                f"does not equal expected {sorted(EXPECTED_DECLARATION_AXIOMS[declaration])}"
            )
    return sorted(set(errors))



def statement_header(text: str, qualified: str) -> str | None:
    """Lock the complete Lean declaration header without copying its proof/body.

    The type of a theorem may contain dependent `let` assignments (`:=`);
    the first assignment is therefore NOT necessarily the declaration body.
    `where`-defined values also have field assignments after the type.
    This is lexical source regression assurance, not elaborated type equivalence.
    """
    terminal = qualified.rsplit(".", 1)[-1]
    code = lean_code(text)
    pattern = re.compile(
        rf"(?m)^[ \t]*(?:(?:noncomputable|protected)\s+)?"
        rf"(?P<kind>def|theorem|abbrev)\s+{re.escape(terminal)}(?=\s|$)"
    )
    matches = list(pattern.finditer(code))
    if len(matches) != 1:
        return None
    match = matches[0]
    remainder = code[match.start():]
    next_declaration = DECLARATION.search(remainder, match.end() - match.start())
    block = remainder[:next_declaration.start()] if next_declaration else remainder

    # Lean permits `def f : T where ...` instead of `:= ...`.
    where_match = re.search(r"\bwhere[ \t]*(?:\n|$)", block)
    if where_match:
        end = where_match.start()
    elif match.group("kind") == "theorem":
        # A mapped theorem is required to have an explicit `:= by` body.
        # This skips `let x := ...` inside the *type* rather than truncating it.
        body_match = re.search(r":=[ \t]*by\b", block)
        if body_match is None:
            return None
        end = body_match.start()
    else:
        body_match = re.search(r":=", block)
        if body_match is None:
            return None
        end = body_match.start()

    header = " ".join(block[:end].split())
    return header if header else None


def statement_lock_errors(
    ledger: dict, lock: dict, source_overrides: dict[str, str] | None = None
) -> list[str]:
    """Fail on drift of any of the 40 governed source-level declaration statements.

    Locks are reviewed commitments to the initial source signatures; they are NOT an
    independently justified Lean elaboration or full prose-to-formalization mapping.
    """
    expected = {
        declaration: claim["intended_lean_module"]
        for claim in ledger["claims"]
        for declaration in claim["lean_declarations"]
    }
    locked = lock.get("signatures")
    if not isinstance(locked, dict):
        return ["proposition lock is missing its signatures map"]
    errors = []
    if set(locked) != set(expected):
        errors.append(
            f"source proposition lock coverage drift: "
            f"missing={sorted(set(expected) - set(locked))} "
            f"unexpected={sorted(set(locked) - set(expected))}"
        )
    sources: dict[str, str] = {}
    for declaration, path in sorted(expected.items()):
        entry = locked.get(declaration)
        if not isinstance(entry, dict) or entry.get("module") != path:
            errors.append(f"{declaration}: proposition lock module mismatch or missing entry")
            continue
        if path not in sources:
            if source_overrides is not None and path in source_overrides:
                sources[path] = source_overrides[path]
            else:
                sources[path] = (ROOT / path).read_text(encoding="utf-8")
        observed = statement_header(sources[path], declaration)
        if observed is None:
            errors.append(f"{declaration}: absent, duplicated, or malformed proposition declaration")
        elif observed != entry.get("header"):
            errors.append(f"{declaration}: proposition signature drift from the reviewed source lock")
    return sorted(set(errors))


def inventory(ledger: dict) -> dict:
    files = []
    forbidden_count = 0
    for path in sorted((ROOT / "mechanization/lean").glob("*.lean")):
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        forbidden_count += len(FORBIDDEN.findall(lean_code(text)))
        files.append({
            "path": relative,
            "sha256": digest(path),
            "line_count": len(text.splitlines()),
            "imports": sorted(set(re.findall(r"(?m)^import\s+([^\s]+)\s*$", text))),
            "declarations": sorted(set(DECLARATION.findall(text))),
            "role": "W2_CORE_V1_1" if relative in W2_MODULES else "LEGACY_OR_OTHER_SCOPE",
        })
    statuses = [claim["formalization_status"] for claim in ledger["claims"]]
    checks = {claim["kernel_check"] for claim in ledger["claims"]}
    return {
        "schema_version": "1.0",
        "inventory_id": "PROJECT-FAR-LEAN-INVENTORY-1.0",
        "authority": "generated_inventory_not_theory_authority",
        "toolchain": ledger["lean_toolchain"],
        "files": files,
        "w2_summary": {
            "formalized": statuses.count("FORMALIZED"),
            "partial_obstruction": statuses.count("PARTIAL/OBSTRUCTION"),
            "contradiction_reopen_required": statuses.count("CONTRADICTION/REOPEN REQUIRED"),
            "kernel_check": checks.pop() if len(checks) == 1 else "MIXED",
            "forbidden_placeholders": forbidden_count,
        },
    }


def alignment_errors(ledger: dict, assurance: dict, core: dict, generated: dict) -> list[str]:
    errors: list[str] = axiom_contract_errors(ledger)
    errors.extend(statement_lock_errors(ledger, load(STATEMENT_LOCK_PATH)))
    expected_ids = [f"FAR-CORE-{index:03d}" for index in range(1, 15)]
    ledger_claims = ledger["claims"]
    assurance_by_id = {item["id"]: item for item in assurance["claims"]}
    core_by_id = {item["id"]: item for item in core["claims"]}
    axiom_audit = (ROOT / "mechanization/lean/FARCoreV11AxiomAudit.lean").read_text(encoding="utf-8")
    errors.extend(axiom_audit_source_errors(axiom_audit))
    if [item["id"] for item in ledger_claims] != expected_ids:
        errors.append("formalization ledger must cover FAR-CORE-001 through 014 in order")
    if set(assurance_by_id) != set(expected_ids) or set(core_by_id) != set(expected_ids):
        errors.append("core/assurance/formalization claim coverage differs")
    for item in ledger_claims:
        identifier = item["id"]
        if item["canonical_prose_statement"] != core_by_id[identifier]["claim"]:
            errors.append(f"{identifier}: canonical prose drift")
        module = ROOT / item["intended_lean_module"]
        if not module.is_file():
            errors.append(f"{identifier}: missing Lean module {item['intended_lean_module']}")
            continue
        text = module.read_text(encoding="utf-8")
        for declaration in item["lean_declarations"]:
            if not declared(text, declaration):
                errors.append(f"{identifier}: missing declaration {declaration}")
        if item["kernel_axioms"] != EXPECTED_KERNEL_AXIOMS[identifier]:
            errors.append(f"{identifier}: recorded kernel assumptions drifted")
        assurance_status = item["formalization_status"].replace("/", "_")
        if assurance_by_id[identifier]["formalization_status"] != assurance_status:
            errors.append(f"{identifier}: assurance/formalization status drift")
        if assurance_by_id[identifier]["lean_declarations"] != item["lean_declarations"]:
            errors.append(f"{identifier}: assurance/ledger Lean declaration drift")
        for source in item["source_locations"]:
            source_path = ROOT / source["path"]
            if not source_path.is_file() or digest(source_path) != source["sha256"]:
                errors.append(f"{identifier}: canonical source hash drift at {source['path']}")
        if item["formalization_status"] == "FORMALIZED" and item["obstruction"]["classification"] != "none":
            errors.append(f"{identifier}: formalized claim retains an obstruction")
    if [item["formalization_status"] for item in ledger_claims] != ["FORMALIZED"] * 14:
        errors.append("FAR-CORE-001 through 014 must be FORMALIZED after the governed MLL bridge compiles")
    last = ledger_claims[-1]
    if last["obstruction"]["classification"] != "none":
        errors.append("FAR-CORE-014 formalized status retains a classified obstruction")
    if core_by_id["FAR-CORE-014"]["status"] != "supported_derived":
        errors.append("FAR-CORE-014 historical/application provenance status was overwritten")
    if assurance_by_id["FAR-CORE-014"]["truth_disposition"] != "PROVED":
        errors.append("FAR-CORE-014 truth disposition was conflated with provenance")
    if generated["w2_summary"] != {
        "formalized": 14,
        "partial_obstruction": 0,
        "contradiction_reopen_required": 0,
        "kernel_check": "PASS",
        "forbidden_placeholders": 0,
    }:
        errors.append(f"unexpected W2 inventory summary: {generated['w2_summary']}")
    mutations = (ROOT / "mechanization/lean/FARCoreV11Mutations.lean").read_text(encoding="utf-8")
    for item in ledger_claims:
        for control in item["mutation_negative_controls"]:
            if control.startswith("FARCoreV11Mutations.") and not declared(mutations, control):
                errors.append(f"{item['id']}: missing mutation control {control}")
    return sorted(set(errors))


def render_report(ledger: dict, generated: dict) -> str:
    rows = []
    for claim in ledger["claims"]:
        declarations = "<br>".join(f"`{value}`" for value in claim["lean_declarations"])
        axioms = "<br>".join(f"`{value}`" for value in claim["kernel_axioms"])
        obstruction = "—" if claim["obstruction"]["classification"] == "none" else claim["obstruction"]["details"]
        rows.append(
            f"| `{claim['id']}` | `{claim['formalization_status']}` | `{claim['kernel_check']}` | "
            f"{axioms} | {declarations} | {obstruction} |"
        )
    w2_files = [item for item in generated["files"] if item["role"] == "W2_CORE_V1_1"]
    file_rows = [
        f"| `{item['path']}` | `{item['sha256']}` | {item['line_count']} | "
        f"{', '.join(f'`{value}`' for value in item['imports']) or 'none'} |"
        for item in w2_files
    ]
    return """# FAR-CORE v1.1 proof-assistant formalization

Status: **Generated W2 assurance view; not governing theory authority**

Sources: [`theory/evaluation/far-core-formalization-ledger-v1.0.json`](../../theory/evaluation/far-core-formalization-ledger-v1.0.json)
and [`artifacts/mechanization/lean-inventory-v1.0.json`](../../artifacts/mechanization/lean-inventory-v1.0.json).
Edit the machine ledger or Lean sources and regenerate this view.

Lean proves machine-checked derivations relative to the encoded premises. It does not establish
novelty, empirical validity, or universal architecture. The W1 truth verdicts, historical
provenance labels, and proof-assistant status remain separate dimensions.

The W2 workflow captures every `#print axioms` result and rejects missing declarations,
unexpected transitive assumptions, or any mismatch with the declaration-level and claim-level
assumption contracts. Merely printing the audit is not accepted as assurance.

## Outcome matrix

| Claim | W2 outcome | Kernel | Kernel assumptions | Declarations | Obstruction |
|---|---|---|---|---|---|
""" + "\n".join(rows) + """

## FAR-CORE-014 bounded application bridge

The governed MLL syntax, cut-free unit-free derivability rules, atom-balance invariant, both named
witness sequents, their mixed projected-successor truth profiles, and the uniform-decoder failure
are now kernel-checked in `FARCoreV11SSS.lean`. The positive hyperedge and frontier statements
remain explicitly conditional on their stated rule-characterization/recursion premises. This
formalization does not enlarge FAR-CORE-014 into a universal architecture claim.

## W2 module inventory

| File | SHA-256 | Lines | Imports |
|---|---|---:|---|
""" + "\n".join(file_rows) + """

The inventory also records every pre-existing Lean file as `LEGACY_OR_OTHER_SCOPE`. Those files
were searched and retained; they do not silently count as coverage of FAR-CORE-001--014.
"""


def expected() -> tuple[dict, str, list[str]]:
    ledger = load(LEDGER_PATH)
    assurance = load(ASSURANCE_PATH)
    core = load(CORE_PATH)
    for exc in jsonschema.Draft202012Validator(load("schemas/far-core-formalization-ledger-v1.schema.json")).iter_errors(ledger):
        raise ValueError(f"formalization ledger schema: {exc.message}")
    generated = inventory(ledger)
    for exc in jsonschema.Draft202012Validator(load(INVENTORY_SCHEMA)).iter_errors(generated):
        raise ValueError(f"Lean inventory schema: {exc.message}")
    return generated, render_report(ledger, generated), alignment_errors(ledger, assurance, core, generated)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--axiom-output", type=Path)
    parser.add_argument("--emit-axiom-audit", type=Path)
    args = parser.parse_args(argv)
    try:
        generated, report, errors = expected()
        if args.axiom_output:
            errors += axiom_output_errors(args.axiom_output.read_text(encoding="utf-8"), load(LEDGER_PATH))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    if errors:
        print("FAIL: " + "; ".join(errors))
        return 1
    if args.emit_axiom_audit:
        args.emit_axiom_audit.parent.mkdir(parents=True, exist_ok=True)
        args.emit_axiom_audit.write_text(render_axiom_audit(), encoding="utf-8")
    outputs = {
        INVENTORY_PATH: json.dumps(generated, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        REPORT_PATH: report,
    }
    if args.write:
        for path, content in outputs.items():
            target = ROOT / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        print("wrote FAR-CORE v1.1 Lean inventory and report")
        return 0
    stale = [path for path, content in outputs.items()
             if not (ROOT / path).is_file() or (ROOT / path).read_text(encoding="utf-8") != content]
    if stale:
        print("FAIL: stale generated formalization outputs: " + ", ".join(stale))
        return 1
    print("FAR-CORE v1.1 formalization alignment: PASS (14 FORMALIZED, 0 PARTIAL/OBSTRUCTION)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
