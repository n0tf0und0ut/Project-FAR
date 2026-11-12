#!/usr/bin/env python3
"""Fail closed on unsupported investigation PASS declarations."""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXECUTIONS = ROOT / "research/validation/executions"
PASS_RESULTS = {"pass", "passed"}
COMPLETE_STATES = {"complete", "completed"}
CLOSURE_CONTRACT = "FAR-EVIDENCE-CLOSURE-1.0"
PRE_CORRECTION_EXECUTION_BLOBS = {
    "VI-001": "8da94d4caa38170303b319769d36b0c4ced731e0",
    "VI-002": "7d047ecf57f6a76e7314f526839d0f72cab523f7",
}
CLOSURE_TRUE_FIELDS = (
    "claim_disposition_separate",
    "decisive_evidence_scope_recorded",
    "denominator_directness_checked",
    "measurement_classification_checked",
    "strongest_support_recorded",
    "strongest_counterevidence_recorded",
    "alternative_explanations_checked",
    "surviving_propositions_recorded",
    "residual_uncertainty_recorded",
)
CLOSURE_RECORDED_LISTS = (
    "measurement_limitations",
    "strongest_support",
    "strongest_counterevidence",
    "alternative_explanations",
    "surviving_propositions",
    "residual_uncertainty",
)
TERMINAL_ZERO_NEW_FIELDS = (
    "new_material_evidence",
    "new_claim_decomposition",
    "new_alternative_explanation",
    "new_residual_uncertainty",
)


def normalized_result(value: object) -> str:
    """Compare results case- and whitespace-insensitively, so `PASS ` cannot evade the PASS gate."""
    return str(value).strip().casefold()


def execution_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "research/validation/executions").glob("*.execution.yaml"))


def load_manifest_results(root: Path = ROOT) -> dict[str, str]:
    """Load canonical results without allowing later duplicate files to shadow earlier ones."""
    results: dict[str, str] = {}
    for path in execution_paths(root):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        investigation = str(data.get("investigation", "")).strip()
        if investigation and investigation not in results:
            results[investigation] = normalized_result(data.get("result", ""))
    return results


def validate_manifest_registry(root: Path = ROOT) -> list[str]:
    """Require a one-to-one mapping between investigation IDs and canonical filenames."""
    errors: list[str] = []
    seen: dict[str, Path] = {}
    for path in execution_paths(root):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        investigation = str(data.get("investigation", "")).strip()
        expected = path.name.removesuffix(".execution.yaml")
        if not investigation:
            errors.append(f"{path.name}: missing investigation ID")
            continue
        if investigation != expected:
            errors.append(
                f"{path.name}: investigation ID {investigation} does not match canonical filename {expected}"
            )
        previous = seen.get(investigation)
        if previous is not None:
            errors.append(
                f"{investigation}: duplicate execution manifests {previous.name} and {path.name}"
            )
        else:
            seen[investigation] = path
    return errors


def resolve_repository_artifact(root: Path, declared_path: object) -> tuple[Path | None, str | None]:
    """Resolve an evidence path and reject absolute or repository-escaping locations."""
    if not isinstance(declared_path, str) or not declared_path.strip():
        return None, "<missing-path>"
    relative = Path(declared_path)
    if relative.is_absolute():
        return None, declared_path
    root_resolved = root.resolve()
    artifact = (root_resolved / relative).resolve()
    try:
        artifact.relative_to(root_resolved)
    except ValueError:
        return None, declared_path
    return artifact, None


