import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_current_state_consistency as checker


EXPECTED_RELEASE = "v1.0.0"
PROGRAM_ID = "EXTERNAL-FALSIFICATION-AND-REPLICATION-001"
PREDECESSOR_ID = "POST-CLOSURE-001"
NEXT_WORKSTREAM = None

VALID_TEXTS = {
    "readme": (
        "## Latest release: v1.0.0\n"
        "`PROJECT-FAR-CORE-THEORY-1.1`\n"
        "Historical v1.0\n"
        "## Post-closure phase\n"
        "`POST-CLOSURE-001` is complete at all six registered workstream scopes.\n"
        "`PCA-W6-EMPIRICAL-AUDIT-UTILITY` is complete.\n"
        "No W7 is registered by `POST-CLOSURE-001`.\n"
    ),
    "status": (
        "Current published repository release: [`v1.0.0`]\n"
        "Current governing theory: `PROJECT-FAR-CORE-THEORY-1.1`.\n"
        "Completed predecessor: `POST-CLOSURE-001` — **complete at its six registered workstream scopes**.\n"
        "Current program: `EXTERNAL-FALSIFICATION-AND-REPLICATION-001`.\n"
        "| `PCA-W6-EMPIRICAL-AUDIT-UTILITY` | Complete | boundary |\n"
        "No `POST-CLOSURE-001` W7 is registered.\n"
    ),
    "map": (
        "Project FAR Core Theory v1.1\n"
        "Historical Project FAR Core Theory v1.0\n"
        "Post-Closure Assurance and Application Program\n"
        "External Falsification and Replication Program\n"
        "Current Project FAR release: [`releases/project-far-v1.0.0.md`](releases/project-far-v1.0.0.md)\n"
    ),
    "roadmap": (
        "Current published repository release: [`v1.0.0`]\n"
        "Current governing core: [`PROJECT-FAR-CORE-THEORY-1.1`]\n"
        "Completed predecessor: [`POST-CLOSURE-001`], complete at its six registered workstream scopes.\n"
        "Current program: [`EXTERNAL-FALSIFICATION-AND-REPLICATION-001`].\n"
        "`PCA-W6-EMPIRICAL-AUDIT-UTILITY` — complete.\n"
        "No W7 is currently registered.\n"
    ),
    "generated": (
        "# Historical Bounded-Program Status (Generated)\n"
        "not a current project-status authority\n"
    ),
    "next_actions": (
        "Program: `POST-CLOSURE-001` — complete.\n"
        "Current program: `EXTERNAL-FALSIFICATION-AND-REPLICATION-001` — preregistered.\n"
        "Current governing theory: `PROJECT-FAR-CORE-THEORY-1.1`.\n"
        "Historical v1.0 Core\n"
        "There is **no registered next `POST-CLOSURE-001` workstream**.\n"
        "OPEN-EXTERNAL-OP-28\n"
    ),
    "matrix": (
        "I1 — Claimed Isolation\n"
        "does **not** prove that every scalarization is impossible\n"
        "finite-corpus result, not a population estimate\n"
    ),
    "efr_protocol": (
        "Status: **PREREGISTERED — NOT EXECUTED**\n"
        "not `PCA-W7` or “W7.”\n"
    ),
    "agents": (
        "If current authoritative sources conflict, stop the affected inference and report the conflict. "
        "Prior chats, summaries and cached copies are not substitutes. "
        "Repository presence, memories, generated outputs and archives do not confer acceptance.\n"
    ),
}


