# Live commercial access and evidence-retrieval comparison

Status: **Research; project-controlled exploratory observations.** Baseline: protected main `38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab`. User authorization: execute live commercial comparisons and determine customer value and general reasoning reliability. The desired conclusion is not an experimental acceptance criterion.

**Result: live retrieval was executed, but customer value, commercial superiority and general reasoning reliability were not established.** The closest document-analysis competitors require authentication. Connected literature products support a narrower comparison; they cannot stand in for those competitors' argument-analysis workflows.

## Observed results

| Configured endpoint | Actual execution | Frozen target full-title presence | Frozen target DOI presence | Scope |
| --- | --- | --- | --- | --- |
| SciSpace paper search | Four successful live queries | 1/4 payloads | 1/4 payloads | Literature discovery, not verification of an argument |
| Consensus search, initial concurrent batch | One response; three rate-limit errors | 1/1 returned payload | 0/1 returned payload | Failed requests remain missing, not incorrect answers |
| Consensus search, sequential successor | Four successful live queries | 2/4 payloads | 0/4 payloads | Unchanged queries; all earlier errors retained |
| FAR default local raw-document workflow | 16 reasoning documents and the same four retrieval questions; 20/20 packages replay | Not a configured literature-search arm | Not a configured literature-search arm | 42 sentence candidates, all `NOT_ESTABLISHED`; 13 inference candidates, all `NOT_CHECKED_UNFORMALIZED` |
| RoastMyPost hosted fallacy extractor | **NOT EXECUTED** | Not applicable | Not applicable | Live `/tools/fallacy-extractor/try` displayed “Authentication Required” |
| Fact Engineering hosted document check | **NOT EXECUTED** | Not applicable | Not applicable | Live sign-in requires email or Google authentication |

The secure Fact Engineering sign-in request was rejected by automatic approval review: the intended account was not identified or explicitly authorized. No credentials were entered and no alternate sign-in route was attempted. Resuming that arm requires the user to identify the account and authorize its use. `authentication-incident-v1.json` preserves the rejection separately from product performance.

Literal target presence was fixed before execution. It is not full relevant-paper recall, factual accuracy, citation support, source applicability or downstream reasoning quality. A returned secondary paper may be useful even if the designated original is missing. Different metadata formats can omit a DOI without missing the paper. No rank or superiority claim follows from these counts. The Consensus sequential response contained the target originals as paper records for Q02 and Q03; their separate post-search fetches are preserved in `metadata-verification/` and do not change the original scores.

The sequential run's measured request times were 4.398, 3.420, 1.703 and 3.812 seconds. SciSpace's were 5.734, 7.156, 6.753 and 5.796 seconds. These are isolated connector observations including service and transport time, with differing output capabilities; they are not customer time savings. Per-call dollar charges, operator effort and fully attributed cost remain unknown. No purchase was made.

## What this says about FAR

The exact raw texts include valid and invalid deductions, altered quantifier meaning, unsupported intent attribution, an arithmetic error, temporal ineligibility, duplicated reporting origins, normative premises, unsupported confidence, qualified expert testimony and quotation of a fallacy. They are synthetic developer-authored cases with implementation exposure, not independent or representative gold.

FAR received the raw text and **no exclusive formulas, semantic labels or cognitive coding**. Its default heuristic path made no decisive inference judgment on these inputs. Package replay establishes artifact consistency; it does not make the interpretation or conclusion correct. These results therefore do not establish an autonomous epistemic debugger capable of reliable general document investigation. FAR-COG's structured-coding checks and the bounded logic engine retain their existing, narrower scopes.

No full configured retrieval ranking against FAR is reported: this FAR arm deliberately records the installed default without a search provider or model proposer. A configuration gap cannot be converted into a claim about every supported FAR configuration. Likewise, unexecuted hosted competitors are neither losses nor wins.

## Customer-value finding

This campaign observed **zero actual customer task sessions, zero measured purchase decisions and zero retention outcomes**. Customer value is **NOT ESTABLISHED**, not valued at zero dollars. There is no basis to infer willingness to pay, reduced reviewer labor or a competitive moat from these runs.

The required next evidence is a configured matched workflow on identical raw inputs, followed by actual user task completion and correction measurements. Record active reviewer time, consequential false acceptance/rejection, useful coverage, evidence repair burden, total cost and actual paid or repeated use. Keep neutral/null/adverse outcomes. The frozen raw cases are ready to submit after hosted access is available. Authentication alone will not establish customer demand. No evaluators were contacted, no EFR inputs or frozen #518 cases were executed, and no scientific or commercial claim was promoted.

## Integrity and limitations

- `registration-v1.json` content-addressed the cases, protocol, evaluator, evaluator tests, Crossref identity receipts and all investigation runtime Python files before the first prediction. Local pre-execution commit: `94f4adc4`. Initial direct Git transport could not authenticate; GitHub publication happened later through the connected API. This is a local prospective internal freeze, not public pre-execution preregistration or an independent seal.
- Four target-paper identities were checked against Crossref metadata before freezing. This verified identity only, not the papers' experiments, reproducibility or correctness.
- `summary-v1.json` and all eight original response/error receipts are unchanged. Three concurrent Consensus calls returned rate-limit errors. `sequential-successor-registration-v2.json` prospectively registered four additional calls with the same inputs and scorer. All four sequential calls succeeded. This observation does not isolate the causal reason for the initial errors.
- The returned service/model/deployment versions were not pinned or exposed. Results are timestamped observations of hosted endpoints. No extrapolation to later versions or unrestricted reliability is authorized.
- Raw responses are archived, including provider limitations, errors, metadata and source links. They are evidence of what the endpoint returned, not independent truth. Search output is not an external adjudicator.
- No original case/reference bytes or runtime behavior changed after freezing. Earlier internal and cognitive results remain intact. This campaign does not repair the previously demonstrated semantic-fidelity gap.

## Replay

The evaluator contains no provider API or credential code. Live searches were invoked through the existing connected product tools. Repeating them requires those connections and a **new registered run**; hosted outputs need not be deterministic.

```bash
python -m unittest discover -s tests -p test_live_commercial_evaluation.py -v
python tools/run_live_commercial_evaluation.py check
python tools/verify_live_commercial_evaluation.py
```

The post-execution verifier checks the artifact inventory, recomputes all twelve original/successor receipt scores and replays the archived FAR packages. It adds no live predictions or new effectiveness endpoint.

`far-deliveries-v1.zip` contains the exact requests and twenty complete FAR packages. Its SHA-256 is `01ecf840e8236e666e126e1d77ea7e3e8c045bedaf62e276792d6af25b181dda`. Extract into a new scratch directory and run `commercial/far-investigation-audit/full_cli.py --verify <package-directory>` on each package. Do not overwrite the recorded campaign or rerun its write-once output names.

Machine results: [initial summary](summary-v1.json), [sequential successor](sequential-summary-v2.json), [local FAR results](far-results-v1.json), [protocol](protocol-v1.json), [cases](cases-v1.json). The shared research register is unaffected: these are new evaluation results, not newly Accepted theory.
