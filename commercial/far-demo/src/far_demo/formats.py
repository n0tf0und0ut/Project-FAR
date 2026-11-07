from __future__ import annotations

import csv
import io
import json
import re
import tomllib
from xml.parsers.expat import ExpatError
from zipfile import BadZipFile
from pathlib import Path
from typing import Any

import xmltodict
import yaml
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from lxml.etree import XMLSyntaxError
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from far_decision_integrity.strict_json import loads_strict

SUPPORTED_EXTENSIONS = {
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".csv",
    ".txt",
    ".md",
    ".docx",
    ".pdf",
    ".xlsx",
}

ACCEPT_ATTRIBUTE = ",".join(sorted(SUPPORTED_EXTENSIONS))


class _UniquePackageYamlLoader(yaml.SafeLoader):
    """Component-local counterpart of the repository's unique-key SafeLoader.

    Inspect the entire original node graph before construction mutates merge
    sources, retaining native inherited-default/explicit-override semantics.
    """

    def get_single_data(self):
        node = self.get_single_node()
        if node is None:
            return None
        _validate_yaml_keys(self, node)
        return self.construct_document(node)


def _validate_yaml_keys(loader, root):
    pending = [root]
    visited = set()
    while pending:
        node = pending.pop()
        if id(node) in visited:
            continue
        visited.add(id(node))
        if isinstance(node, yaml.SequenceNode):
            pending.extend(node.value)
        elif isinstance(node, yaml.MappingNode):
            seen = set()
            merge_seen = False
            for key_node, value_node in node.value:
                pending.extend((key_node, value_node))
                if key_node.tag == 'tag:yaml.org,2002:merge':
                    if merge_seen:
                        raise ValueError('Duplicate YAML merge key')
                    merge_seen = True
                    continue
                # Complex mapping keys are unhashable under SafeLoader. Avoid
                # constructing them here, which could flatten another node.
                if not isinstance(key_node, yaml.ScalarNode):
                    raise ValueError('Unhashable YAML mapping key')
                # SafeLoader normalizes this special key tag to a string during
                # flatten_mapping. Compare that same scalar text without changing
                # the original node or constructing the unsupported value tag.
                key = (key_node.value if key_node.tag == 'tag:yaml.org,2002:value'
                       else loader.construct_object(key_node))
                if key in seen:
                    raise ValueError(f'Duplicate YAML mapping key {key!r}')
                seen.add(key)


def _load_yaml(text: str) -> Any:
    try:
        return yaml.load(text, Loader=_UniquePackageYamlLoader)
    except RecursionError as exc:
        raise ValueError('YAML nesting exceeds the supported decoder limit') from exc


def parse_package_file(filename: str, data: bytes) -> dict[str, Any]:
    try:
        return _parse_package_file(filename, data)
    except (yaml.YAMLError, ExpatError, BadZipFile, PackageNotFoundError,
            XMLSyntaxError, InvalidFileException, PdfReadError, KeyError) as exc:
        raise ValueError(f"Invalid {Path(filename).suffix.lower()} package: {exc}") from exc


