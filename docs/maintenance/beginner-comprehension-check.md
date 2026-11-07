# Beginner comprehension and navigation check

Status: **Documentation usability procedure only.** This document does not define FAR theory, prove scientific results, or claim that a human usability study has already been performed.

## Purpose

Determine whether readers unfamiliar with FAR can understand the [five-minute introduction](../START_HERE.md) **in their own words** without learning scientific vocabulary. The goal is accurate comprehension, not passing a technical quiz.

## How to conduct a first pilot

Invite several readers who have not worked on FAR and have no assumed background in science or software. Six to eight different readers are a practical **discovery pilot**, not a representative sample or proof of accessibility. Ask permission to take anonymous notes; do not collect names, private history, or identifying details.

Record the exact guide version/commit and whether the reader has encountered FAR before. Give the reader the introduction without coaching, definitions, or examples beyond those printed on the page. Allow roughly five minutes to read; let readers take longer without treating reading speed as failure.

Ask these prompts as an ordinary conversation, not a written exam:

1. **Explain:** "How would you explain FAR to a friend who has never heard of it?"
2. **Apply:** "Can you think of a situation where leaving out an important detail could change someone's conclusion?"
3. **Limits:** "Would using FAR automatically mean you have the correct answer? Why or why not?"

If they naturally raise a question, let them ask it. Do not require specific words such as *contract*, *representation*, *factorization*, or *quotient*. Do not introduce those terms as hints. Do not reward repetition of the guide's wording without demonstrated meaning.

For an optional **availability** check, ask: "What, if anything, could you actually try from this repository today?" For an optional **navigation** check, ask them to locate (a) the current limitations and (b) instructions for running existing code. Observe where they click and whether they can find the destination without being told which link to choose.

## What to observe

| Observation | Clear understanding | Misunderstanding worth fixing |
|---|---|---|
| What FAR is about | Describes information loss or important distinctions depending on a question, using ordinary words. | Says FAR automatically determines truth, reads minds, or solves every reasoning task. |
| Application | Recognizes an analogous everyday situation and explains the missing detail. | Cannot connect the idea to another situation or confuses it with checking whether the original facts are true. |
| Limits | Recognizes that the method does not guarantee that the starting evidence or conclusion is correct. | Assumes FAR makes arbitrary AI answers correct or independently verifies every real-world fact. |
| Availability (optional) | Distinguishes a bounded runnable check from an everyday consumer product. | Assumes the demonstration receipt example is a working receipt-auditing application. |
| Navigation (optional) | Finds limitations and executable guidance unassisted. | Cannot locate those pages or interprets an index as an assurance result. |

Record each item as **clear**, **partial**, **misunderstood**, or **not observed**, with the reader's phrasing and the confusing sentence or link when identifiable. Do not assign numerical passing grades or treat fast completion as evidence of scientific comprehension.

## Recording and revision

For each reader, note an anonymous session code, tested commit, the explanations in their own words, any incorrect expectations, links attempted, help required, and actionable wording problems. Keep raw notes private as appropriate; publish only de-identified, authorized observations. Never manufacture participants or outcomes.

If a reader leaves believing FAR guarantees truth, has proved general superiority over other AI systems, or ships an unrestricted fact-checking product, treat that as a substantive **documentation failure to investigate**, even if other answers sound correct. Revise the smallest misleading passage, check the revision against [current project status](../project-status.md) and [canonical boundaries](../CANONICAL_MAP.md), and repeat with *new* uncoached readers.

Static checks can detect broken links and malformed Markdown; they cannot prove that people understand a page. An internal editorial review is not an independent reader study. Report pilot observations and limits separately; do not claim a universal comprehension rate from a small or convenience sample.

The normal documentation checks are described in [repository health checks](repository-health-checks.md).
