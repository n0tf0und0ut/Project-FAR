"""Command-line interface for Project FAR mechanization."""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence
import yaml

from .diagnostics import Diagnostic, DiagnosticSeverity, SourceLocation, DiagnosticCode
from .external_models import FORMAT_VERSION, ExternalFARDocument
from .graph_engine import build_graph, compute_reachability, graph_statistics, resolve_references, validate_dependencies, validate_graph
from .conformance import run_conformance
from .parser import ParseResult, parse_document, parse_file
from .serialization import serialize_json, serialize_yaml, external_to_data
from .normalization import normalize_ir_document
from .epistemic import EpistemicDocument, EpistemicValidationError, calibration

CLI_VERSION = "0.6.0"
FOUNDATION_VERSION = "v1.0"
IR_VERSION = "far-ir/1.0"

@dataclass(frozen=True, slots=True)
class CLIConfig:
    output: str = "text"
    quiet: bool = False
    verbose: bool = False
    color: str = "auto"

def _load_config(path: str | None) -> CLIConfig:
    if not path:
        return CLIConfig()
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return CLIConfig()
        return CLIConfig(output=str(data.get("output", "text")), quiet=bool(data.get("quiet", False)), verbose=bool(data.get("verbose", False)), color=str(data.get("color", "auto")))
    except OSError:
        return CLIConfig()

def _effective(args: argparse.Namespace) -> CLIConfig:
    cfg = _load_config(getattr(args, "config", None))
    return CLIConfig(output=args.output or cfg.output, quiet=args.quiet or cfg.quiet, verbose=args.verbose or cfg.verbose, color=args.color or cfg.color)

def _diagnostic_to_dict(d: Diagnostic) -> dict[str, Any]:
    return {
        "code": d.code.value,
        "severity": d.severity.value,
        "message": d.message,
        "source": None if d.source is None else {"source": d.source.source, "line": d.source.line, "column": d.source.column, "end_line": d.source.end_line, "end_column": d.source.end_column},
        "related_identifier": d.related_identifier,
        "details": dict(d.details),
    }

def _diagnostics_json(diagnostics: Sequence[Diagnostic]) -> str:
    return json.dumps([_diagnostic_to_dict(d) for d in _sort_diagnostics(diagnostics)], indent=2, sort_keys=True) + "\n"

def _sort_diagnostics(diagnostics: Sequence[Diagnostic], sort: str = "code") -> tuple[Diagnostic, ...]:
    if sort == "severity":
        order = {DiagnosticSeverity.ERROR: 0, DiagnosticSeverity.WARNING: 1, DiagnosticSeverity.INFO: 2}
        return tuple(sorted(diagnostics, key=lambda d: (order[d.severity], d.code.value, d.message)))
    if sort == "source":
        return tuple(sorted(diagnostics, key=lambda d: ((d.source.source if d.source else ""), d.code.value, d.message)))
    return tuple(sorted(diagnostics, key=lambda d: (d.code.value, d.message)))

def _diagnostics_text(diagnostics: Sequence[Diagnostic], sort: str = "code") -> str:
    if not diagnostics:
        return "No diagnostics.\n"
    lines = []
    for d in _sort_diagnostics(diagnostics, sort):
        loc = f" {d.source.source}" if d.source else ""
        if d.source and d.source.line:
            loc += f":{d.source.line}"
            if d.source.column: loc += f":{d.source.column}"
        ident = f" [{d.related_identifier}]" if d.related_identifier else ""
        lines.append(f"{d.severity.value.upper()} {d.code.value}{ident}{loc}: {d.message}")
    return "\n".join(lines) + "\n"

def _summary(diagnostics: Sequence[Diagnostic]) -> dict[str, int]:
    return {"error": sum(1 for d in diagnostics if d.severity == DiagnosticSeverity.ERROR), "warning": sum(1 for d in diagnostics if d.severity == DiagnosticSeverity.WARNING), "info": sum(1 for d in diagnostics if d.severity == DiagnosticSeverity.INFO), "total": len(diagnostics)}

def _read_stdin_or_file(path: str | None) -> tuple[str | None, str | None, tuple[Diagnostic, ...]]:
    if path in {None, "-"}:
        return sys.stdin.read(), "<stdin>", ()
    try:
        return Path(path).read_text(encoding="utf-8"), path, ()
    except OSError as exc:
        return None, path, (Diagnostic(DiagnosticCode.UNREADABLE_FILE, DiagnosticSeverity.ERROR, str(exc), SourceLocation(path)),)

