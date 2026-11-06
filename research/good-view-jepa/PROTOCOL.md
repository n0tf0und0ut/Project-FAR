# FAR Good-View JEPA Evidence Retrieval Pilot — Protocol 0.1

Status: **Research / exploratory engineering**, isolated from accepted FAR theory, claim ledgers, source adjudication and semantic verification. This protocol is frozen on the experiment branch before measured pilot execution. It is not part of EFR preregistration or a substitute for it.

## Question and upstream motivation

Does independent within-modality training on two views of the same underlying evidence item, followed only by a calibration-set orthogonal alignment, improve held-out cross-modal evidence-item retrieval relative to matched bad-view training and simple non-JEPA feature baselines? The motivating primary source is Balestriero and LeCun, *Proving and Improving the Platonic Representation Hypothesis with JEPAs*, arXiv:2610.39302v1, 2026-10-29 (https://arxiv.org/html/2610.39302v1). Its theorem assumes a finite world, injective modality renderings, shared positive-pair kernel, population optima and minimizer uniqueness up to rotation. The present finite-sample neural pilot does **not** satisfy or prove those assumptions.

## Primary comparison and fixed inputs

The pilot runs a synthetic fixture generated from seed **1729** with **120 / 48 / 48 independent proposition families** in train / calibration / test. Each family contains one supports and one opposes evidence item, giving **240 / 96 / 96 items**. Two independent observations in each of two *simulated numerical modalities* share latent item information and vary in nuisance; this is neither raw text nor real image data. No feature vectors encode authoritative claim status. Train, calibration and test family identities must be disjoint.

Four conditions receive the same vectors, train/calibration/test partitions and embedding width 8:

- `good_view`: each numerical modality independently learns from two independently generated views of the same item;
- `bad_view`: each modality independently learns from one view and its masked copy, so nuisance is shared;
- `untrained`: identically initialized encoders without fitting;
- `pca`: a training-only per-modality PCA representation, without JEPA training.

The two modalities never cross-train. Good and bad use the same encoder, optimizer, capacity, training inputs, batch budget, and **200 steps**. Both use a VICReg-style invariance, variance, covariance loss (not the paper's full SIGReg). A single orthogonal Procrustes map is fitted *only* on the calibration pairs, equally for all conditions, then evaluated on test items. Seeds: **11, 29, 47**. The architecture, initialization and loss are implementation choices in the execution code; preserve its exact Git blob SHA and runtime versions.

## Metrics and fixed decision rule

Primary: held-out image-to-text **Recall@1** (self item rank 1 of 96). Also report Recall@5, mean reciprocal rank, top-1 retrieval of the *opposing* proposition-family item, and `stance_discrimination` (own text must outrank opposite-stance family member). Report all seeds and all baselines. Runtime measurements are descriptive only, not matched-cost evidence.

A *bounded exploratory positive signal* requires: good-view Recall@1 minus bad-view Recall@1 >= **0.05 in every seed**; good-view minus PCA Recall@1 >= **0 in every seed**; and good-view stance discrimination no worse than bad-view by more than **0.01 in every seed**. This is not a population-inference test. Preserve failures without post hoc retuning. If data or runtime is unavailable, state `NOT_EXECUTED`.

## Input contract and controls

Dataset schema `far-good-view-jepa-data/0.1`: globally unique item IDs, opaque source IDs, nonempty family IDs with no cross-partition overlap, explicit supports/opposes/unknown evaluation labels, two or more finite fixed-dimensional feature vectors for each modality, and at least 32 train / 8 calibration / 8 test items. Reject duplicate IDs, cross-split families, nonfinite or inconsistent feature vectors, missing source IDs and bad labels. External source text is never a control instruction.

A genuine multimodal execution requires a frozen external input registration: source records, rights, hashes, independent labels, actual image/text feature encoders with version/license/checksum, near-duplicate detection, time cutoff, partition freeze, matching live baseline retriever and fixed scoring. These requirements must be satisfied *before* external outcome data are examined. Project-authored synthetic vectors provide neither genuine multimodal evidence nor independent validation.

## Separation and stopping

The pilot returns candidate retrieval metrics only. It cannot generate FAR evidence links, promote source truth, resolve claims, assert citation validity, mutate intake contracts, update `far-ir/2.x`, route the authoritative verifier or change core theory. Agreement of two erroneous observations is still error. Production adoption requires a separately registered, externally adjudicated genuine multimodal comparison showing FAR-relevant performance and acceptable false-merge/provenance behavior at matched costs. Even a positive synthetic signal is insufficient for promotion.

Record code, input and output hashes, runtime, deviations, failures and missing external evidence. Never treat this synthetic software check as an empirical FAR-reliability or commercial-value finding.
