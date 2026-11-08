"""Black-box checker contracts and source-derived adversarial mutants.

These are internal, project-authored adversarial controls, not external evaluator
independence or a population estimate of mutation-detection power.  Each fixture
runs the *actual CLI* in a disposable miniature repository. Expected acceptance
is specified here, not imported from the checker under test. Source mutants are
confined to temporary copies; the tracked checker and evidence are untouched.
"""
from __future__ import annotations

import json
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GOVERNANCE = "tools/check_governance_register_integrity.py"
CLAIMS = "tools/check_claim_status_ceiling.py"
SEMANTIC = "tools/check_semantic_consistency.py"
CI = "tools/check_ci_workflows.py"
STATUS = "tools/check_project_status.py"
EXTERNAL = "tools/check_external_validation_terms.py"
LEGACY = {
    GOVERNANCE: "test_governance_register_integrity.py",
    CLAIMS: "test_claim_status_ceiling.py",
    SEMANTIC: "test_semantic_consistency.py",
}


def _copy(source: str, destination: Path) -> None:
    target = destination / source
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / source, target)


def _fixture(root: Path, checker: str) -> None:
    _copy(checker, root)
    if checker in LEGACY:
        _copy("tests/" + LEGACY[checker], root)
    if checker == GOVERNANCE:
        for name in (
            "README.md",
            "docs/project-status.md",
            "docs/CANONICAL_MAP.md",
            "docs/governance/claim-status-matrix.md",
            "docs/governance/limitations-register.md",
            "docs/governance/open-problems-register.md",
        ):
            _copy(name, root)
    elif checker == CLAIMS:
        _copy("theory/evaluation/central-claim-registry.json", root)
    elif checker == SEMANTIC:
        registry = "docs/governance/semantic-consistency.json"
        _copy(registry, root)
        for name in (
            "README.md",
            "docs/ARCHITECTURE.md",
            "docs/CANONICAL_MAP.md",
            "docs/glossary/canonical-terminology.md",
        ):
            _copy(name, root)
        data = json.loads((ROOT / registry).read_text(encoding="utf-8"))
        for name in data["required_documents"]:
            _copy(name, root)
    elif checker == CI:
        workflow = root / ".github/workflows/example.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            "name: Validation fixture\non: workflow_dispatch\njobs:\n"
            "  check:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps: []\n",
            encoding="utf-8",
        )
    elif checker == STATUS:
        status = root / "docs/project-status.md"
        status.parent.mkdir(parents=True)
        status.write_text("# Current status\n", encoding="utf-8")
    elif checker == EXTERNAL:
        for name in ("README.md", "docs/project-status.md"):
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("# Current facts\n", encoding="utf-8")
    else:
        raise ValueError(f"unknown checker: {checker}")


def _run_checker(root: Path, checker: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", checker],
        cwd=root, capture_output=True, text=True, timeout=30, check=False,
    )


def _run_legacy(root: Path, checker: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover",
         "-s", "tests", "-p", LEGACY[checker]],
        cwd=root, capture_output=True, text=True, timeout=90, check=False,
    )


def _append_promotion(root: Path, phrase: str) -> None:
    target = root / "README.md"
    target.write_text(target.read_text(encoding="utf-8") + "\n" + phrase + "\n", encoding="utf-8")


def _remove_claim(root: Path, claim_id: str) -> None:
    path = root / "theory/evaluation/central-claim-registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["claims"] = [c for c in data["claims"] if c["id"] != claim_id]
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def _duplicate_claim(root: Path, claim_id: str) -> None:
    path = root / "theory/evaluation/central-claim-registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    match = next(c for c in data["claims"] if c["id"] == claim_id)
    data["claims"].append(dict(match))
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def _remove_ci_timeout(root: Path) -> None:
    path = root / ".github/workflows/example.yml"
    text = path.read_text(encoding="utf-8")
    assert "    timeout-minutes: 5\n" in text
    path.write_text(text.replace("    timeout-minutes: 5\n", ""), encoding="utf-8")


def _remove_canonical_status(root: Path) -> None:
    (root / "docs/project-status.md").unlink()


def _claim_external_validation(root: Path) -> None:
    path = root / "README.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\nIndependent validation achieved without any external replication.\n",
        encoding="utf-8",
    )


