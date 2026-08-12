# MSO-02B paired prelearning identifiability execution contract

Status: `TARGET_BLIND_AMENDED_AFTER_SOURCE_IMPORT_QA_AND_BEFORE_FIRST_FORMAL_DEFECT_OR_TARGET`.

The original complete contract was frozen at commit
`887d4cdab3dbd9e856e552ff47e50a3cf481d72f` with SHA-256
`44c6588db89568b7990e8804e8017dbd2fc2572c023390e253ad75b2e53bf3b4`
before first reference-source access. Subsequent source-import QA evaluated the
analytical A/B reference paths for 384 frozen states in memory, generated no
formal defect, wrote no target, and inspected no scientific outcome. The
implementation amendments below close target-blind numerical ambiguities after
that QA and before the first formal defect/target generation; they do not use a
target value or H3 outcome. At this amendment, formal defect generations and
formal target-store writes both remain zero.

## Authorization and terminal boundary

MSO-02B is the first formal scientific target experiment in SPH-MSO. It may
generate/read the frozen DDO-compatible analytical continuum reference and the
lambda-one defect, evaluate H3-style identifiability quantities, and fit only
the frozen simple non-neural diagnostic oracle family. It may not instantiate a
deep neural network, attention model, Transformer, learned kernel, learned
operator, optimizer, training loop, time integration, solver-in-loop,
trajectory, rollout, sealed test, or ARC-derived input. Here `DNN` means only
Descriptor Nearest-Neighbour.

The stage stops immediately after the H-MSO-01 verdict and MSO-03 deterministic
closure-baseline eligibility decision. It does not execute MSO-03.

## Immutable Git and evidence handoff

The authorized parent state is local commit
`48fc1b15298948bad9084f4e9b8758965ad84bd2` on `main`, with clean working tree
and no remote. The release-order placeholder in the old MSO-02A manifest is
resolved only by `08_manifests/mso02a_git_handoff.json`; no MSO-00, MSO-01, or
MSO-02A artifact is rewritten.

The following complete-file SHA-256 identities are immutable inputs:

| Frozen input | SHA-256 |
|---|---|
| `08_manifests/mso00_manifest.json` | `c00261aac588f8b1f34e0a606259512ea8d45cf3e9cb0a10f40ab0970a2f7d95` |
| `08_manifests/mso01_manifest.json` | `bf2fad0dfaf03db02d21db30c4f35a145187df557dcd60b26a4e0ee7f5348306` |
| `08_manifests/mso02a_manifest.json` | `c8e8770cda1779041b5b380b7ccec387446c9aa0f82c2b50f4a38655ad968e81` |
| formal 384-case registry | `9893cf48d73be3316a66bb7b9c7f71db8c122247ce56b67d1b0f685605b761c6` |
| six-fold registry | `b163a6b3e70cde47e033d204d74b997fd218596885a4b96287dc160a948c42ff` |
| SS schema (39 columns) | `b2237506cac4bbc67dfda981f15daea47c32535259d394b962263a82190e2ec4` |
| MS schema (110 columns) | `51ff5e04dde4b862f3cab19c80e2aea93c151006fe7b3f497001e43475ec18cb` |
| fold normalization registry | `f8fb9ccde826ece14690ab255955ecb7b922bc5cd27ddb9b0544b9fd9c9bd634` |
| bootstrap registry | `93a6d66626a1cefb1a2192f321f5fc207dc4d21d3db4d1887c468ca3cf59c4f0` |
| 10,000 paired bootstrap draws | `6814db3e995d104b31c929e041d612bde2d57039f729f944bdcc80b97165a86c` |
| observable store | `3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e` |
| H-MSO-01 contract | `5dcfe3b60f1bea0f402b02286c2627881e12ee57f973e5fbfe15a23a047792e3` |
| prospective gates | `faac8228263b92b9a89dc016d27c5067253c1aeefc72ce0148d9b63939070efb` |

Any mismatch before target generation or formal verdict terminates with
`MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE`.

## Formal population and target

Use all and only the frozen 384 formal cases, exactly 96 per F1--F4, with the
frozen particle states, 234 lineages, disorder states, scales, six folds, and
row order. No reserve, replacement, deletion, addition, redraw, or post-access
case exclusion is permitted. Once any formal target is accessed,
`CASE_REPLACEMENT_AUTHORIZED=false`.

For the three primary components, construct only

`d_h* = R_h L(q*) - L_h(R_h q*)`,

where `L_h` is the frozen lambda=1.00 vendor-base operator on exactly the formal
particle state. The sign is continuum/reference minus lambda-one low-cost
operator, interpreted as the correction added to the low-cost semidiscrete RHS.
No defect at lambda 0.75, 1.25, or 1.50 is constructed. High-resolution SPH is
not truth. `interpolation_density` is diagnostic-only and `total_acceleration`
is derived-only; neither may decide the global hypothesis.

## Isolated analytical source and target qualification

