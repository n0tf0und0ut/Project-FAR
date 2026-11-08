# FAR Decision Integrity — Commercial pilot validation

Status: **commercial planning hypothesis**, not Accepted FAR science, executed research, buyer evidence, certification, or a statement of current revenue.

## Why this product

Build the first commercial offer around existing `far-decision-integrity` behavior. Its decision-package validator classifies **disclosed** structures, dependencies, contradictions, unknowns and (when explicitly supplied) governed semantic contracts. It cannot recover concealed reasoning, establish external factual truth, or certify compliance. The purpose of a customer pilot is to test whether those bounded checks deliver incremental value under a real buyer's workflow.

## Customer and qualification

Initial hypothesis: enterprise AI engineering and model-risk teams that already review structured AI-generated decisions. Qualify prospects only if they (a) own a recurring decision-review workflow, (b) can lawfully furnish test cases, (c) can explain current review errors and costs, (d) identify the budget holder, and (e) can supply an existing comparator and independent adjudicator.

## Pilot offer (unvalidated)

- Proposed **$5,000**, **three weeks**, at most **30 eligible structured decision packages**. Scope, fee and delivery economics are negotiating hypotheses; no sales or commitments are represented here.
- Buyer supplies lawful, appropriately redacted packages, a comparator workflow, explicit decision criteria, and blinded outcome adjudication. Do not accept sensitive, regulated or production credentials until data-handling and contract obligations are verified.
- FAR supplies input-integrity checks, per-case structural adjudication, explicit semantic-contract checks where records meet canonical verifier requirements, error traces, reproducible report files and a comparison summary.
- Evaluate FAR against the buyer's **active baseline**, not against an unevaluated or intentionally weak control. Match tasks and adjudication standards; preserve all invalid, missing and negative cases.
- **Outputs:** case-level status and findings, source/contract identities when applicable, time and direct cost measured for both workflows, incremental actionable defect count, false approvals/blocks, and unresolved limitations.
- A buyer decision is based on **verified incremental value**, net of setup, human review and integration cost. The pilot is not an estimate of population superiority or an external independent replication of `EFR-001`.

## Operating sequence and measurable gates

1. **Product intake:** require malformed, duplicate-key, non-finite and overflow JSON to fail closed. Test installability, both demonstration packages, the CLI, and report reproducibility. Verify canonical semantic routing separately.
2. **Founder use:** exercise the package on actual self-owned decision records; log failures and user effort. Improve only defects or friction supported by that use.
3. **Customer discovery:** pursue 15 substantive interviews from a qualified prospect pool. Record workflow, comparator, spend, purchaser, refusal reasons, and source consent. Interviews are evidence of the problem, not of purchase intent.
4. **Commercial conversion:** propose paid pilots only where the buyer has a meaningful comparator and usable cases. Track opportunities, actual signed contracts, invoices, receipts, time/cost and renewals; do not substitute expressed interest for a sale.
5. **Pilot evaluation:** do not claim a FAR-specific benefit from merely comparing with a no-tool workflow. Independently adjudicate disagreements and retain complete run artifacts, including false positives and failures.
6. **Expansion gate:** seek three independent paying customers and two continuing paid relationships. These are **targets, not predictions**. Revise pricing and product scope from observed unit economics.
7. **Funding gate:** pursue capital only with credible buyer evidence, documented rights to commercialize the relevant IP, and a cash model derived from observed acquisition, delivery, and retention.

## Failure and stopping conditions

Stop commercial superiority claims if no meaningful gain over the buyer's active comparator is established. Stop external pilot intake on unresolved critical input-integrity, provenance, access-control or data-handling defects. If no independently evidenced buyer pain or willingness to pay appears after sufficient qualified outreach, narrow or abandon the proposed offer instead of broadening claims or building speculative features.

The current research program `EFR-001` has distinct preregistration, external-participant and promotion gates. A commercial pilot must never be counted as satisfying `EFR-001` without separate governance and evidence.

## Demonstration

From a Project FAR checkout, with the commercial package installed:

```bash
python -m pip install ./commercial/far-decision-integrity
far-decision commercial/far-decision-integrity/examples/clear-package.json
far-decision commercial/far-decision-integrity/examples/contradicted-package.json
```

The **synthetic** first package returns `justified` (exit code 0) under its disclosed non-semantic structural checks. The second returns `unsupported` (exit code 30) because its disclosed evidence node is marked `contradicted`. Neither result verifies any external-world assertion. With `--require-semantic-contract`, the clear package instead returns `unverifiable` (exit code 32) because it lacks a decision-gating semantic contract.

See the package README and canonical project-status / limitations registers for claim boundaries.