def _parse_input(args: argparse.Namespace) -> ParseResult:
    if getattr(args, "file", None) == "-":
        text, source, ds = _read_stdin_or_file("-")
        if ds: return ParseResult(None, ds, source, None, None)
        return parse_document(text or "", source, getattr(args, "format", None))
    return parse_file(args.file, explicit_format=getattr(args, "format", None))

def _validate(args: argparse.Namespace) -> tuple[int, str, str]:
    cfg = _effective(args)
    result = _parse_input(args)
    diagnostics = list(result.diagnostics)
    if result.document is not None:
        graph = build_graph(result.document).graph
        diagnostics.extend(validate_graph(graph, result.document).diagnostics)
        diagnostics.extend(validate_dependencies(result.document, graph))
    if cfg.output == "json":
        out = json.dumps({"valid": not diagnostics, "summary": _summary(diagnostics), "diagnostics": [_diagnostic_to_dict(d) for d in _sort_diagnostics(diagnostics)]}, indent=2, sort_keys=True) + "\n"
    else:
        out = "" if cfg.quiet and diagnostics else ("VALID\n" if not diagnostics else "INVALID\n")
        if not cfg.quiet: out += _diagnostics_text(diagnostics)
    return (0 if not diagnostics else 1), out, ""

def _parse_cmd(args: argparse.Namespace) -> tuple[int, str, str]:
    result = _parse_input(args)
    if not result.success:
        return 1, _diagnostics_json(result.diagnostics) if args.output == "json" else "", _diagnostics_text(result.diagnostics)
    external, ds = ExternalFARDocument.from_ir(result.document)
    if args.output == "json":
        return 0, json.dumps(external_to_data(external), indent=2, sort_keys=True) + "\n", ""
    if args.output == "yaml":
        return 0, yaml.safe_dump(external_to_data(external), sort_keys=True, allow_unicode=True), ""
    return 0, f"FARDocument {result.document.identifier}\nInvestigation {result.document.investigation.identifier}: {result.document.investigation.question}\n", ""

def _normalize(args: argparse.Namespace) -> tuple[int, str, str]:
    result = _parse_input(args)
    if not result.success: return 1, "", _diagnostics_text(result.diagnostics)
    ser = serialize_yaml(result.document) if args.output == "yaml" else serialize_json(result.document)
    if not ser.success: return 1, "", _diagnostics_text(ser.diagnostics)
    if args.write:
        path = Path(args.write)
        if path.exists() and not args.force:
            return 1, "", f"Refusing to overwrite existing file: {path}\n"
        path.write_text(ser.text, encoding="utf-8")
        return 0, f"Wrote {path}\n", ""
    return 0, ser.text or "", ""

def _graph_data(document) -> tuple[dict[str, Any], tuple[Diagnostic, ...]]:
    built = build_graph(document)
    graph = built.graph
    validation = validate_graph(graph, document)
    stats = graph_statistics(graph, validation.diagnostics)
    data = {
        "nodes": [{"id": str(n.identifier), "kind": n.node_kind.value} for n in graph.nodes],
        "edges": [{"id": str(e.identifier), "kind": e.edge_kind.value, "source": str(e.source.identifier), "target": str(e.target.identifier)} for e in graph.edges],
        "statistics": asdict(stats),
    }
    return data, built.diagnostics + validation.diagnostics

def _graph(args: argparse.Namespace) -> tuple[int, str, str]:
    result = _parse_input(args)
    if not result.success: return 1, "", _diagnostics_text(result.diagnostics)
    data, diagnostics = _graph_data(result.document)
    if args.export:
        Path(args.export).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output == "json":
        return (0 if not diagnostics else 1), json.dumps(data | {"diagnostics": [_diagnostic_to_dict(d) for d in diagnostics]}, indent=2, sort_keys=True) + "\n", ""
    s=data["statistics"]
    return (0 if not diagnostics else 1), f"Nodes: {s['node_count']}\nEdges: {s['edge_count']}\nDependencies: {s['dependency_count']}\nCycles: {s['cycle_count']}\n", _diagnostics_text(diagnostics) if diagnostics else ""

def _diagnostics_cmd(args: argparse.Namespace) -> tuple[int, str, str]:
    code, out, err = _validate(args)
    if args.output == "json": return code, out, err
    result = _parse_input(args)
    diagnostics = list(result.diagnostics)
    if result.document is not None:
        graph = build_graph(result.document).graph
        diagnostics.extend(validate_graph(graph, result.document).diagnostics)
        diagnostics.extend(validate_dependencies(result.document, graph))
    return code, _diagnostics_text(diagnostics, args.sort), ""

