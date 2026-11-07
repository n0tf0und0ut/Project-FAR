# Beginner comprehension and navigation check

Status: **Documentation usability procedure only.** This document does not define FAR theory, prove scientific results, or claim that a human usability study has already been performed.

## Purpose

Determine whether readers unfamiliar with FAR can understand the [five-minute introduction](../START_HERE.md) **in their own words** without learning scientific vocabulary. The goal is accurate comprehension, not passing a technical quiz.

## How to conduct a first pilot

Invite several readers who have not worked on FAR and have no assumed background in science or software. Six to eight different readers are a practical **discovery pilot**, not a representative sample or proof of accessibility. Ask permission to take anonymous notes; do not collect names, private history, or identifying details.

Record the exact guide version/commit and whether the reader has encountered FAR before. Give the reader the introduction without coaching, definitions, or examples beyond those printed on the page. Allow roughly five minutes to read; let readers take longer without treating reading speed as failure.

Ask these prompts as an ordinary conversation, not a written exam:

1. **Explain:** "How would you explain FAR to a friend who has never heard of it?"
2. **Apply to a different situation:** "Two train tickets both cost $15. One train arrives at 8 a.m., the other at 2 p.m. An app shows only the prices. Is that screen enough to compare what the tickets cost? Is it enough to tell which train arrives before a 10 a.m. appointment? What would you need to see?"
3. **Limits:** "Would using FAR automatically mean you have the correct answer? Why or why not?"
4. **What exists today:** "Do you think FAR is already a tool that can check any news story for you, or does the repository currently offer something more limited? What makes you think so?"

For the train example, do not first explain the answer. A reader who understands the relevant difference should say **yes** to comparing listed prices ($15 versus $15), but **no** to determining which train arrives before 10 a.m. without the arrival-time information. They need not use those exact words. Merely saying "details matter" does **not** demonstrate that the same abbreviated information works for one question and fails for another.

If they naturally raise a question, let them ask it. Do not require specific words such as *contract*, *representation*, *factorization*, or *quotient*. Do not introduce those terms as hints. Do not reward repetition of the guide's wording without demonstrated meaning.

For an optional **navigation** check, ask them to locate (a) the current limitations and (b) instructions for running existing code. Observe where they click and whether they can find the destination without being told which link to choose.

## What to observe

| Observation | Clear understanding | Misunderstanding worth fixing |
|---|---|---|
| What FAR is about | Describes information loss or important distinctions depending on a question, using ordinary words. | Says FAR automatically determines truth, reads minds, or solves every reasoning task. |
| Application to a new question | Says listed prices suffice to compare price but cannot establish arrival before 10 a.m.; identifies arrival time as the missing detail. | Gives the same yes/no answer for both questions, or repeats only that details matter without explaining the difference. |
| Limits | Recognizes that the method does not guarantee that the starting evidence or conclusion is correct. | Assumes FAR makes arbitrary AI answers correct or independently verifies every real-world fact. |
| Actual availability | Identifies limited runnable checks over prepared records, not general news checking or a consumer product. | Confuses the fictional receipt walkthrough or registered toy fixture with a deployed general fact-checking service. |
| Navigation (optional) | Finds limitations and executable guidance unassisted. | Cannot locate those pages or interprets an index as an assurance result. |

Record each item as **clear**, **partial**, **misunderstood**, or **not observed**. A general statement that "missing details can change decisions" is insufficient for a **clear** mark on the transfer question if the reader cannot distinguish the two different questions about the same price-only screen. Do not equate recognition of an example with evidence of FAR software correctness. Record the reader's own phrasing and, when identifiable, the sentence or link that caused confusion. Do not assign numerical passing grades or treat fast completion as evidence of scientific comprehension.

## Recording and revision

For each reader, note an anonymous session code, tested commit, the explanations in their own words, any incorrect expectations, links attempted, help required, and actionable wording problems. Keep raw notes private as appropriate; publish only de-identified, authorized observations. Never manufacture participants or outcomes.

If a reader leaves believing FAR guarantees truth, has proved general superiority over other AI systems, or ships an unrestricted fact-checking product, treat that as a substantive **documentation failure to investigate**, even if other answers sound correct. Revise the smallest misleading passage, check the revision against [current project status](../project-status.md) and [canonical boundaries](../CANONICAL_MAP.md), and repeat with *new* uncoached readers.

Static checks can detect broken links and malformed Markdown; they cannot prove that people understand a page. An internal editorial review is not an independent reader study. Report pilot observations and limits separately; do not claim a universal comprehension rate from a small or convenience sample.

The normal documentation checks are described in [repository health checks](repository-health-checks.md).
