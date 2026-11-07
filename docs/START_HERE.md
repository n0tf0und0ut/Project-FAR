# Project FAR in five minutes

This is a first introduction for people who have never studied computer science or formal logic. It explains the *idea* using an invented example, not a real investigation or a new scientific result. The [project overview](OVERVIEW.md) and [current project status](project-status.md) lead to the precise technical sources.

## Why would anyone care?

A short description can leave out something important. But what counts as important depends on the question we want to answer.

FAR studies how to specify those questions precisely, describe information explicitly, and check whether a way of representing it loses a distinction that matters for the chosen question. It does not decide what matters for every possible question.

## One everyday example: two receipts

Imagine two receipts from a shop:

| Receipt | Items before tax | Tax charged | Total paid |
|---|---:|---:|---:|
| A | $20 | $0 | $20 |
| B | $18 | $2 | $20 |

**Step 1 — Keep only the totals.** Our short description of both receipts is *$20*. We have combined two different receipts into the same description.

**Step 2 — Decide what question we need to answer.** If the question is "How much did the customer pay?", the short description is enough: both answers are $20.

**Step 3 — Ask a different question.** If the question is "How much tax was charged?", the same short description fails. Receipt A needs the answer $0, while receipt B needs $2. Both still look like "$20" in the shortened version.

**Step 4 — Keep what that question needs.** A description that also records the tax amount now distinguishes the two receipts. This does not make it the best description for *every* question.

The key idea is simple: **a summary can be good enough for one question and inadequate for another**. FAR's formal theory expresses and checks a precise version of this idea under declared conditions. See the [governing theory](../theory/theorems/Project-FAR-Theory-Closure-v1.1.md).

This receipt example is fictional and worked out by hand. It is **not** a claim that FAR software processed actual receipts, confirmed tax amounts, or detected a real error.

## What FAR can do — and what it cannot promise

| What exists or is established within a stated scope | What that does *not* establish |
|---|---|
| Formal results describe when information preserves what a specified comparison requires. | That there is one perfect way to represent all reasoning or answer every question. |
| Software can check certain explicitly supplied, finite comparison records using declared rules. | That it can independently read any story, judge witnesses, or establish whether real-world evidence is true. |
| Recorded mathematical and software checks can be inspected and repeated under their assumptions. | That FAR has proved a general advantage over ChatGPT or other AI systems, or that its usefulness has been independently validated for everyday decisions. |

These are deliberately different kinds of claims. See the [claim/evidence matrix](governance/w1-w6-claim-evidence-matrix-v1.0.md), [project status](project-status.md), and [limitations register](governance/limitations-register.md) for the authoritative boundaries.

## Why not just ask ChatGPT?

ChatGPT can explain a claim or summarize documents. A fluent explanation by itself, however, does not specify which distinctions a summary must preserve or demonstrate that they were checked.

FAR's research framework makes the comparison requirements explicit and provides scoped ways to inspect whether a supplied representation meets them. That is a difference in *method*, not evidence that FAR generally produces truer answers or better decisions than ChatGPT.

## What can I actually try today?

For someone comfortable running Python, the repository includes registered machine-readable examples and a verifier. From the repository root, a documented check is:

```bash
python -m mechanization.far_mechanization.contract_conformance --manifest conformance/far-ir-2.0-current/manifest.json
```

This checks the registered conformance examples, **not** the fictional receipts above or arbitrary claims you paste into a chatbot. The [mechanization guide](../mechanization/README.md) describes the checks and their limitations. No general-purpose consumer fact-checking product is established by these tests.

## Where to go next

- **Just curious?** Read the [short project overview](OVERVIEW.md) or try explaining the receipt example to someone else.
- **Want to run or modify code?** Use the [contributor guide](../CONTRIBUTING.md) and [mechanization guide](../mechanization/README.md).
- **Want the science and evidence?** Start with [project status](project-status.md), then the [canonical map](CANONICAL_MAP.md) and [governing theory](../theory/theorems/Project-FAR-Theory-Closure-v1.1.md).

A [nontechnical reader check](maintenance/beginner-comprehension-check.md) explains how to see whether this introduction actually communicates its intended meaning. It has not been presented as a completed human study.