Only after the pre-target Git commit is clean may the project inspect and
provenance-audit the DDO analytical field/reference implementation at frozen
DDO HEAD `d76d29ae51e8104641b710371f0fcb248d5ea268`. Before it is used, record
source paths and hashes, copy only the analytical field/continuum implementation
needed for the three primary components into an isolated MSO-02B vendor path,
record destination hashes, and freeze the target builder executable. DDO
historical target archives, H3 ledgers, metrics, and outcomes are not inputs.

The target builder may read the formal registry and analytical parameters,
physical constants, lambda-one operator, and qualified continuum formulas. It
may not read the MS feature matrix, SS/MS H3 geometry/result artifacts, oracle
outcomes, or any target-derived selection information. Target arrays live only
under `06_experiments/mso02b/target_ref/`; the required qualification table and
access ledger live at `06_experiments/mso02b/`. The MSO-02A observable store is
read-only and its hash is checked immediately before and after target work.

Every case must pass analytical formula/derivative consistency, finite values,
lambda-one base operator/topology identity, component identity and closure,
repeatability, sign convention, and the frozen DDO-compatible numerical/
reference uncertainty semantics before H3 evaluation. Any failure stops the
formal verdict with `MSO02B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE` and
`NOT_EVALUATED_DUE_TO_TARGET_QUALIFICATION_FAILURE`; no reserve is used.

The target store binds case, particle, lineage, family, fold, particle-state
hash, the three primary targets, and reference/numerical uncertainty metadata.
An explicit row-order join audit must prove case, particle, and particle-state
identity against the observable store; no silent reorder is allowed.

## Absolute representation and normalization freeze

SS remains exactly 39 columns and MS exactly 110 columns. Retain the known five
exact constants in each arm, all IQR-degenerate columns (13 involved in SS and
65 in MS), and all five registered exact duplicate MS columns. No PCA,
whitening, correlation pruning, feature selection, embedding, new feature,
deleted feature, alternate distance, or altered fallback is permitted.

For each held-out fold and arm, apply exactly the frozen training-side median,
IQR, and `UNIT_SCALE_RETAIN_COLUMN` fallback constants serialized by MSO-02A.
Observable scaling is never refit from targets or held-out observables.

## Formal statistical unit and paired execution

Particles are dependent measurements. Compute particle quantities only as
inputs to a complete-case summary; cases receive equal weight within each
family/fold, families receive equal weight, and the six outer folds receive
equal weight. Complete lineages are held out. All SS/MS target rows, folds,
target denominators, neighborhood rules, oracle candidates, tuning budget,
case summaries, and 10,000 already-serialized two-stage cluster-bootstrap draws
are paired. The 16-particle-per-case MSO-02A coverage diagnostic sample is not
the formal H3 sample.

A single hash-bound formal executable evaluates SS first, MS second, and the
paired contrast without adaptive modification between arms.

## Frozen metric semantics

### Descriptor nearest-neighbour disagreement

For every held-out particle, use arm-specific frozen normalization and
Euclidean distance to development particles with primary `K=10`; exclude the
same complete case, disorder seed, and field lineage. `K={5,20}` is sensitivity
only. Neighbors are selected without targets. Report componentwise target
disagreement relative to a deterministic matched random baseline, complete-case
median and p90, reciprocal-neighbor consistency, sign disagreement, family
composition, and coverage. Formal aggregation is case-equal, family-equal, and
fold-equal.

The authoritative K=10 matched-random identity is an exact size-10
`numpy.Generator(PCG64(full_SHA256_integer))` draw without replacement. The K=5
sensitivity uses its first five identities. The K=20 sensitivity appends ten
additional identities drawn without replacement from the remaining permitted
pool using the independent domain
`MSO02B|BASELINE_K20_EXTENSION|<case_id>|<particle_id>`; this extension cannot
change any primary K=10 identity or metric.

### Conditional target variance

Use exactly the same target-blind primary K=10 neighborhoods. Compute the
cross-fitted within-neighborhood component trace variance, with the frozen
bias-correction semantics, divided by the corresponding total
development-target trace variance. Do not tune K, radius, bandwidth, weighting,
or transform from outcomes.

### Simple non-neural oracle

Use only the frozen classes: KNN averaging at K={5,10,20}, linear least squares/
ridge, and degree-two polynomial ridge on the frozen invariant subset.
Hyperparameters are selected only by nested complete-lineage validation inside
each outer development partition; SS and MS use the same candidate classes,
selection loss, inner folds, and tuning budget. Report held-out dimensional
RMSE, NRMSE using the frozen target RMS denominator, MAE, bias, vector-angle
diagnostics above the frozen magnitude floor, improvement over the identical
development-fold mean-target predictor, and every family's NRMSE. No tree,
boosting, MLP, GNN, attention, Transformer, or neural operator is permitted.

Where the MSO contract names an exact class but delegates its numerical
implementation to the frozen DDO analytical/H3 semantics (bias correction,
deterministic matched-random construction, ridge grid, invariant polynomial
subset, target magnitude floor, and numerical floor), MSO-02B must import and
hash-bind that already-frozen DDO implementation before target generation. It
must not invent an alternative. If no provenance-audited frozen definition
exists, the affected metric is `NOT_EVALUABLE` and cannot pass; target outcomes
must not be used to fill the gap.

