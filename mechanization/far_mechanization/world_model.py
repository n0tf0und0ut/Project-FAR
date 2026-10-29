"""FAR-WORLD/0.1: finite, provenance-bound world-state and causal simulation.

A model-relative experimental kernel. No response generation, autonomous source
interpretation, doctrinal authorization, probabilistic learning, or causal
identification is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker

VERSION = "FAR-WORLD/0.1"
ORTHODOX = "eastern-orthodox/0.1"
SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "far-world-model-v0.1.schema.json"
_DOMAINS = {"empirical", "theological", "normative"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class WorldModelError(ValueError):
    """Invalid input or unsupported operation; never return success on bad data."""


def _unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise WorldModelError(f"duplicate JSON key: {k}")
        result[k] = v
    return result


def _parse_raw(raw: str) -> dict:
    try:
        return json.loads(raw, object_pairs_hook=_unique,
                          parse_constant=lambda token: (_ for _ in ()).throw(WorldModelError("nonfinite JSON: " + token)))
    except (ValueError, TypeError) as exc:
        raise WorldModelError(str(exc)) from exc


def _canonical(value: object) -> bytes:
    """FAR-CJ/1-compatible canonical bytes (no NFC normalization)."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8", "strict")


def _instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise WorldModelError(f"invalid ISO date-time: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorldModelError("date-time requires UTC offset")
    return parsed.astimezone(timezone.utc)


def _index(rows: list[dict], name: str) -> dict[str, dict]:
    items = {x["id"]: x for x in rows}
    if len(items) != len(rows):
        raise WorldModelError(f"duplicate {name} ID")
    return items


def _literal(row: dict) -> tuple[str, bool]:
    return row["proposition_ref"], row["polarity"]


def _ordered_variables(variables: dict[str, dict]) -> list[str]:
    order = []
    visiting, visited = set(), set()

    def visit(k):
        if k in visiting:
            raise WorldModelError("causal model contains a directed cycle")
        if k in visited:
            return
        visiting.add(k)
        for p in variables[k]["parents"]:
            if p not in variables:
                raise WorldModelError("unresolved parent variable " + p)
            visit(p)
        visiting.remove(k)
        visited.add(k)
        order.append(k)

    for v in variables:
        visit(v)
    return order


def _validate(data: dict) -> None:
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data),
                        key=lambda e: (tuple(str(i) for i in e.path), e.message))
        if errors:
            raise WorldModelError("; ".join(f"{list(e.path)}: {e.message}" for e in errors))
        sources = _index(data["sources"], "source")
        propositions = _index(data["propositions"], "proposition")
        assertions = _index(data["assertions"], "assertion")
        _index(data["rules"], "rule")
        causal_models = _index(data["causal_models"], "causal model")
        foundation = data["christological_foundation"]
        root_id = foundation["proposition_ref"]
        root = propositions.get(root_id)
        if (root is None or root["domain"] != "theological" or
                root["framework_id"] != ORTHODOX or
                root["statement"] != "Jesus Christ is God."):
            raise WorldModelError("foundation must identify the explicit Jesus-is-God theological proposition")
        if (not foundation["source_refs"] or
                not set(foundation["source_refs"]) <= sources.keys() or
                any(sources[x]["kind"] not in {"scripture", "tradition"}
                    for x in foundation["source_refs"])):
            raise WorldModelError("foundation requires resolved Scripture/Tradition sources")
        grounding = foundation["ontological_grounding"]
        # This is a declared metaphysical relation, not a rule in the
        # consequence engine. In particular it cannot generate empirical,
        # mathematical, or moral propositions without explicit premises.
        if len(grounding["targets"]) != len(set(grounding["targets"])):
            raise WorldModelError("duplicate ontological grounding target")
        if not grounding["source_refs"] or not set(grounding["source_refs"]) <= sources.keys():
            raise WorldModelError("missing grounding source")
        if any(sources[x]["kind"] not in {"scripture", "tradition"} for x in grounding["source_refs"]):
            raise WorldModelError("invalid grounding source type")
        if not any(a["proposition_ref"] == root_id and a["polarity"] is True and
                   set(a["source_refs"]) & set(foundation["source_refs"])
                   for a in assertions.values()):
            raise WorldModelError("foundation must have a source-committed positive confession")
        if any(a["proposition_ref"] == root_id and a["polarity"] is False
               for a in assertions.values()):
            raise WorldModelError("a negative root assertion is incompatible with the fixed confessional profile")
        if any(a["supersedes"] is not None and
               assertions.get(a["supersedes"], {}).get("proposition_ref") == root_id
               for a in assertions.values()):
            raise WorldModelError("the confessional root is fixed and cannot be superseded")

        for row in sources.values():
            if hashlib.sha256(row["text"].encode("utf-8")).hexdigest() != row["sha256"]:
                raise WorldModelError(f"source digest mismatch: {row['id']}")
            if not _SHA256.fullmatch(row["sha256"]):
                raise WorldModelError("invalid digest")
        for p in propositions.values():
            if p["domain"] in ("normative", "theological") and p["framework_id"] != ORTHODOX:
                raise WorldModelError("normative/theological proposition must declare its framework")
            if p["domain"] == "empirical" and p["framework_id"] is not None:
                raise WorldModelError("empirical proposition cannot carry a theological framework")
        for a in assertions.values():
            prop = propositions.get(a["proposition_ref"])
            if prop is None:
                raise WorldModelError("assertion references missing proposition")
            if not a["source_refs"] or not set(a["source_refs"]) <= sources.keys():
                raise WorldModelError("assertion requires resolved source references")
            kinds = {sources[s]["kind"] for s in a["source_refs"]}
            if prop["domain"] == "empirical" and not (kinds & {"observation", "research"}):
                raise WorldModelError("empirical assertion requires empirical source")
            if prop["domain"] != "empirical" and not (kinds & {"scripture", "tradition"}):
                raise WorldModelError("theological/normative assertion requires scriptural/traditional source")
            if _instant(a["valid_at"]) > _instant(a["recorded_at"]):
                raise WorldModelError("future valid time cannot precede recording")
            prior = a["supersedes"]
            if prior is not None:
                if prior not in assertions or prior == a["id"]:
                    raise WorldModelError("supersedes references missing/self assertion")
                previous = assertions[prior]
                if previous["proposition_ref"] != a["proposition_ref"]:
                    raise WorldModelError("supersedes must revise the same proposition")
                if _instant(previous["recorded_at"]) >= _instant(a["recorded_at"]):
                    raise WorldModelError("supersedes chronology invalid")
        revised = [a["supersedes"] for a in assertions.values() if a["supersedes"] is not None]
        if len(revised) != len(set(revised)):
            raise WorldModelError("one assertion cannot have multiple successor revisions")
        for r in data["rules"]:
            head = r["conclusion"]["proposition_ref"]
            if head not in propositions or any(x["proposition_ref"] not in propositions for x in r["premises"]):
                raise WorldModelError("rule refers to missing proposition")
            if not r["premises"]:
                raise WorldModelError("zero-premise rules must be explicit sourced assertions")
            if not set(r["justification_refs"]) <= sources.keys() or not r["justification_refs"]:
                raise WorldModelError("rules require anchored justification sources")
            domains = {propositions[x["proposition_ref"]]["domain"] for x in r["premises"]}
            target = propositions[head]["domain"]
            if target == "empirical" and domains != {"empirical"}:
                raise WorldModelError("normative/theological inputs cannot imply empirical claims")
            if target == "theological" and domains != {"theological"}:
                raise WorldModelError("empirical/normative inputs cannot imply theological claims")
            if target == "normative" and not (domains & {"theological", "normative"}):
                raise WorldModelError("normative claim cannot follow from empirical facts alone")
            if target == "empirical":
                if r["framework_id"] is not None:
                    raise WorldModelError("empirical rule cannot be theology-indexed")
                if not any(sources[x]["kind"] in {"observation", "research"} for x in r["justification_refs"]):
                    raise WorldModelError("empirical rule requires empirical justification")
            else:
                if r["framework_id"] != ORTHODOX:
                    raise WorldModelError("theological/normative rule must declare the Orthodox framework")
                if not any(sources[x]["kind"] in {"scripture", "tradition"} for x in r["justification_refs"]):
                    raise WorldModelError("theological/normative rule requires theological justification")
        for model in causal_models.values():
            variables = _index(model["variables"], "causal variable")
            order = _ordered_variables(variables)
            if not set(model["source_refs"]) <= sources.keys() or not model["source_refs"]:
                raise WorldModelError("causal model requires cited model-assumption sources")
            if not any(sources[x]["kind"] in {"observation", "research"} for x in model["source_refs"]):
                raise WorldModelError("causal model needs empirical model-assumption references")
            for var in variables.values():
                parents = var["parents"]
                if len(parents) != len(set(parents)) or len(parents) > 8:
                    raise WorldModelError("causal parent set duplicated or exceeds bounded enumeration")
                table = var["table"]
                if not parents:
                    if table is not None:
                        raise WorldModelError("exogenous root must have null table")
                else:
                    if table is None or set(table) != {format(i, f"0{len(parents)}b") for i in range(2 ** len(parents))}:
                        raise WorldModelError("causal truth table incomplete or malformed")
            if not order:
                raise WorldModelError("causal model requires variables")
    except (KeyError, TypeError, AttributeError, UnicodeError) as exc:
        raise WorldModelError("invalid world model: " + str(exc)) from exc