def _git_blob_oid(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _is_pinned_pre_correction_manifest(path: Path, investigation: str) -> bool:
    expected_blob = PRE_CORRECTION_EXECUTION_BLOBS.get(investigation)
    if expected_blob is None:
        return False
    if path.name != f"{investigation}.execution.yaml" or not path.is_file():
        return False
    return _git_blob_oid(path) == expected_blob


def _validate_evidence_entries(
    *,
    investigation: str,
    label: str,
    evidence: object,
    root: Path,
    errors: list[str],
    require_nonempty: bool = True,
) -> None:
    if not isinstance(evidence, list):
        errors.append(f"{investigation}: {label} evidence must be a list")
        return
    if require_nonempty and not evidence:
        errors.append(f"{investigation}: {label} requires evidence")
        return
    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            errors.append(f"{investigation}: {label} evidence entry {index} must be a mapping")
            continue
        declared_path = item.get("path")
        artifact, invalid_path = resolve_repository_artifact(root, declared_path)
        if invalid_path is not None:
            errors.append(
                f"{investigation}: evidence artifact must remain within repository root: {invalid_path}"
            )
        elif artifact is not None and not artifact.is_file():
            errors.append(f"{investigation}: missing evidence artifact {declared_path}")


def _validate_string_list(
    *, investigation: str, label: str, value: object, errors: list[str]
) -> None:
    if not isinstance(value, list):
        errors.append(f"{investigation}: {label} must be a list")
        return
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{investigation}: {label}[{index}] must be a non-empty string")


def _validate_recorded_list(
    *,
    closure: dict,
    field: str,
    investigation: str,
    root: Path,
    errors: list[str],
) -> None:
    """Require substantive typed records, not list cardinality or placeholder values."""
    value = closure.get(field)
    if not isinstance(value, list):
        errors.append(f"{investigation}: evidence_closure.{field} must be a list")
        return
    if not value:
        basis = closure.get(f"{field}_basis")
        if not isinstance(basis, str) or not basis.strip():
            errors.append(
                f"{investigation}: empty evidence_closure.{field} requires {field}_basis"
            )
        return

    seen_ids: set[str] = set()
    for index, record in enumerate(value, start=1):
        label = f"evidence_closure.{field}[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{investigation}: {label} must be a mapping")
            continue

        raw_id = record.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            errors.append(f"{investigation}: {label}.id must be a non-empty string")
        else:
            record_id = raw_id.strip()
            if record_id in seen_ids:
                errors.append(f"{investigation}: duplicate {field} record id: {record_id}")
            seen_ids.add(record_id)

        statement = record.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            errors.append(f"{investigation}: {label}.statement must be a non-empty string")

        basis = record.get("basis")
        evidence = record.get("evidence")
        has_basis = isinstance(basis, str) and bool(basis.strip())
        has_evidence = isinstance(evidence, list) and bool(evidence)
        if not has_basis and not has_evidence:
            errors.append(
                f"{investigation}: {label} requires a non-empty basis or evidence"
            )
        if evidence is not None:
            _validate_evidence_entries(
                investigation=investigation,
                label=label,
                evidence=evidence,
                root=root,
                errors=errors,
                require_nonempty=not has_basis,
            )


def _requires_evidence_closure(path: Path, investigation: str, result: str) -> bool:
    """Grandfather only exact Git objects that predate the closure correction."""
    return result in PASS_RESULTS and not _is_pinned_pre_correction_manifest(path, investigation)


