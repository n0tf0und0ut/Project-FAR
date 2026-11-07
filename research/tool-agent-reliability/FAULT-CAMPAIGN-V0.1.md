# Tool-agent deterministic fault campaign v0.1

Status: **Research — software regression/control only**. This additive harness does not change any governing theory, accepted methodology, production agent, frozen protocol, archived model output, or previously reported performance result.

## Why this exists

The existing `tools/tool_agent_reliability.py` runner already checkpoints original provider bytes, recomputes tool receipts and final state, and checks individual adverse cases. The bounded 72/72 synthetic-task model outcome is not a general reliability or FAR causal result. A repeatable host-level *fault campaign* provides a single falsifiable regression gate across failure categories without invoking Ollama or running a new model study.

The new `tools/tool_agent_fault_campaign.py` uses the current real runner, atomic checkpoint writer and verifier. Provider responses and time are scripted. The fixture and protocol identity are derived from committed fixture inputs. This checks code behavior under declared perturbations; it does not claim that any model would choose those actions.

## Test contract

The finite suite contains **10 scripted execution cases** with exact expected (passed, terminal reason, unsafe-attempt presence) tuples: a clean read/write/finish sequence; missing observation; wrong answer; protected-file overwrite followed by restoration; obedience to untrusted file instructions by creating a forbidden file; duplicate JSON action member; HTTP 503; connection drop after an initial observation; an incomplete provider envelope; and exhaustion of eight allowed actions.

For every case, the existing replay verifier must reconstruct the returned record, and a separate, fixture-specific oracle independently checks ordered observations, permitted writes, expected final files and the answer without calling `grade()`. The separate oracle is intentionally narrow; it is not a substitute for a general domain oracle.

Starting from a clean complete record, **13 targeted mutations** must be rejected: request hash, response hash, content changed with a newly valid hash, tool receipt, final file state, recorded grade, source identity, model identity, protocol identity, seed, event chronology, event reordering, and an extra event after terminal action. Rehashing altered bytes must not evade semantic reconstruction.

Every execution must have `SYNTHETIC_TEST` provenance. The harness verifies the exact number of scripted provider invocations, so an undeclared retry cannot hide behind a subsequent transport failure. The report includes SHA-256 identities of the fixture, runner module and campaign module. The report is fail-closed if any expected outcome differs, a clean recording is unreplayable, or any mutated recording is accepted. The test suite also checks exact within-environment repeatability, checkpoint agreement, preservation of a transient unsafe-write failure even when the final file was restored, and a deliberately broken verifier that accepts everything.

## Reproduce

From the repository root with Python 3.11+:

```bash
python -m unittest tests.test_tool_agent_fault_campaign -v
python -m tools.tool_agent_fault_campaign --out /tmp/tool-agent-fault-campaign.json
```

Exit status zero means **the declared 23 synthetic software checks passed**, not that an agent is reliable. Generated reports are derived runtime observations and must retain their exact source/head identity if used in a PR's evidence record. A report is not a replacement for prospective model evaluation or independent verification.

## Explicit limitations and stop rules

- `LOCAL_OLLAMA` is a *recorded provenance label*, not a cryptographic attestation of the responding model. The test `test_replay_is_not_model_origin_authentication` documents that relabeling an otherwise replayable synthetic record as `LOCAL_OLLAMA` is accepted by offline replay. Authenticity therefore requires trusted execution provenance and external receipt evidence; this suite does not provide those.
- The independent sentinel oracle covers only one synthetic input/output contract, not arbitrary tasks, tools, repository operations or distributed branches. It is not an independent external investigator.
- A deterministic scripted provider never measures model choice, generalized autonomous task success, FAR-versus-control performance, or real-world evidence quality. `general_agent_reliability=NOT_ESTABLISHED` and `far_causal_effect=NOT_TESTED` are mandatory report fields.
- Host-side checks cannot establish correctness for unimplemented tools or model actions outside the declared virtual filesystem.
- The current GitHub `main` remains the only canonical project state. Neither candidate branch checks nor a green PR workflow promotes a research result.

The suite borrows deterministic simulation and adversarial conformance methods commonly used in high-integrity infrastructure testing. No Pando code, Git backend, novel theory, external model service, or new dependency is imported.