### Coverage

Freeze a target-blind arm/outer-fold radius on exactly the prospective formal
128-particle-per-case sample, not the earlier 16-particle geometry diagnostic.
Within each outer development partition, apply the exact formal normalization
and the same complete-case, complete-lineage, and equal-nonzero-seed exclusions
used for held-out neighbours. For every development row, take its tenth
permitted development-neighbour distance; the arm/fold radius is the p95 using
NumPy `method="inverted_cdf"`. A held-out particle is covered only when its
tenth permitted development-neighbour distance is no larger than that radius.
Report overall, familywise, and foldwise coverage. Coverage is
component-independent and may never substitute for an identifiability metric.

## Frozen gates and verdict logic

For each primary component, MS absolute requirements are:

- DNN median point <=0.20 and simultaneous one-sided UCB <=0.25;
- DNN p90 point <=0.50 and simultaneous UCB <=0.60;
- conditional variance point <=0.25 and simultaneous UCB <=0.35;
- oracle NRMSE point <=0.60 and simultaneous UCB <=0.70;
- improvement over mean predictor point >=25% and simultaneous LCB >=15%;
- every-family NRMSE point <=0.85 and no family UCB >1.00;
- overall coverage >=90%, every-family coverage >=80%; and
- all six folds valid and fold-equal.

Paired MS/SS rescue requires, for every primary component:

- DNN p90 ratio <=0.80 and simultaneous ratio UCB <=0.90;
- conditional-variance ratio <=0.80 and simultaneous ratio UCB <=0.90;
- oracle-NRMSE ratio <=0.85 and simultaneous ratio UCB <=0.95;
- DNN median does not worsen by >0.02 absolute or >5% relative when stable;
- MS worst-family NRMSE does not exceed SS by >0.05 and passes its absolute
  gate;
- MS overall/family coverage passes absolute gates and does not fall >0.05
  below SS; and
- no valid fold reverses all three primary relative effects.

Use the frozen paired log-ratio semantics and numerical-floor diagnostic.
Never add an outcome-dependent epsilon. Use the frozen 10,000 resamples and
one-sided 95% maximum-studentized simultaneous correction across the three
primary components within each metric family. More than 2% degenerate resamples
or insufficient effective lineages makes the inferential gate `NOT_EVALUABLE`.
Pointwise confidence intervals cannot replace simultaneous bounds.

### Target-blind numerical-floor execution amendment

This prospective implementation amendment is frozen before any formal defect
generation. The upstream DDO H3 implementation did not serialize the
dimensionless ratio-stability floor delegated by the preceding paragraph.
MSO-02B therefore fixes it transparently as the same CA-01 floating-point
coefficient used by the qualified reference path:

`f_ratio = C_fp * eps64 = 128 * np.finfo(float64).eps`.

A relative ratio is numerically stable only when the formal SS point estimate
is greater than `100*f_ratio`. This branch is chosen once from the point
estimate and never per bootstrap draw; no epsilon is added. Because no frozen
absolute-difference noninferiority margin exists, an unstable ratio is
`NOT_EVALUABLE` and cannot pass. This amendment supplies only a target-blind
machine-resolution rule; it does not alter a scientific threshold, metric,
feature, fold, normalization, oracle, bootstrap identity, or gate value.

Ratio stability is assessed separately for each component. If a metric family
contains both stable and unstable components, the unstable component is
`NOT_EVALUABLE`; the maximum-studentized statistic is computed jointly across
all and only the stable primary components so multiplicity is retained for
every evaluable contrast. It is never reduced to separate pointwise bounds.

Any non-evaluable required metric, oracle, inferential bound, fold, or component
propagates explicitly to component/global `NOT_EVALUABLE`; it is not relabeled
as a scientific failure and cannot authorize MSO-03. Candidate-level numerical
failures invalidate only that frozen candidate. If all candidates are invalid
for an arm/fold/component, or the selected candidate cannot produce its frozen
outer prediction, that oracle component is `NOT_EVALUABLE` with no fallback to
a different post-selection candidate.

For each component:

`COMPONENT_H_MSO01_PASS = ABSOLUTE_IDENTIFIABILITY_PASS AND RELATIVE_MULTISCALE_RESCUE_PASS`.

Use explicit mixed verdicts when only one side passes. Global
`H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED` requires all three
component passes. If every required component is evaluable but any fails, the
global result is `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED`. If
any required component is non-evaluable, the global result is
`H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`.

If global PASS, only `MSO03_DETERMINISTIC_CLOSURE_BASELINE_ELIGIBLE=true` is
granted. If global FAIL or `NOT_EVALUABLE`, that eligibility and every neural/
attention/learned-operator authorization remain false. No outcome executes
MSO-03.

## No second chance and firewall

After first formal target access, all feature, scale, fold, normalization,
gate, atlas, target, oracle-family, bootstrap, component, and case definitions
are immutable. Record authorized target/reference access counts separately.
The counts for target-derived feature/scale/fold/normalization/gate changes,
neural models, optimizers, training, time integration, solver-in-loop, rollout,
sealed test, and ARC access must all remain zero.
