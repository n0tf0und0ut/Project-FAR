# SATURATION-FALSIFICATION-001

Status: Research / Provisional reconstruction  
Base: `8618384efe4576580f65ff67b02b22bac43ffc51`

This campaign reconstructs the interrupted SATURATION-FALSIFICATION-001 run from the surviving transcript and the canonical repository. It is not a byte-for-byte recovery of the unpushed local commit `f3bd22de`.

## Question

Can Saturation Baseline v0.5 represent **and enforce** the decision-relevant distinctions introduced by the selected findings without changing a first-class capability class, invariant, assurance boundary, or extension interface?

Broad category fit is not sufficient. A finding counts as absorbed only when the frozen architecture has typed, non-opaque surfaces for the distinction and an existing validation/decision hook capable of making it consequential.

## Hostile-review result

All seven tested findings are `REPRESENTABLE_NO_CHANGE`.

| Finding | Why v0.5 already absorbs the distinction |
|---|---|
| Hearsay / independent evidentiary observation | v0.5 already represents source lineage, source dependence, attestation, provenance, evidence independence, `INDEPENDENCE_LIMITED`, and explicit evidence requirements. A self-authored record and an independently observed/corroborating record are therefore distinct typed evidence states. |
| SkillCascade / cross-skill composition | v0.5 already represents dependency-bearing transformations/relations; every consequential transformation is inspectable, every consequential relationship is challengeable, and consequential transitions require validator contracts. A composition can therefore carry a validation state distinct from its components. |
| Verification before reliance-state promotion | v0.5 already has fail-closed `EXPLORATORY` / `EXTERNAL_RELIANCE_PENDING` / `EXTERNAL_RELIANCE_READY` states and requires successful applicable assurance validation before recorded promotion. |
| Synthesis / provenance fidelity | v0.5 already requires synthesis to preserve disagreement, uncertainty, contradicting evidence, alternatives, source lineage, and forbids summaries from strengthening the underlying graph. |
| Who&When Pro / failure-origin localization | v0.5 already makes `CAUSES` a challengeable provenance-bearing relation and routes causal claims through a specialized gate. Detection and causal-origin attribution need not collapse. |
| CRV coverage / realization / validity | v0.5 already makes evaluation stage-specific and separately names retrieval coverage, evidence-support accuracy, and adjudication accuracy. |
| Lean kernel trust-base qualification | v0.5 already bounds downstream assurance by inherited uncertainty, applies validation discipline to FAR's own formal outputs, and requires assurance cases to retain unresolved defeaters/limitations linked to evidence or validation records. |

No operative amendment is justified by this campaign. The previous candidate `saturation-baseline-v0.5-amendment-a1.md` is retained only as a **WITHDRAWN / NON-OPERATIVE** tombstone so the failed repair remains auditable.

## What the result means

The **bounded no-change hypothesis survives these seven attacks**. That is evidence that the literal v0.5 architecture is broader than the first reconstruction credited.

It is **not** evidence that v0.5 is globally saturated, minimal, uniquely correct, fully implemented, or commercially useful. Repeatedly fitting new findings into broad buckets would be unfalsifiable; the supporting record therefore binds every disposition to literal baseline anchors and decision/enforcement hooks.

The findings can still expose implementation-assurance work. In particular, SkillCascade is a direct reason to test supported orchestration paths at composition level rather than infer safety from component passes. That is an implementation coverage question, not an architecture delta.

## Source freeze

All six papers are pinned to exact arXiv `v1` identities in `findings-v1.0.json`.

The three mutable Lean sources are additionally bound to bounded content receipts in `source-receipts-v1.0.json`. Each receipt stores the exact decisive excerpt used by this campaign plus its SHA-256. The receipt is intentionally not a full-page republication.

## Review corrections incorporated

The reconstruction originally manufactured deltas by asking whether v0.5 used the exact new paper terminology rather than whether its existing typed objects, relations, invariants, and validators could preserve the same decision-relevant distinction. Hostile review corrected that error.

The final record also:
- removes the false zero-match Lean scan;
- does not redefine FARA candidate admission;
- pins paper sources to exact arXiv revisions;
- content-binds the mutable Lean evidence with bounded receipts;
- withdraws Amendment A1 and strips it of operative rules;
- replaces baseline/amendment “acceptance” simulations with literal baseline-anchor mappings.

## Nonclaims

- No FAR-CORE claim, premise, theorem, W1-W6 result, independence status, novelty status, external-validity status, or commercial-readiness status changes.
- FARA primitive/minimality questions remain separate.
- EFR and #518 remain unexecuted by this campaign.
- The Lean finding does not establish that any governed FAR proof is invalid.
- No customer utility, competitive moat, or global saturation is demonstrated.

## Artifacts

- `findings-v1.0.json` — source-bound dispositions and literal baseline mappings.
- `counterexamples-v1.0.json` — 25 attack/control fixtures bound to baseline anchors.
- `source-receipts-v1.0.json` — bounded content receipts for mutable Lean sources.
- `replication.md` — reconstruction, source-freeze, and hostile-review record.
- `docs/architecture/saturation-baseline-v0.5-amendment-a1.md` — withdrawn non-operative tombstone preserving the rejected intermediate repair.
- `tests/test_saturation_falsification_001.py` — regression checks that each mapped anchor literally exists in frozen v0.5 and no operative amendment/status promotion survives.

## Acceptance rule

This reconstruction is candidate material until the exact branch head passes the repository's required protected validation. Green CI is necessary but not sufficient for scientific acceptance; a reviewer should still challenge whether each cited baseline surface genuinely preserves the decision-relevant distinction.
