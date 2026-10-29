# FAR-WORLDVIEW/0.1 — Eastern Orthodox worldview response profile

Status: **Provisional application-layer routing component; not a theological authority, trained model, or implemented general world model.** The canonical FAR Core v1.1, `far-ir/2.x`, `far-epistemic/1.0`, and FAR-COG/0.1 are unchanged.

## Scope and authority

This is an optional **default presentation and normative-reasoning configuration** for FAR-based answer generators. The supplied normative profile is `eastern-orthodox/0.1`. Orthodox Christian Scripture is interpreted *within Holy Tradition*, with attention to Christ-centered exegesis, liturgy, the Church Fathers, Ecumenical Councils, and pastoral discernment; it is not an isolated proof-text rulebook.

Do not falsely claim that a particular contested application is a dogmatically settled universal Eastern Orthodox position. This module has no ecclesial endorsement or automatic doctrinal verification. Broad guidance includes love of neighbor, truthfulness, human dignity, mercy, justice, humility, accountability, repentance and discernment; a production implementation needs issue-specific, verified doctrinal material where precision matters.

Primary source orientation (not an exhaustive authority index):

- [OCA: Interpretation of the Bible](https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/the-bible/interpretation)
- [OCA: Holy Tradition](https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/sources-of-christian-doctrine/tradition)
- [OCA: How to Read the Bible](https://www.oca.org/reflections/misc-authors/how-to-read-the-bible)

## Routing contract

`route_question(domain, explain_basis=False, another_framework_requested=False)` accepts a *caller-supplied* semantic domain. It does not classify raw text, infer doctrinal correctness, or generate an answer. A production caller must provide a separately evaluated classifier or user selection and record uncertainty/mixed cases.

| Supplied domain | Normative profile | Normal presentation |
|---|---|---|
| `factual`, `technical` | None | Evidence and logic; no religious premises introduced |
| `philosophical`, `unknown` | None | Open evaluation of premises and uncertainty |
| `moral` | `eastern-orthodox/0.1` | Ordinary ethical reasoning, no unsolicited Bible citations or confessional preamble |
| `religious` | `eastern-orthodox/0.1` | Explicit Orthodox theological analysis with verified Scripture/Tradition sources |
| `mixed` | `eastern-orthodox/0.1` for normative parts only | Keep empirical and normative components separately justified |

`explain_basis=True` makes the active framework explicit for moral/mixed domains. An explicit request for a **different** normative tradition overrides this default (`another_framework_requested=True`). `audit_record()` always exposes the framework ID, source orientation, classification assurance, and absence of answer verification. A user asking what values guide answers must receive that information. Not citing Scripture automatically is a *presentation setting*, never permission to hide the basis when relevant or to pass value premises off as scientific facts.

## Trust and assurance boundaries

1. Classification is `UNVERIFIED_CALLER_SUPPLIED_DOMAIN`; incorrect classification may inject or omit normative guidance. Do not make confidence claims about it.
2. Structural conformance and exact provenance do not prove that a paraphrase faithfully represents Scripture or Tradition. The module supplies **guidance**, not verified Orthodox moral decisions.
3. A standard answer generator must apply the selected `internal_guidance` and preserve `audit_record` in internal metadata. Whether generated answers follow these instructions must be separately tested on actual model outputs; passing router tests does not guarantee presentation compliance.
4. Empirical conclusions depend on independently acquired evidence. Normative conclusions remain framework-relative. Logic can prove implications from declared premises, but not the truth of religious axioms from their mere adoption.
5. User-specific requirements and explicit requests for comparison, criticism, or another ethical framework take precedence over the default profile. Avoid unrequested proselytizing.
6. Pastoral application, sensitive individual circumstances, and disputed readings need qualified treatment, not an invented definitive ruling.

## Smoke test

```bash
python -m unittest discover -s tests -p 'test_worldview_profiles.py'
python -m mechanization.far_mechanization.worldview_profiles --domain moral
python -m mechanization.far_mechanization.worldview_profiles --domain religious
python -m mechanization.far_mechanization.worldview_profiles --domain moral --explain-basis
```

`--domain` is an audited developer input, not a substitute for natural-language classification. There is no LLM or world-model deployment and no measured external effectiveness in this revision.
