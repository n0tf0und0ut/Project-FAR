# FAR-AGENT-ALPHAXIV-001 — 2026-11-20 source-access execution record

**Status: RESEARCH; FAILED_SOURCE_INTAKE; no cohort selected; not an executed scientific comparison.**

The registered metadata source was `alphaXiv/AgentAlphaXiv@a63f46066ac16fcb470f41933415e175825b6bcc`, expecting 961 studies and 926 `in_paper_cohort` records. This exact registration is preserved and was **not** silently changed.

## Reproducible read-only attempts

- GitHub Actions run 44744341908, `metadata-only-intake` job 136315638620, head `97d537b5bff849467038f615801de14222995ed8`: all six synthetic intake tests passed; pinned `datasets==4.4.1` installed; original pinned dataset failed with `FileNotFoundError: ... @a63f46066ac16fcb470f41933415e175825b6bcc/data/studies.parquet (revision not found)`. No manifest produced. https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44744341908
- GitHub Actions run 44744679448, `metadata-only-intake` job 136316817298, head `93eb3bec0b7e135d67571d2b10495d259ea89eaf`: original registered revision returned `RevisionNotFoundError: 404` via `HfApi.dataset_info`. The observation-only current branch returned SHA `cc892aab131be3872283e1a778af663382315817`, 916 studies, 881 `in_paper_cohort` records. Subsequent registered-revision intake failed as expected. https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44744679448

## Adjudication boundary

The original source revision is not accessible to unauthenticated GitHub-hosted execution at the observed timestamp. This is an availability limitation, not proof of invalid research, and is not permission to reconstruct removed records or read withdrawn contributions. The change from 961/926 to 916/881 is observed, but its causal explanation was not established by these commands. Web-indexed copies of the earlier card are not substitutes for original dataset bytes.

**Outcomes for study 001:** selected 0/60, eligible source cases 0, independently sealed cases 0, paired comparator runs 0, FAR runs 0, confirmed scientific defects 0. Study 001 stops at source intake. To use currently accessible data requires a separately identified candidate with independently defined source, denominators, contract and prospective seal; never promote this attempt to successful external validation.