def _parse_package_file(filename: str, data: bytes) -> dict[str, Any]:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type {suffix or '(none)'}. Supported: {supported}.")

    if suffix == ".json":
        return _require_mapping(loads_strict(data.decode("utf-8")))
    if suffix == ".jsonl":
        return _parse_jsonl(data.decode("utf-8"))
    if suffix in {".yaml", ".yml"}:
        return _require_mapping(_load_yaml(data.decode("utf-8")))
    if suffix == ".toml":
        return _require_mapping(tomllib.loads(data.decode("utf-8")))
    if suffix == ".xml":
        return _normalize_xml(xmltodict.parse(data))
    if suffix == ".csv":
        return _table_rows_to_payload(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    if suffix == ".xlsx":
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValueError("The XLSX file is empty.")
        headers = [str(value or "").strip() for value in rows[0]]
        records = [dict(zip(headers, row, strict=False)) for row in rows[1:]]
        return _table_rows_to_payload(records)
    if suffix == ".docx":
        document = Document(io.BytesIO(data))
        return _parse_embedded_text("\n".join(paragraph.text for paragraph in document.paragraphs))
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return _parse_embedded_text("\n".join(page.extract_text() or "" for page in reader.pages))
    return _parse_embedded_text(data.decode("utf-8"))


def _require_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("The uploaded file must decode to one FAR decision-package object.")
    return value


def _parse_jsonl(text: str) -> dict[str, Any]:
    objects = _jsonl_values(text)
    if len(objects) != 1:
        raise ValueError("A FAR JSONL upload must contain exactly one non-empty JSON object.")
    return _require_mapping(objects[0])


def _jsonl_values(text: str) -> list[Any]:
    return [loads_strict(line) for line in text.splitlines() if line.strip()]


def _parse_embedded_text(text: str) -> dict[str, Any]:
    candidates = [(None, text.strip())]
    # Complete fence labels are authoritative. A prefix such as "jsonc",
    # "json5", or "json-schema" is not a declared JSON block. Unsupported
    # labeled snippets must not suppress a later legitimate package.
    for match in re.finditer(r"```([^\r\n`]*)\r?\n(.*?)```", text, re.I | re.S):
        language = match.group(1).strip().lower()
        if language in {"", "json", "jsonl", "yaml", "yml", "toml"}:
            candidates.append((language, match.group(2).strip()))
    errors: list[str] = []
    for hint, candidate in candidates:
        if not candidate:
            continue
        # A format declaration is binding. In particular, malformed or ambiguous
        # fenced JSON must never be accepted by the more permissive YAML parser.
        if hint in {'json', 'jsonl'}:
            values = _jsonl_values(candidate) if hint == 'jsonl' else [loads_strict(candidate)]
            if hint == 'jsonl' and len(values) != 1 and any(isinstance(value, dict) for value in values):
                raise ValueError('A FAR JSONL upload must contain exactly one non-empty JSON object.')
            if len(values) == 1 and isinstance(values[0], dict):
                return values[0]
            continue
        if hint in {'yaml', 'yml', 'toml'}:
            parser = tomllib.loads if hint == 'toml' else _load_yaml
            value = parser(candidate)
            if isinstance(value, dict):
                return value
            continue
        try:
            value = loads_strict(candidate)
            if isinstance(value, dict):
                return value
            # Supporting JSON fragments are not package candidates. They do not
            # relax strict errors or override a later decision-package object.
            continue
        except json.JSONDecodeError as exc:
            # Unlabeled text can contain a YAML/TOML document, not JSON.
            errors.append(str(exc))
        except ValueError as exc:
            # The strict JSON decoder can invoke a semantic hook before checking
            # whether the candidate is a *complete* JSON value. For example,
            # "NaN handling..." or "NaN: note" begins with a nonfinite token
            # but is ordinary prose or YAML, respectively. Only such syntax
            # failures may fall through to document parsers. A complete JSON
            # value containing nonfinite numbers, duplicate keys, or overflow
            # remains terminal, as does any JSON-shaped object/array.
            if candidate.lstrip().startswith(("{", "[")):
                raise
            try:
                json.loads(candidate)  # Syntax probe only; never use its result.
            except json.JSONDecodeError:
                errors.append(str(exc))
            else:
                raise
        for parser in (_load_yaml, tomllib.loads):
            try:
                value = parser(candidate)
                if isinstance(value, dict):
                    return value
            except (yaml.YAMLError, tomllib.TOMLDecodeError) as exc:
                errors.append(str(exc))
    raise ValueError(
        "No embedded FAR package was found. Text, Markdown, PDF, and DOCX files must contain "
        "one JSON, YAML, or TOML decision-package object."
    )


def _normalize_xml(data: dict[str, Any]) -> dict[str, Any]:
    root = next(iter(data.values())) if len(data) == 1 else data
    root = _require_mapping(root)
    payload = dict(root)

    nodes_container = payload.get("nodes", {})
    dependencies_container = payload.get("dependencies", {})
    nodes = nodes_container.get("node", []) if isinstance(nodes_container, dict) else nodes_container
    dependencies = (
        dependencies_container.get("dependency", [])
        if isinstance(dependencies_container, dict)
        else dependencies_container
    )
    payload["nodes"] = _as_list(nodes)
    payload["dependencies"] = _as_list(dependencies)

    requirements = payload.get("authorization_requirements", {})
    if isinstance(requirements, dict):
        requirements = requirements.get("node_id", requirements.get("requirement", []))
    payload["authorization_requirements"] = _as_list(requirements)

    unknowns = payload.get("unknowns", {})
    if isinstance(unknowns, dict):
        unknowns = unknowns.get("unknown", [])
    payload["unknowns"] = _as_list(unknowns)

    if "trace_completeness" in payload:
        payload["trace_completeness"] = float(payload["trace_completeness"])
    payload.setdefault("metadata", {})
    payload.setdefault("proposed_action", {})
    for node in payload["nodes"]:
        if isinstance(node, dict):
            node.setdefault("attributes", {})
    return payload


def _as_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def _table_rows_to_payload(rows: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "nodes": [],
        "dependencies": [],
        "authorization_requirements": [],
        "unknowns": [],
        "metadata": {},
        "proposed_action": {},
    }
    for raw in rows:
        row = {str(key).strip(): value for key, value in dict(raw).items() if key is not None}
        record_type = str(row.get("record_type") or "").strip().lower()
        if not record_type:
            continue
        if record_type == "meta":
            key = str(row.get("key") or "").strip()
            value = _coerce(row.get("value"))
            if key.startswith("metadata."):
                payload["metadata"][key.removeprefix("metadata.")] = value
            elif key.startswith("proposed_action."):
                payload["proposed_action"][key.removeprefix("proposed_action.")] = value
            else:
                payload[key] = value
        elif record_type == "node":
            payload["nodes"].append(
                {
                    "node_id": str(row.get("node_id") or "").strip(),
                    "kind": str(row.get("kind") or "").strip(),
                    "statement": str(row.get("statement") or "").strip(),
                    "attributes": _coerce(row.get("attributes") or "{}"),
                }
            )
        elif record_type == "dependency":
            payload["dependencies"].append(
                {
                    "source_id": str(row.get("source_id") or "").strip(),
                    "target_id": str(row.get("target_id") or "").strip(),
                    "relation": str(row.get("relation") or "").strip(),
                }
            )
        elif record_type == "authorization_requirement":
            payload["authorization_requirements"].append(
                str(row.get("node_id") or row.get("value") or "").strip()
            )
        elif record_type == "unknown":
            payload["unknowns"].append(str(row.get("statement") or row.get("value") or "").strip())
        else:
            raise ValueError(f"Unknown tabular record_type: {record_type}.")
    return payload


def _coerce(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return ""
    try:
        return loads_strict(text)
    except json.JSONDecodeError:
        return text
    except ValueError:
        # Strict numeric/member hooks can reject a prefix before the JSON
        # decoder knows whether the *whole* cell is a JSON value. Only a
        # syntax-invalid cell may fall back to plain text; complete ambiguous
        # or non-finite JSON must retain the strict rejection.
        try:
            json.loads(text)  # Syntax probe only; never consume its result.
        except json.JSONDecodeError:
            return text
        raise
