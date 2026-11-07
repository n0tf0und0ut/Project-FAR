# FAR-MAS-MATCHED-002 — prospective matched-parameter replication

**Status: Research / frozen design / NOT YET EXECUTED at this commit.**

## Why this experiment exists
The completed MAS v0.1 pilot selected two stacked attention blocks but compared it against smaller single-block candidates. The model-capacity confound prevents isolating the effect of architectural depth. This follow-up attempts to falsify that pilot's apparent advantage. It is not another neural-architecture-discovery campaign.

## Frozen inputs and identity
- Exact model source: `tools/model_architecture_search.py`, SHA-256 `05310a91107286502e2afa55cae42c32719d408683583e6c3a0fe5b501464104` (unchanged v0.1 source).
- Exact v0.2 runner: `tools/model_architecture_replication.py`, SHA-256 `eb974a6047b8bedc50e30134b4ce07891fc47c4d579e4b221e581f41773de519`.
- Experimental contract: `protocol-v0.2.json`, SHA-256 `293f97fc61e6b6a84943a6b2127c16b1f30df3ef47e495a9a31a45df19bfbe19`.
- The source, tests and frozen contract were committed to the existing research branch before any scored v0.2 execution.
- Established prior art: AlphaEvolve (https://arxiv.org/abs/2506.13131), AgentNAS (https://arxiv.org/abs/2607.07984), SPARK (https://github.com/AIM-ResearchLab/SPARK). Their authors' larger evaluations are separate; FAR has neither independently replicated nor matched them.

## Comparators and design
The candidate is two causal attention blocks, hidden width 16. The three alternatives are a single causal attention block, a single GRU block and a single causal convolution block. Their hidden widths are selected deterministically to minimize the absolute parameter-count difference from the candidate. Parameter counts must be within 5% and are reported. This improves on v0.1 but does **not** equate FLOPs, wall time, optimization ease, or inductive bias.

Two disjoint binary input lengths, 15 and 17, are trained **from scratch**; the study does not test out-of-distribution length extrapolation of one trained model. The three original deterministic tasks remain: first-bit recall, XOR endpoints, and majority. For each length there are 2,048 unique train inputs, 512 unique validation inputs and 1,024 unique held-out test inputs, sampled deterministically from a separately pinned data seed. No within-length split repeats. The tasks remain synthetic and authored by FAR.

Training: two predeclared budgets of 120 and 240 AdamW steps, batch size 64, common learning rate 0.004, deterministic PyTorch CPU one-thread execution. Five fixed paired initialization/minibatch seeds (3101–3105). Total **80** scored runs: 2 lengths × 2 budgets × 4 architectures × 5 seeds. Every condition must execute and be retained, even if the hypothesis fails. No replacement trials, changing thresholds, or winner reselection after observing test data.

### Primary preregistered falsification screen
For length 15 at 120 steps, compare stacked attention with the capacity-matched single wide-attention model, seed-for-seed. A directional internal screen passes only if all of:
1. Mean held-out macro-accuracy advantage of stacked attention is at least **2 percentage points**.
2. At least **4/5** matched seeds favor stacked attention.
3. No individual task family is worse by more than **5 percentage points** on mean accuracy.

The 240-step budget, length-17 tasks, GRU and convolution are secondary/exploratory controls; they cannot rescue a failed primary screen. The screen is a predeclared engineering threshold, **not** a statistical population inference or scientific acceptance rule.

## Evidence preservation and stopping
A write-once JSON report records every evaluated model, true/returned per-case predictions (packed bits), task-level scores, loss, parameters, model-state fingerprint, budget, seed, elapsed time, source/protocol/environment identity, and analysis. The separate append-only journal records request/start/completion of all 80 slots. The verifier reconstructs splits and scores from predictions and checks complete run coverage, model identity, condition order and journal; optional exact-inference replay retrains every model and compares its state digest and predictions on the local environment. Report hashes detect accidental corruption and are not independent cryptographic attestations by an external observer.

Any runner failure must produce FAILED_OR_INCOMPLETE with the completed prefix; infrastructure errors cannot be reinterpreted as model failures or omitted. Only genuinely fresh preregistered replication versions may be run after this trial. No accepted theory, production FAR logic or unbounded reliability/novelty claim changes.

## Independent acceptance boundary
Even a successful result establishes only an authored binary task comparison with tied parameter counts and fixed training budgets. External datasets, independent evaluators, compute matching, stronger architectures, multiple model scales, cross-hardware replication, and exact-head substantive review remain separate obligations.