def _stats(args: argparse.Namespace) -> tuple[int, str, str]:
    result = _parse_input(args)
    if not result.success: return 1, "", _diagnostics_text(result.diagnostics)
    graph = build_graph(result.document).graph
    diagnostics = validate_graph(graph, result.document).diagnostics
    stats = asdict(graph_statistics(graph, diagnostics))
    if args.output == "json": return 0, json.dumps(stats, indent=2, sort_keys=True) + "\n", ""
    return 0, "\n".join(f"{k}: {v}" for k, v in stats.items()) + "\n", ""

def _export(args: argparse.Namespace) -> tuple[int, str, str]:
    result = _parse_input(args)
    if not result.success: return 1, "", _diagnostics_text(result.diagnostics)
    if args.kind == "graph-json":
        data, diagnostics = _graph_data(result.document)
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    elif args.kind == "yaml":
        ser = serialize_yaml(result.document); diagnostics = ser.diagnostics; text = ser.text or ""
    else:
        ser = serialize_json(result.document); diagnostics = ser.diagnostics; text = ser.text or ""
    if diagnostics: return 1, "", _diagnostics_text(diagnostics)
    if args.output_file:
        Path(args.output_file).write_text(text, encoding="utf-8")
        return 0, f"Wrote {args.output_file}\n", ""
    return 0, text, ""

def _inspect(args: argparse.Namespace) -> tuple[int, str, str]:
    result = _parse_input(args)
    if not result.success: return 1, "", _diagnostics_text(result.diagnostics)
    graph = build_graph(result.document).graph
    nodes = {str(n.identifier): n for n in graph.nodes}
    if args.identifier not in nodes:
        return 1, "", f"Identifier not found: {args.identifier}\n"
    incoming = [e for e in graph.edges if str(e.target.identifier) == args.identifier]
    outgoing = [e for e in graph.edges if str(e.source.identifier) == args.identifier]
    data = {"id": args.identifier, "type": nodes[args.identifier].node_kind.value, "metadata": dict(nodes[args.identifier].metadata), "incoming_edges": [str(e.identifier) for e in incoming], "outgoing_edges": [str(e.identifier) for e in outgoing], "dependencies": [str(e.target.identifier) for e in outgoing if e.edge_kind.value == "depends_on"]}
    if args.output == "json": return 0, json.dumps(data, indent=2, sort_keys=True) + "\n", ""
    return 0, f"Identifier: {data['id']}\nType: {data['type']}\nIncoming edges: {len(incoming)}\nOutgoing edges: {len(outgoing)}\nDependencies: {', '.join(data['dependencies']) or '-'}\n", ""

def _version(args: argparse.Namespace) -> tuple[int, str, str]:
    cfg = _effective(args)
    from . import __version__ as package_version
    data = {"foundation_version": FOUNDATION_VERSION, "ir_version": IR_VERSION, "schema_version": FORMAT_VERSION, "package_version": package_version, "cli_version": CLI_VERSION}
    if cfg.output == "json": return 0, json.dumps(data, indent=2, sort_keys=True) + "\n", ""
    return 0, "\n".join(f"{k}: {v}" for k, v in data.items()) + "\n", ""

def _conformance(args: argparse.Namespace) -> tuple[int, str, str]:
    result = run_conformance(getattr(args, "manifest", None) or None)
    if args.output == "json":
        out = json.dumps({"suite": result.suite, "passed": result.passed, "failed": result.failed, "total": result.total, "success": result.success, "results": [asdict(r) for r in result.results]}, indent=2, sort_keys=True) + "\n"
    else:
        lines = [f"Conformance suite {result.suite}: {result.passed}/{result.total} passed"]
        lines.extend(("PASS" if r.passed else "FAIL") + f" {r.case_id}" for r in result.results)
        out = "\n".join(lines) + "\n"
    return (0 if result.success else 1), out, ""

def _epistemic(args: argparse.Namespace) -> tuple[int, str, str]:
    """Validate or summarize a validated epistemic loop."""
    try:
        document = EpistemicDocument.load(args.file)
        if args.epistemic_command == "validate":
            payload = {"valid": True, "content_hash": document.digest,
                       "audit_event": document.audit_event()}
        elif args.epistemic_command == "calibration":
            records = document.to_dict()["records"]
            by_id = {record["id"]: record for record in records}
            outcomes = [
                {"probability": by_id[record["prediction_ref"]]["probability"],
                 "binary_outcome": record["binary_outcome"],
                 "reference_class": by_id[record["prediction_ref"]]["reference_class"]}
                for record in records if record["kind"] == "outcome"
            ]
            payload = calibration(outcomes, bin_edges=args.bin_edges.split(","))
        else:
            payload = document.to_dict()
    except (OSError, json.JSONDecodeError, EpistemicValidationError) as exc:
        details = list(exc.errors) if isinstance(exc, EpistemicValidationError) else [str(exc)]
        return 1, json.dumps({"valid": False, "errors": details}, indent=2, sort_keys=True) + "\n", ""
    return 0, json.dumps(payload, indent=2, sort_keys=True) + "\n", ""

