# Bounded live autonomous FAR investigation — preregistration v0.1

**Status: Research, before live workflow execution.** This protocol adds *actual* source retrieval, contract discovery/freeze, semantic verifier calls and aggregation to the earlier routing-only pilot. It does not promote a new FAR Core theorem.

## Falsifiable target

Input: `Is the latest release tag of n0tf0und0ut/Project-FAR v1.0.0?`. Two materially plausible operational readings of "latest" are retained: the tag at GitHub's `/releases/latest` endpoint, and the first tag at `/releases?per_page=10` (not guaranteed to coincide). This is a bounded GitHub-API metadata inquiry, not a proof about the whole software publishing ecosystem or current GitHub UI.

## Actual permitted tools and containment

Two allowlisted HTTPS GitHub REST sources are fetched with a fixed repository identity and strict JSON parsing. The terminal bounded saturation pass *refetches both* and compares semantic release-tag/ID projections, failing closed on drift. Raw response bytes, SHA-256, exact URL, timestamps and all actions are kept in run artifacts (no API secrets). No arbitrary browsing, shell commands, writes to GitHub, or prompts supplied by external content are executable. Network and API errors block verdicts.

The accepted `far-intake/1.0` implementation builds a complete two-member candidate family from two interpretations, records source/term/parameter provenance, performs a recorded bounded final zero-new scan, then freezes before evaluating. The current `far-ir/2.0` v1.1 verifier checks a finite reduction: whether a constant representation factors the literal claimed tag and the observed source tag. This mathematical check is equivalent to equality of the two recorded tag values. It **does not independently authenticate GitHub's claims**; output must say "within the retrieved bounded source snapshot." Each candidate's post-freeze verifier record is bound to its frozen contract hash. `aggregate_manifest` computes a cross-contract verdict; divergent source projections produce `CONTRACT_SENSITIVE`.

## Router comparison

The fixed arm executes a deterministic state machine. In the model-proposal arm, the pinned CPU model proposes the next action from a supplied live list of eligible actions. A typed guard rejects unavailable or unsafe actions and records deterministic controller fallback, including reasons, so completion cannot be misattributed to agent initiative. The same model identity/quantization pin as prior uncertain-choice pilot is used. Both lanes must perform real source retrieval, freeze, and verifier calls; a model that loops on clarification or invalid choices has no demonstrated autonomous planning ability.

## Primary observations

Count real HTTP response receipts, source rechecks, frozen candidate count, verifier calls, completed stage transitions, source drift/rejections, terminal status, model suggestions, controller interventions, inference tokens, elapsed time and semantic outcomes. Run mock-network adversarial tests and pinned real GitHub Actions workflow. Preserve results in Research; no market, general reasoning, open-domain autonomy, or independent source-reliability inference.

Failure is recorded and kept as an outcome. A successful *bounded* investigation is not a complete general-purpose epistemic debugger or a verified commercial advantage.