class CurrentStateConsistencyTests(unittest.TestCase):
    def validate(self, texts, next_workstream=NEXT_WORKSTREAM):
        return checker.validate_texts(
            texts, EXPECTED_RELEASE, PROGRAM_ID, next_workstream
        )

    def test_consistent_terminal_state_passes(self):
        self.assertEqual([], self.validate(copy.deepcopy(VALID_TEXTS)))

    def test_consistent_state_passes(self):
        """Preserve the pre-W6 regression ID against the terminal state."""
        self.test_consistent_terminal_state_passes()

    def test_stale_current_release_is_rejected(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["roadmap"] += "v0.4.0 is the current release baseline\n"
        errors = self.validate(texts)
        self.assertTrue(any("stale current-state assertion" in error for error in errors))

    def test_historical_generated_report_cannot_claim_current_mode(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["generated"] += "## Current Research Mode\n"
        errors = self.validate(texts)
        self.assertTrue(any("Current Research Mode" in error for error in errors))

    def test_terminal_next_actions_cannot_invent_workstream(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["next_actions"] += "Canonical next workstream: `PCA-W7-FAKE`.\n"
        errors = self.validate(texts)
        self.assertTrue(any("terminal program still declares a canonical next workstream" in error for error in errors))

    def test_next_actions_must_follow_registered_next_workstream(self):
        """Preserve the active-state regression ID at the no-W7 boundary."""
        self.test_terminal_next_actions_cannot_invent_workstream()

    def test_terminal_status_cannot_mark_next_active(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["status"] += "| `PCA-W7-FAKE` | **Next / Active** | invalid |\n"
        errors = self.validate(texts)
        self.assertTrue(any("Next / Active" in error for error in errors))

    def test_map_cannot_redeclare_completed_predecessor_current(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["map"] += "Current program: `docs/governance/post-closure-assurance-and-application-program-v1.0.md`.\n"
        self.assertTrue(any("completed predecessor is still declared current" in e for e in self.validate(texts)))

    def test_terminal_no_w7_boundary_is_required(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["roadmap"] = texts["roadmap"].replace("No W7 is currently registered.\n", "")
        errors = self.validate(texts)
        self.assertTrue(any("no-W7 boundary" in error for error in errors))

    def test_superseded_upp_queue_cannot_return(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["next_actions"] += "PTE-W1-INDEPENDENT-REVIEW\n"
        errors = self.validate(texts)
        self.assertTrue(any("superseded UPP evaluation planning" in error for error in errors))

    def test_agent_routing_must_subordinate_memory(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["agents"] = (
            "If current authoritative sources conflict, stop the affected inference and report the conflict. "
            "Repository presence, memories, generated outputs and archives do not confer acceptance.\n"
        )
        errors = self.validate(texts)
        self.assertTrue(any("subordinate memory" in error for error in errors))

    def test_agent_routing_must_fail_closed_on_authority_conflict(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["agents"] = texts["agents"].replace(
            "If current authoritative sources conflict, stop the affected inference and report the conflict. ", ""
        )
        self.assertTrue(any("authority conflicts" in error for error in self.validate(texts)))

    def test_agent_routing_must_not_promote_repository_presence(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["agents"] = texts["agents"].replace(
            "Repository presence, memories, generated outputs and archives do not confer acceptance.", ""
        )
        self.assertTrue(any("epistemic authority" in error for error in self.validate(texts)))

    def test_historical_v1_0_cannot_be_repromoted_as_current(self):
        texts = copy.deepcopy(VALID_TEXTS)
        texts["status"] += "Current governing theory: `PROJECT-FAR-CORE-THEORY-1.0`\n"
        errors = self.validate(texts)
        self.assertTrue(any("stale current-state assertion" in error for error in errors))

    def test_program_identity_parses_active_registered_next_workstream(self):
        program = (
            "Program: `POST-CLOSURE-001`\n\n"
            "- `PCA-W0-REPOSITORY-CONFORMITY`: complete.\n"
            "- `PCA-W6-EMPIRICAL-AUDIT-UTILITY`: **open — next**.\n"
        )
        self.assertEqual(
            (PREDECESSOR_ID, "PCA-W6-EMPIRICAL-AUDIT-UTILITY"),
            checker.program_identity(program),
        )

    def test_program_identity_parses_registered_next_workstream(self):
        """Preserve the parser regression ID for an explicitly active workstream."""
        self.test_program_identity_parses_active_registered_next_workstream()

    def test_program_identity_allows_explicit_terminal_absence(self):
        program = (
            "Program: `POST-CLOSURE-001`\n\n"
            "Status: **Complete at the six registered workstream scopes; downstream external utility remains open**\n\n"
            "- `PCA-W6-EMPIRICAL-AUDIT-UTILITY`: complete.\n"
            "No W7 is registered by this program.\n"
        )
        self.assertEqual((PREDECESSOR_ID, None), checker.program_identity(program))


if __name__ == "__main__":
    unittest.main()