def _remove_procedure(root: Path, value: str) -> None:
    path = root / "docs/governance/semantic-consistency.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["procedures"].remove(value)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


class BehavioralCheckerAssuranceTests(unittest.TestCase):
    def test_valid_governance_input_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root, GOVERNANCE)
            result = _run_checker(root, GOVERNANCE)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_label_status_promotions_are_rejected_by_the_executable(self):
        # Punctuation-separated labels are the known formerly accepted counterexample.
        examples = (
            "Novelty: established",
            "Priority — demonstrated",
            "External validation: confirmed",
            "Universality | proved",
            "I3: validated",
            "Necessity: proven",
            "**Novelty**: **established**",
            "*Priority*: *confirmed*",
            "**Novelty:** established",
            "| **External validation** | confirmed |",
            "| **Priority** | **proved** |",
            "_Novelty_: _established_",
            "__Priority__: __confirmed__",
            "`Novelty`: `established`",
        )
        for phrase in examples:
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                self.assertIn("unnegated assurance promotion", result.stdout)

    def test_negated_labels_do_not_trigger_a_false_alarm(self):
        for phrase in (
            "Novelty: not established",
            "I3: unresolved",
            "Universality — not proved",
            "**Novelty**: **not established**",
            "Novelty: established only if independently replicated.",
            "Novelty: established unless a prior example is found.",
            "If independently replicated, novelty: established.",
            "If independently replicated and externally reviewed, novelty: established.",
            "Novelty: established, only if independently replicated.",
            "Novelty: established, but only if independently replicated.",
            "Novelty: established, unless a prior example is found.",
            "| Assurance | Status | Condition |\\n|---|---|---|\\n| Novelty | established | only if independently replicated |".replace("\\n", "\n"),
            "| Novelty | established | unless a prior example is found |",
            "Novelty: not established, Priority: not confirmed.",
            "Do not assert novelty: established.",
            "| **External validation** | confirmed only if independently replicated |",
        ):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_local_context_does_not_hide_an_adjacent_false_promotion(self):
        # Two statements on one line must be judged separately, including in
        # a Markdown-table row. Whole-line NEGATION matching is not sufficient.
        cases = (
            "Novelty: not established; Priority: confirmed",
            "Novelty: not established and Priority: proved",
            "Novelty: not established but Priority: proved",
            "Novelty: not established while Priority: proved",
            "Priority: proved whereas Novelty: not established",
            "Novelty: established; Priority: not established",
            "Novelty: established only if independently replicated; Priority: proved",
            "Novelty: established, Priority: not confirmed",
            "Novelty: not established, Priority: proved",
            "If independently replicated, novelty: established, Priority: proved",
            "Novelty: established, only if independently replicated, Priority: proved",
            "Novelty: established, but only if independently replicated, Priority: proved",
            "| Novelty | established | only if independently replicated | Priority | confirmed |",
            "| Novelty | established | not confirmed |",
            "| **Novelty** | not established | **Priority** | confirmed |",
        )
        for phrase in cases:
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                self.assertIn("unnegated assurance promotion", result.stdout)

    def test_explicit_shared_condition_qualifies_both_coordinated_statuses(self):
        for phrase in (
            "If independently replicated, both novelty: established and priority: established.",
            "If independently replicated, novelty: established and priority: established.",
            "If independently replicated and externally reviewed, both novelty: established and priority: confirmed.",
            "Unless a prior example is found, both novelty: established and priority: demonstrated.",
            "**If** independently replicated, **both** **novelty:** **established** and _priority_: _established_.",
            "`Unless` a prior example is found, both __novelty__: __established__ and *priority*: *demonstrated*.",
            "- If independently replicated, both novelty: established and priority: established.",
            "* **If** independently replicated, both novelty: established and priority: established.",
        ):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_shared_condition_does_not_qualify_independent_statuses(self):
        for phrase in (
            "Both novelty: established and priority: established.",
            "If independently replicated, both novelty: established, priority: established.",
            "If independently replicated, both novelty: established and priority: established; uniqueness: proved.",
            "If independently replicated, both novelty: established and priority: established, uniqueness: proved.",
            "If independently replicated, both novelty: established and priority: established and uniqueness: proved.",
            "| If independently replicated, both novelty: established | and priority: established |",
            "**If** independently replicated, **both** novelty: established and priority: established, __uniqueness__: __proved__.",
            "If independently replicated, **both** novelty: established, __priority__: __established__.",
        ):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                self.assertIn("unnegated assurance promotion", result.stdout)

    def test_condition_cell_emphasis_preserves_qualification(self):
        for condition in (
            "**only if independently replicated**",
            "*if independently replicated*",
            "__unless a prior example is found__",
            "`only if independently replicated`",
            "**only** if independently replicated",
            "*only* if independently replicated",
            "__only__ if independently replicated",
            "**_only_ if** independently replicated",
            "_only_ if independently replicated",
            "`only` if independently replicated",
            "*only if* independently replicated",
            "_only if_ independently replicated",
            "__only if__ independently replicated",
            "`only if` independently replicated",
        ):
            phrase = "| Assurance | Status | Condition |\n|---|---|---|\n| Novelty | established | " + condition + " |"
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_formatted_condition_cells_do_not_hide_neighboring_promotions(self):
        for phrase in (
            "| Novelty | established | **not confirmed** |",
            "| Novelty | established | **only if independently replicated** | Priority | confirmed |",
            "| Novelty | established | **Priority: not confirmed** |",
            "| __Novelty__ | __established__ | **only** if independently replicated | `Priority` | `confirmed` |",
            "| Novelty | established | *only* | if independently replicated |",
            "| Novelty | established | **only if independently replicated |",
        ):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                self.assertIn("unnegated assurance promotion", result.stdout)

    def test_condition_introducers_have_consistent_local_and_shared_scope(self):
        for condition in (
            "If independently replicated",
            "Only if independently replicated",
            "Unless a prior example is found",
        ):
            for phrase in (
                condition + ", both novelty: established and priority: established.",
                "Novelty: not established, but " + condition.lower() + ", priority: established.",
                "Novelty: not established, and " + condition.lower() + ", priority: established.",
                "Novelty: established, but " + condition.lower() + ".",
                "Novelty: not established, but " + condition.lower() + ", both priority: established and external validation: established.",
                condition + ", both novelty: not established and priority: established.",
                condition + ", both novelty: unresolved and priority: established.",
            ):
                with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _fixture(root, GOVERNANCE)
                    _append_promotion(root, phrase)
                    result = _run_checker(root, GOVERNANCE)
                    self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_following_claim_conditions_never_qualify_previous_promotion(self):
        for condition in (
            "if independently replicated",
            "only if independently replicated",
            "unless a prior example is found",
        ):
            for conjunction in ("but", "and", "whereas", "while"):
                phrase = "Novelty: established, " + conjunction + " " + condition + ", priority: not established."
                with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _fixture(root, GOVERNANCE)
                    _append_promotion(root, phrase)
                    result = _run_checker(root, GOVERNANCE)
                    self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                    self.assertIn("unnegated assurance promotion", result.stdout)

    def test_numeric_punctuation_preserves_conditions_but_not_sentence_scope(self):
        for phrase in (
            "If the external replication meets the preregistered p < 0.05 threshold, external validation: established.",
            "Only if p < .05, both novelty: established and priority: established.",
            "Unless error exceeds 1.25 percent, both novelty: established and priority: confirmed.",
            "| External validation | established | only if p < 0.05 |",
        ):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)
        for phrase in (
            "If p < 0.05, novelty: established. Priority: established.",
            "If p < .05, novelty: established; Priority: established.",
            "Only if p < 0.05, both novelty: established and priority: established, uniqueness: proved.",
            "Novelty: not established. Priority: established.",
        ):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                self.assertIn("unnegated assurance promotion", result.stdout)

    def test_explicit_pair_preserves_shared_leading_prohibitions(self):
        for qualifier in ("Do not assert", "Do not claim", "Never claim", "No basis to claim"):
            for pair in (
                "both novelty: established and priority: established.",
                "both **novelty:** **established** and _priority_: _established_.",
            ):
                phrase = qualifier + " " + pair
                with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _fixture(root, GOVERNANCE)
                    _append_promotion(root, phrase)
                    result = _run_checker(root, GOVERNANCE)
                    self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_explicit_pair_preserves_shared_trailing_qualification(self):
        for qualifier in (
            ", only if independently replicated.",
            " only if independently replicated.",
            ", if independently replicated.",
            ", unless a prior example is found.",
            ", but only if independently replicated.",
            " are not asserted.",
            " remain unresolved.",
            " are not established.",
            ", **only** if p < 0.05.",
        ):
            for pair in (
                "Both novelty: established and priority: established",
                "Both novelty: established and priority: not established",
            ):
                phrase = pair + qualifier
                with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _fixture(root, GOVERNANCE)
                    _append_promotion(root, phrase)
                    result = _run_checker(root, GOVERNANCE)
                    self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_explicit_pair_context_never_masks_independent_promotions(self):
        cases = (
            "Do not assert novelty: established and priority: established.",
            "Do not assert both novelty: established, priority: established.",
            "Do not assert both novelty: established and priority: established; uniqueness: proved.",
            "Never claim both novelty: established and priority: established, uniqueness: proved.",
            "Both novelty: not established and priority: established.",
            "Both novelty: established and priority: not established.",
            "Both novelty: established and priority: established, only if replicated; uniqueness: proved.",
            "Both novelty: established and priority: established, only if replicated, uniqueness: proved.",
            "Both novelty: established and priority: established, but if replicated, uniqueness: not established.",
            "| Both novelty | established | and priority | not established |",
            "| Do not assert both novelty | established | and priority | established |",
            "Novelty: established, only if replicated but priority: proved.",
            "Both novelty: established and priority: established, only if replicated but uniqueness: proved.",
            "Both novelty: established and priority: established, unless refuted whereas uniqueness: proved.",
        )
        cases += tuple(
            qualifier + " both novelty: established and priority: established" + separator + "uniqueness: proved."
            for qualifier in ("Do not assert", "Do not claim", "Never claim", "No basis to claim")
            for separator in (", ", "; ", " but ", " and ", " while ", " whereas ")
        )
        cases += tuple(
            "Both novelty: established and priority: established, " + qualifier + separator + "uniqueness: proved."
            for qualifier in ("only if replicated", "unless refuted", "if externally replicated")
            for separator in (", ", "; ", " but ", " and ", " while ", " whereas ")
        )
        for phrase in cases:
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                self.assertIn("unnegated assurance promotion", result.stdout)

    def test_following_negated_claim_never_qualifies_unconditional_pair(self):
        for qualifier in ("not", "do not assert", "never claim", "no basis to claim", "without asserting"):
            for conjunction in ("and", "but", "while", "whereas"):
                phrase = "Both novelty: established and priority: established, " + conjunction + " " + qualifier + " uniqueness: established."
                with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    _fixture(root, GOVERNANCE)
                    _append_promotion(root, phrase)
                    result = _run_checker(root, GOVERNANCE)
                    self.assertNotEqual(0, result.returncode, phrase + "\n" + result.stdout)
                    self.assertIn("unnegated assurance promotion: 'novelty: established'", result.stdout)
                    self.assertIn("unnegated assurance promotion: 'priority: established'", result.stdout)

    def test_local_prohibitions_after_no_comma_conjunction_remain_local(self):
        for qualifier in ("do not assert", "do not claim", "never claim", "no basis to claim", "without asserting"):
            for conjunction in ("and", "but", "while", "whereas"):
                for claim in (
                    "priority: established.",
                    "both priority: established and uniqueness: established.",
                ):
                    phrase = "Novelty: not established " + conjunction + " " + qualifier + " " + claim
                    with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        _fixture(root, GOVERNANCE)
                        _append_promotion(root, phrase)
                        result = _run_checker(root, GOVERNANCE)
                        self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_trailing_qualification_composes_with_following_independent_claim(self):
        for condition in ("if independently replicated", "only if independently replicated", "unless refuted"):
            for conjunction in ("and", "but", "while", "whereas"):
                for preceding in (
                    "Novelty: established",
                    "Both novelty: established and priority: established",
                ):
                    for following, accepted in (
                        ("uniqueness: not established.", True),
                        ("do not assert uniqueness: established.", True),
                        ("uniqueness: established.", False),
                    ):
                        phrase = preceding + ", but " + condition + ", " + conjunction + " " + following
                        with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                            root = Path(directory)
                            _fixture(root, GOVERNANCE)
                            _append_promotion(root, phrase)
                            result = _run_checker(root, GOVERNANCE)
                            self.assertEqual(accepted, result.returncode == 0, phrase + "\n" + result.stdout)

    def test_conjunctions_inside_leading_conditions_stay_with_their_claim(self):
        for condition in (
            "if independently replicated and externally reviewed",
            "only if independently replicated and externally reviewed",
            "unless refuted or contradicted",
        ):
            phrase = "Novelty: not established, but " + condition + ", priority: established."
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, GOVERNANCE)
                _append_promotion(root, phrase)
                result = _run_checker(root, GOVERNANCE)
                self.assertEqual(0, result.returncode, phrase + "\n" + result.stdout)

    def test_bounded_qualifier_composition_matrix(self):
        # Expected claim ownership is declared by templates, independently of
        # the parser. This is a finite controlled grammar, not general English.
        spec = importlib.util.spec_from_file_location("composition_checker", ROOT / GOVERNANCE)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        leading = (
            ("If independently replicated, ", True),
            ("Only if p < 0.05, ", True),
            ("Unless refuted, ", True),
            ("**Only** if p < .05 and independently replicated, ", True),
            ("Do not assert ", False), ("Never claim ", False), ("No basis to claim ", False),
        )
        trailing = (
            ", only if independently replicated",
            ", but only if p < 0.05",
            ", unless refuted",
            ", **only** if p < .05",
            " are not asserted", " remain unresolved",
        )
        cases = []
        for mark in ("", "**", "`"):
            x, y, z = (mark + name + mark + ": " + mark + "established" + mark for name in ("novelty", "priority", "uniqueness"))
            for join in (", and ", ", but ", " and ", " but "):
                for following, expected in ((z, {"uniqueness"}), ("uniqueness: not established", set())):
                    for prefix, conditional_pair in leading:
                        # Existing controlled grammar shares a leading
                        # condition across X-and-Y even without "both".
                        member_expected = set() if conditional_pair and join == " and " else expected
                        cases.append((prefix + x + join + following, member_expected))
                        cases.append((prefix + "both " + x + " and " + y + join + following, expected))
                        cases.append((x + join + prefix + following, {"novelty"}))
                        cases.append(("Both " + x + " and " + y + join + prefix + following, {"novelty", "priority"}))
                    for suffix in trailing:
                        cases.append((x + suffix + join + following, expected))
                        cases.append(("Both " + x + " and " + y + suffix + join + following, expected))
        failures = []
        for text, expected in cases:
            result = checker.promotion_clauses(text + ".")
            observed = {name for name in ("novelty", "priority", "uniqueness")
                        if any(re.search(r"\b" + name + r"\b", entry, re.I) for entry in result)}
            if observed != expected:
                failures.append((text, sorted(expected), result))
        self.assertEqual(0, len(failures), f"{len(failures)}/{len(cases)} ownership failures; first cases: {failures[:8]}")
        print(f"BOUNDED_COMPOSITION: {len(cases)} independently specified ownership cases passed")

    def test_nonfirst_missing_and_duplicate_claims_are_rejected(self):
        for change in (_remove_claim, _duplicate_claim):
            with self.subTest(change=change.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, CLAIMS)
                change(root, "CLM-ECONOMY")
                result = _run_checker(root, CLAIMS)
                self.assertNotEqual(0, result.returncode, result.stdout)
                self.assertIn("CLM-ECONOMY", result.stdout)

    def test_each_required_procedure_is_semantically_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root, SEMANTIC)
            baseline = _run_checker(root, SEMANTIC)
            self.assertEqual(0, baseline.returncode, baseline.stdout + baseline.stderr)
            _remove_procedure(root, "fail report")
            result = _run_checker(root, SEMANTIC)
            self.assertNotEqual(0, result.returncode, result.stdout)
            self.assertIn("unclassified procedure", result.stdout)

    def test_additional_checker_cli_contracts_reject_false_acceptance(self):
        # Independent expectations for three further production checkers.
        cases = (
            (CI, _remove_ci_timeout, "missing timeout-minutes"),
            (STATUS, _remove_canonical_status, "missing canonical docs/project-status.md"),
            (EXTERNAL, _claim_external_validation, "unqualified independent validation"),
        )
        for checker, corrupt, diagnostic in cases:
            with self.subTest(checker=checker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, checker)
                baseline = _run_checker(root, checker)
                self.assertEqual(0, baseline.returncode, baseline.stdout + baseline.stderr)
                corrupt(root)
                result = _run_checker(root, checker)
                self.assertNotEqual(0, result.returncode, checker + "\n" + result.stdout)
                self.assertIn(diagnostic, result.stdout)

    def test_additional_checker_benign_inputs_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture(root, EXTERNAL)
            path = root / "README.md"
            path.write_text(
                "Independent validation requires new external evidence.\n", encoding="utf-8"
            )
            result = _run_checker(root, EXTERNAL)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_semantic_mutants_are_exposed_by_black_box_inputs(self):
        # These mutants retain syntax, realistic branches and failure paths.
        # Some survive the old paired unit tests; the independent CLI fixtures
        # must catch their *observable* false acceptance, without trusting
        # the mutant's own internal status calculation.
        experiments = (
            (GOVERNANCE,
             "established|proved|proven|demonstrated|confirmed|validated",
             "established|proved|proven|demonstrated|validated",
             lambda root: _append_promotion(root, "External validation: confirmed"),
             "promotional-verb-omission"),
            (GOVERNANCE,
             "for match in LABEL_PROMOTION.finditer(statement):",
             "for match in ():",
             lambda root: _append_promotion(root, "Novelty: established"),
             "label-check-disabling"),
            (CLAIMS,
             "if missing := sorted(set(CEILINGS) - seen):",
             'if missing := sorted((set(CEILINGS) - seen) - {"CLM-ECONOMY"}):',
             lambda root: _remove_claim(root, "CLM-ECONOMY"),
             "claim-specific-omission"),
            (CLAIMS,
             "if cid in seen:",
             'if cid in seen and cid != "CLM-ECONOMY":',
             lambda root: _duplicate_claim(root, "CLM-ECONOMY"),
             "claim-specific-duplicate-bypass"),
            (SEMANTIC,
             '"Pareto comparison", "fail report", "uncertainty output"',
             '"Pareto comparison", "uncertainty output"',
             lambda root: _remove_procedure(root, "fail report"),
             "required-procedure-erasure"),
            (CI,
             "if 'timeout-minutes' not in job:",
             "if 'timeout-minutes' not in job and job_name != 'check':",
             _remove_ci_timeout,
             "ci-timeout-specific-bypass"),
            (STATUS,
             "if not (ROOT/'docs/project-status.md').exists():",
             "if not (ROOT/'docs/project-status.md').exists() and (ROOT/'docs/PROJECT_STATUS.md').exists():",
             _remove_canonical_status,
             "canonical-status-absence-bypass"),
            (EXTERNAL,
             "'independent validation' in low and not any(",
             "'independent validation' in low and 'achieved' not in low and not any(",
             _claim_external_validation,
             "external-validation-claim-exemption"),
        )
        for checker, before, after, change, identifier in experiments:
            with self.subTest(identifier=identifier), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _fixture(root, checker)
                change(root)
                original = _run_checker(root, checker)
                self.assertNotEqual(0, original.returncode, f"{identifier}: original failed to reject")
                source_path = root / checker
                source = source_path.read_text(encoding="utf-8")
                self.assertEqual(1, source.count(before), identifier + " mutation anchor changed")
                source_path.write_text(source.replace(before, after, 1), encoding="utf-8")
                mutant = _run_checker(root, checker)
                self.assertEqual(
                    0, mutant.returncode,
                    f"{identifier}: this mutation no longer produces a false acceptance; replace the canary\n"
                    + mutant.stdout + mutant.stderr,
                )
                # Baseline paired suite runs against the mutated *implementation*
                # but unchanged registered inputs, in an independent clean fixture.
                # Compare the pre-existing paired tests only where a
                # registered paired suite exists. No suite is not a PASS.
                old_suite_result = "not_registered"
                if checker in LEGACY:
                    with tempfile.TemporaryDirectory() as clean_directory:
                        clean = Path(clean_directory)
                        _fixture(clean, checker)
                        baseline_paired = _run_legacy(clean, checker)
                        self.assertEqual(
                            0, baseline_paired.returncode,
                            f"{identifier}: old suite baseline not executable on fixture\n"
                            + baseline_paired.stdout + baseline_paired.stderr,
                        )
                        (clean / checker).write_text(source.replace(before, after, 1), encoding="utf-8")
                        old = _run_legacy(clean, checker)
                        old_suite_result = "survived" if old.returncode == 0 else "killed"
                print(
                    f"ADVERSARIAL {identifier}: original_reject=1 "
                    f"mutant_false_accept=1 old_suite={old_suite_result}"
                )


if __name__ == "__main__":
    unittest.main()