def validate_evidence_closure(data: dict, root: Path, investigation: str) -> list[str]:
    """Validate machine-checkable FAR-EVIDENCE-CLOSURE-1.0 evidence for a PASS."""
    errors: list[str] = []
    closure = data.get("evidence_closure")
    if not isinstance(closure, dict):
        return [f"{investigation}: PASS requires evidence_closure contract {CLOSURE_CONTRACT}"]

    if closure.get("contract") != CLOSURE_CONTRACT:
        errors.append(
            f"{investigation}: evidence_closure contract must equal {CLOSURE_CONTRACT}"
        )

    _validate_evidence_entries(
        investigation=investigation,
        label="evidence closure",
        evidence=closure.get("evidence"),
        root=root,
        errors=errors,
    )

    search_frame = closure.get("search_frame")
    if not isinstance(search_frame, dict):
        errors.append(f"{investigation}: evidence_closure.search_frame must be a mapping")
    else:
        for field in ("evidence_cutoff", "stopping_rule"):
            value = search_frame.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"{investigation}: evidence_closure.search_frame.{field} must be a non-empty string"
                )
        for field in ("inclusion_rules", "exclusion_rules"):
            _validate_string_list(
                investigation=investigation,
                label=f"evidence_closure.search_frame.{field}",
                value=search_frame.get(field),
                errors=errors,
            )

    for field in CLOSURE_TRUE_FIELDS:
        if closure.get(field) is not True:
            errors.append(f"{investigation}: evidence_closure.{field} must be true")

    for field in CLOSURE_RECORDED_LISTS:
        _validate_recorded_list(
            closure=closure,
            field=field,
            investigation=investigation,
            root=root,
            errors=errors,
        )

    search_classes = closure.get("evidence_search_classes")
    executed_class_ids: set[str] = set()
    if not isinstance(search_classes, list) or not search_classes:
        errors.append(
            f"{investigation}: evidence_closure.evidence_search_classes must be a non-empty list"
        )
    else:
        seen_class_ids: set[str] = set()
        for index, search_class in enumerate(search_classes, start=1):
            label = f"evidence_closure.evidence_search_classes[{index}]"
            if not isinstance(search_class, dict):
                errors.append(f"{investigation}: {label} must be a mapping")
                continue
            raw_class_id = search_class.get("id")
            class_id: str | None = None
            if not isinstance(raw_class_id, str) or not raw_class_id.strip():
                errors.append(f"{investigation}: {label}.id must be a non-empty string")
            else:
                class_id = raw_class_id.strip()
                if class_id in seen_class_ids:
                    errors.append(
                        f"{investigation}: duplicate evidence/search class id: {class_id}"
                    )
                else:
                    seen_class_ids.add(class_id)

            state = str(search_class.get("status", "")).lower()
            if state == "executed":
                if class_id is not None and class_id in seen_class_ids:
                    executed_class_ids.add(class_id)
                _validate_evidence_entries(
                    investigation=investigation,
                    label=f"evidence/search class {class_id or '<invalid-id>'}",
                    evidence=search_class.get("evidence"),
                    root=root,
                    errors=errors,
                )
            elif state == "not_applicable":
                reason = search_class.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    errors.append(
                        f"{investigation}: evidence/search class {class_id or '<invalid-id>'} NOT_APPLICABLE requires a reason"
                    )
            else:
                errors.append(
                    f"{investigation}: evidence/search class {class_id or '<invalid-id>'} status must be executed or not_applicable"
                )

    terminal = closure.get("terminal_saturation")
    if not isinstance(terminal, dict):
        errors.append(f"{investigation}: evidence_closure.terminal_saturation must be a mapping")
    else:
        if terminal.get("completed") is not True:
            errors.append(
                f"{investigation}: evidence_closure.terminal_saturation.completed must be true"
            )
        for field in TERMINAL_ZERO_NEW_FIELDS:
            if terminal.get(field) is not False:
                errors.append(
                    f"{investigation}: evidence_closure.terminal_saturation.{field} must be false"
                )
        _validate_evidence_entries(
            investigation=investigation,
            label="terminal saturation",
            evidence=terminal.get("evidence"),
            root=root,
            errors=errors,
        )

        class_results = terminal.get("class_results")
        terminal_class_ids: set[str] = set()
        duplicate_terminal_ids: set[str] = set()
        if not isinstance(class_results, list):
            errors.append(
                f"{investigation}: evidence_closure.terminal_saturation.class_results must be a list"
            )
        else:
            for index, result in enumerate(class_results, start=1):
                label = f"evidence_closure.terminal_saturation.class_results[{index}]"
                if not isinstance(result, dict):
                    errors.append(f"{investigation}: {label} must be a mapping")
                    continue
                raw_class_id = result.get("class_id")
                if not isinstance(raw_class_id, str) or not raw_class_id.strip():
                    errors.append(f"{investigation}: {label}.class_id must be a non-empty string")
                    class_id = None
                else:
                    class_id = raw_class_id.strip()
                    if class_id in terminal_class_ids:
                        duplicate_terminal_ids.add(class_id)
                    terminal_class_ids.add(class_id)
                if result.get("rechecked") is not True:
                    errors.append(f"{investigation}: {label}.rechecked must be true")
                for field in TERMINAL_ZERO_NEW_FIELDS:
                    if result.get(field) is not False:
                        errors.append(f"{investigation}: {label}.{field} must be false")
                _validate_evidence_entries(
                    investigation=investigation,
                    label=label,
                    evidence=result.get("evidence"),
                    root=root,
                    errors=errors,
                )

        for class_id in sorted(duplicate_terminal_ids):
            errors.append(
                f"{investigation}: duplicate terminal saturation class result: {class_id}"
            )
        missing_classes = sorted(executed_class_ids - terminal_class_ids)
        unexpected_classes = sorted(terminal_class_ids - executed_class_ids)
        if missing_classes:
            errors.append(
                f"{investigation}: terminal saturation missing executed classes: {', '.join(missing_classes)}"
            )
        if unexpected_classes:
            errors.append(
                f"{investigation}: terminal saturation contains non-executed classes: {', '.join(unexpected_classes)}"
            )

    methodology_audit = closure.get("methodology_audit")
    if not isinstance(methodology_audit, dict):
        errors.append(f"{investigation}: evidence_closure.methodology_audit must be a mapping")
    else:
        if methodology_audit.get("completed") is not True:
            errors.append(
                f"{investigation}: evidence_closure.methodology_audit.completed must be true"
            )
        _validate_evidence_entries(
            investigation=investigation,
            label="methodology audit",
            evidence=methodology_audit.get("evidence"),
            root=root,
            errors=errors,
        )

    return errors