@dataclass(frozen=True)
class WorldModel:
    """Immutable validated FAR world-model snapshot; no network dependencies."""
    _raw: bytes

    @classmethod
    def from_dict(cls, data: dict) -> "WorldModel":
        if not isinstance(data, dict):
            raise WorldModelError("document must be an object")
        try:
            raw = _canonical(data)
            frozen = _parse_raw(raw.decode("utf-8"))
            _validate(frozen)
        except (ValueError, TypeError, UnicodeError) as exc:
            raise WorldModelError(str(exc)) from exc
        return cls(raw)

    @classmethod
    def loads(cls, raw: str) -> "WorldModel":
        return cls.from_dict(_parse_raw(raw))

    @classmethod
    def load(cls, path: str | Path) -> "WorldModel":
        return cls.loads(Path(path).read_text(encoding="utf-8"))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self._raw).hexdigest()

    def to_dict(self) -> dict:
        return _parse_raw(self._raw.decode("utf-8"))

    def foundational_confession(self) -> dict:
        """Inspect the governing assumption without declaring it externally proved."""
        foundation = self.to_dict()["christological_foundation"]
        return {
            "proposition_ref": foundation["proposition_ref"],
            "kind": foundation["kind"],
            "source_refs": list(foundation["source_refs"]),
            "ontological_grounding": dict(foundation["ontological_grounding"]),
            "assurance": "ADOPTED_CONFESSIONAL_AXIOM_NOT_EMPIRICALLY_PROVED",
        }

    def derive(self, *, known_at: str, valid_at: str | None = None) -> "ModelState":
        """Recompute finite Horn consequences with bitemporal cutoffs.

        Belnap-like FOUR status is *about the declared model*; no explosion from
        conflicting literals. A source hash checks identity, never source truth.
        """
        knowledge_cutoff = _instant(known_at)
        world_cutoff = _instant(valid_at or known_at)
        data = self.to_dict()
        active = {a["id"]: a for a in data["assertions"]
                  if _instant(a["recorded_at"]) <= knowledge_cutoff and _instant(a["valid_at"]) <= world_cutoff}
        for a in active.copy().values():
            if a["supersedes"] in active:
                del active[a["supersedes"]]
        # finite sets of proof leaves + rule IDs, not a claim of logically
        # complete first-order closure or semantic validity of the declared rules.
        proofs: dict[tuple[str, bool], dict[str, set[str]]] = {}
        for a in active.values():
            target = (a["proposition_ref"], a["polarity"])
            bucket = proofs.setdefault(target, {"assertions": set(), "rules": set(), "sources": set()})
            bucket["assertions"].add(a["id"])
            bucket["sources"].update(a["source_refs"])
        changed = True
        while changed:
            changed = False
            for r in data["rules"]:
                if all(_literal(p) in proofs for p in r["premises"]):
                    head = _literal(r["conclusion"])
                    bucket = proofs.setdefault(head, {"assertions": set(), "rules": set(), "sources": set()})
                    before = sum(map(len, bucket.values()))
                    bucket["rules"].add(r["id"])
                    bucket["sources"].update(r["justification_refs"])
                    for premise in r["premises"]:
                        support = proofs[_literal(premise)]
                        for k in bucket:
                            bucket[k].update(support[k])
                    if sum(map(len, bucket.values())) != before:
                        changed = True
        return ModelState(data, proofs, known_at, valid_at or known_at, self.digest)

    def simulate(self, model_id: str, *, context: dict[str, bool],
                 interventions: dict[str, bool] | None = None) -> dict[str, bool]:
        """Deterministic Boolean SCM simulation, conditional on stipulated tables.

        This is an on-model intervention; it does not identify causal effects in
        an observational dataset or claim equations are faithful to reality.
        """
        if not isinstance(context, dict) or not isinstance(interventions, (dict, type(None))):
            raise WorldModelError("context/interventions must be objects")
        models = {m["id"]: m for m in self.to_dict()["causal_models"]}
        if model_id not in models:
            raise WorldModelError("unknown causal model")
        variables = _index(models[model_id]["variables"], "causal variable")
        interventions = interventions or {}
        if (set(context) - set(variables) or set(interventions) - set(variables)
                or any(type(v) is not bool for v in (*context.values(), *interventions.values()))):
            raise WorldModelError("unknown causal variable or non-Boolean assignment")
        roots = {k for k, v in variables.items() if not v["parents"]}
        if set(context) != roots - set(interventions):
            raise WorldModelError("context must assign exactly the unintervened exogenous roots")
        result = {}
        for var_id in _ordered_variables(variables):
            if var_id in interventions:
                result[var_id] = interventions[var_id]
            elif var_id in roots:
                result[var_id] = context[var_id]
            else:
                v = variables[var_id]
                key = "".join("1" if result[x] else "0" for x in v["parents"])
                result[var_id] = v["table"][key]
        return result

    def counterfactual(self, model_id: str, *, context: dict[str, bool],
                       interventions: dict[str, bool]) -> dict:
        if not isinstance(interventions, dict) or not interventions:
            raise WorldModelError("counterfactual needs at least one intervention")
        # For interventions on a root, the baseline root assignment must be
        # supplied separately and retained for the un-intervened world.
        baseline = self.simulate(model_id, context=context)
        what_if = self.simulate(model_id, context={k: v for k, v in context.items() if k not in interventions},
                                interventions=interventions)
        return {"baseline": baseline, "intervened": what_if,
                "changed_variables": sorted(k for k in baseline if baseline[k] != what_if[k]),
                "assurance": "MODEL_RELATIVE_STIPULATED_BOOLEAN_SCM"}