def _cognitive(args: argparse.Namespace) -> tuple[int, str, str]:
    from .cognitive import CognitiveDocument, CognitiveValidationError, audit
    try:
        document = CognitiveDocument.load(args.file)
        payload = audit(document) if args.cognitive_command == "audit" else {"valid": True, "status": "Research", "input_sha256": document.digest}
        return 0, json.dumps(payload, sort_keys=True, indent=2) + "\n", ""
    except (OSError, UnicodeError, CognitiveValidationError) as exc:
        return 2, json.dumps({"valid": False, "errors": [str(exc)]}, sort_keys=True) + "\n", ""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="far", description="Project FAR mechanization CLI")
    p.add_argument("--config"); p.add_argument("--output", choices=["text","json","yaml"], default=None); p.add_argument("--quiet", action="store_true"); p.add_argument("--verbose", action="store_true"); p.add_argument("--color", choices=["auto","always","never"], default=None)
    sub = p.add_subparsers(dest="command")
    def add_common(cmd):
        cmd.add_argument("--output", choices=["text","json","yaml"], default=None)
        cmd.add_argument("--quiet", action="store_true")
        cmd.add_argument("--verbose", action="store_true")
        cmd.add_argument("--color", choices=["auto","always","never"], default=None)
        return cmd
    def add_file(cmd):
        add_common(cmd); cmd.add_argument("file"); cmd.add_argument("--format", choices=["json","yaml"]); return cmd
    add_file(sub.add_parser("validate", help="validate a FAR document")).set_defaults(func=_validate)
    add_file(sub.add_parser("parse", help="parse and display canonical IR")).set_defaults(func=_parse_cmd)
    n=add_file(sub.add_parser("normalize", help="normalize a FAR document")); n.add_argument("--write"); n.add_argument("--force", action="store_true"); n.set_defaults(func=_normalize)
    g=add_file(sub.add_parser("graph", help="build and report graph")); g.add_argument("--export"); g.set_defaults(func=_graph)
    d=add_file(sub.add_parser("diagnostics", help="print diagnostics")); d.add_argument("--sort", choices=["severity","code","source"], default="code"); d.set_defaults(func=_diagnostics_cmd)
    add_file(sub.add_parser("stats", help="print graph statistics")).set_defaults(func=_stats)
    e=add_file(sub.add_parser("export", help="export normalized document or graph")); e.add_argument("--kind", choices=["json","yaml","graph-json"], default="json"); e.add_argument("--output-file"); e.set_defaults(func=_export)
    i=add_file(sub.add_parser("inspect", help="inspect an identifier")); i.add_argument("identifier"); i.set_defaults(func=_inspect)
    c=add_common(sub.add_parser("conformance", help="run far-ir/1.0 conformance suite")); c.add_argument("--manifest"); c.set_defaults(func=_conformance)
    ep = sub.add_parser("epistemic", help="operate on additive far-epistemic/1.0 records")
    eps = ep.add_subparsers(dest="epistemic_command", required=True)
    cmd = eps.add_parser("validate"); cmd.add_argument("file"); cmd.set_defaults(func=_epistemic)
    cal = eps.add_parser("calibration"); cal.add_argument("file"); cal.add_argument("--bin-edges", default="0,0.5,1"); cal.set_defaults(func=_epistemic)
    cog = sub.add_parser("cognitive", help="Research FAR-COG/0.1 audit of anchored, explicitly coded observations")
    cogs = cog.add_subparsers(dest="cognitive_command", required=True)
    for name in ("validate", "audit"):
        cmd = cogs.add_parser(name); cmd.add_argument("file"); cmd.set_defaults(func=_cognitive)
    add_common(sub.add_parser("version", help="show versions")).set_defaults(func=_version)
    sub.add_parser("help", help="show help").set_defaults(func=lambda args: (0, p.format_help(), ""))
    return p

def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser(); args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help(); return 0
    code, out, err = args.func(args)
    if out: sys.stdout.write(out)
    if err: sys.stderr.write(err)
    return code

if __name__ == "__main__":
    raise SystemExit(main())