def validate_manifest(
    path: Path,
    root: Path = ROOT,
    manifest_results: dict[str, str] | None = None,
) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    investigation = str(data.get("investigation", path.stem)).strip()
    raw_result = data.get("result", "")
    result = normalized_result(raw_result)
    required = data.get("required_steps")
    upstream = data.get("upstream_dependencies", [])
    if not isinstance(raw_result, str):
        errors.append(f"{investigation}: result must be a string, got {type(raw_result).__name__}")

    if required is None:
        required_steps: list[dict] = []
    elif isinstance(required, list):
        required_steps = required
    else:
        errors.append(f"{investigation}: required_steps must be a list")
        required_steps = []

    seen_step_ids: set[str] = set()
    for step in required_steps:
        if not isinstance(step, dict):
            errors.append(f"{investigation}: required step must be a mapping")
            continue
        raw_step_id = step.get("id")
        if not isinstance(raw_step_id, str) or not raw_step_id.strip():
            errors.append(f"{investigation}: required step has missing, empty, or non-string id")
        else:
            step_id = raw_step_id.strip()
            if step_id in seen_step_ids:
                errors.append(f"{investigation}: duplicate required step id: {step_id}")
            else:
                seen_step_ids.add(step_id)
        state = str(step.get("status", "")).lower()
        evidence = step.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"{investigation}: step {step.get('id')} evidence must be a list")
            continue
        if state in COMPLETE_STATES and not evidence:
            errors.append(f"{investigation}: complete step {step.get('id')} has no evidence")
        _validate_evidence_entries(
            investigation=investigation,
            label=f"step {step.get('id')}",
            evidence=evidence,
            root=root,
            errors=errors,
            require_nonempty=False,
        )

    if result in PASS_RESULTS:
        if not isinstance(required, list) or not required_steps:
            errors.append(f"{investigation}: PASS requires a non-empty required_steps list")

        incomplete = [
            str(step.get("id"))
            for step in required_steps
            if isinstance(step, dict)
            and str(step.get("status", "")).lower() not in COMPLETE_STATES
        ]
        if incomplete:
            errors.append(f"{investigation}: PASS with incomplete required steps: {', '.join(incomplete)}")

        missing_evidence = [
            str(step.get("id"))
            for step in required_steps
            if isinstance(step, dict) and not step.get("evidence")
        ]
        if missing_evidence:
            errors.append(
                f"{investigation}: PASS with required steps lacking evidence: {', '.join(missing_evidence)}"
            )

        canonical_results = manifest_results if manifest_results is not None else load_manifest_results(root)
        unresolved: list[str] = []
        if not isinstance(upstream, list):
            errors.append(f"{investigation}: upstream_dependencies must be a list")
            upstream = []
        for dependency in upstream:
            if not isinstance(dependency, dict):
                unresolved.append("<invalid-dependency>")
                continue
            dependency_id = str(dependency.get("id", "")).strip()
            if not dependency_id:
                unresolved.append("<missing-id>")
                continue
            canonical_result = canonical_results.get(dependency_id)
            if canonical_result not in PASS_RESULTS:
                unresolved.append(dependency_id)
        if unresolved:
            errors.append(
                f"{investigation}: PASS with unresolved upstream dependencies: {', '.join(unresolved)}"
            )

        if _requires_evidence_closure(path, investigation, result):
            errors.extend(validate_evidence_closure(data, root, investigation))
    return errors


def validate_declared_results(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    manifests = load_manifest_results(root)
    for path in sorted((root / "research/validation/investigations").glob("VI-*.md")):
        text = path.read_text(encoding="utf-8")
        ident_match = re.search(r"## Investigation ID\s+\n\s*(VI-\d+)", text)
        if not ident_match:
            continue
        ident = ident_match.group(1)
        if re.search(r"(?:Result:\s*\*\*|Result:\s*|Scoped Result:\s*\*\*)PASS\b", text, re.IGNORECASE):
            if ident not in manifests:
                errors.append(f"{ident}: PASS declared without an execution manifest")
            elif manifests[ident] not in PASS_RESULTS:
                errors.append(f"{ident}: document declares PASS but manifest result is {manifests[ident]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    paths = execution_paths()
    manifest_results = load_manifest_results()
    errors = validate_manifest_registry()
    errors.extend(
        error
        for path in paths
        for error in validate_manifest(path, manifest_results=manifest_results)
    )
    errors.extend(validate_declared_results())
    if errors:
        print("Investigation execution validation: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Investigation execution validation: PASS ({len(paths)} manifests checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