@dataclass(frozen=True)
class ModelState:
    _document: dict
    _proofs: dict
    known_at: str
    valid_at: str
    model_sha256: str

    def status(self, proposition_id: str) -> str:
        ids = {p["id"] for p in self._document["propositions"]}
        if proposition_id not in ids:
            raise WorldModelError("unregistered proposition")
        yes = (proposition_id, True) in self._proofs
        no = (proposition_id, False) in self._proofs
        return "BOTH" if yes and no else "SUPPORTED" if yes else "REFUTED" if no else "UNKNOWN"

    def inspect(self, proposition_id: str) -> dict:
        """Full audit record; never conceal theological premises from audit."""
        p = next((x for x in self._document["propositions"] if x["id"] == proposition_id), None)
        if p is None:
            raise WorldModelError("unregistered proposition")
        supports = {}
        for polarity in (True, False):
            entry = self._proofs.get((proposition_id, polarity), {})
            supports["positive" if polarity else "negative"] = {key: sorted(entry.get(key, ()))
                                                                  for key in ("assertions", "rules", "sources")}
        return {"proposition": dict(p), "status": self.status(proposition_id),
                "supports": supports, "known_at": self.known_at, "valid_at": self.valid_at,
                "world_sha256": self.model_sha256, "assurance": "MODEL_RELATIVE_DECLARED_PREMISES"}

    def project(self, kind: str = "empirical", *, expose_basis: bool = False) -> list[dict]:
        """Non-linguistic model projection; not a user-facing answer generator.

        Default moral projection omits worldview provenance from this projection,
        *not* from immutable source data or inspect(). Biblical projection and
        explicit expose_basis reveal it. Truth-status always remains scoped.
        """
        if kind not in {"empirical", "moral", "biblical", "all"}:
            raise WorldModelError("unsupported model projection")
        accepted = {"empirical"} if kind == "empirical" else {"normative"} if kind == "moral" else {"theological", "normative"} if kind == "biblical" else _DOMAINS
        result = []
        for p in self._document["propositions"]:
            if p["domain"] not in accepted:
                continue
            row = {"proposition_id": p["id"], "statement": p["statement"],
                   "domain": p["domain"], "status": self.status(p["id"]),
                   "assurance": "MODEL_RELATIVE_DECLARED_PREMISES"}
            if kind in {"biblical", "all"} or expose_basis:
                inspected = self.inspect(p["id"])
                row["framework_id"] = p["framework_id"]
                row["supports"] = inspected["supports"]
            result.append(row)
        return result
