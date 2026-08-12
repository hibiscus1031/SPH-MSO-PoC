# MSO-02A fresh atlas and representation freeze report

## Terminal decision

`MSO02A_FRESH_PAIRED_IDENTIFIABILITY_ATLAS_AND_REPRESENTATION_FROZEN`

`MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_ELIGIBLE = true`

MSO-02A constructed and froze a completely target-blind, deployment-observable,
paired SS/MS atlas. This decision establishes numerical admissibility and a
prospective representation/analysis freeze only. It does not answer defect
identifiability and does not execute MSO-02B.

## Git and provenance

- All 46 registered MSO-00/MSO-01 artifact hash checks passed before new
  artifacts were created.
- DDO and PIO parent HEADs remained respectively
  `d76d29ae51e8104641b710371f0fcb248d5ea268` and
  `a0556093070f7f069ca6bea64b5f83d37bea9c76`; both parent worktrees were clean
  at the audit and were not modified.
- Obvious-secret signatures: zero. Files at least 10 MiB before MSO-02A: zero.
  No accidental target/reference payload was present in the MSO project.
- The local pre-science baseline is
  `5869125a0a687db89e1beea4a2d077815c6228b0` on `main`; no remote was created.
- The deterministic seed is the SHA-256 of the complete MSO-00 manifest-file
  hash, complete MSO-01 manifest-file hash, and literal
  `MSO02A_FRESH_ATLAS`. Candidate selection never retried a seed.
- PRIMARY and RESERVE registries were frozen before the formal operator run.
  Their hashes remained unchanged through a float64 feature-assembly compliance
  correction and deterministic replay; no case, order, fold, scale, gate, or
  schema changed.

## Fresh atlas and case preflight

The formal atlas contains exactly 384 cases: F1=96, F2=96, F3=96, F4=96.
It contains 234 complete field lineages. Exact DDO-01D/DDO-02B lineage payload
overlap is zero; PIO and MSO registered identity namespaces are disjoint and no
PIO F1--F4 analytical-field lineage was imported. MSO-01 fixture identity
overlap is zero.

All 384 PRIMARY cases passed, so primary failures=0 and reserve use=0. The
preflight table has 1,536 case-scale rows. Every row passed finite-state/output,
deterministic graph, reciprocal/deduplicated/self-edge, periodic minimum-image,
support completeness, graph nesting, support, covariance rank, repeatability,
component closure, lambda-one vendor-base identity, and finite scale-response
checks. Total graph-nesting failures=0, zero-neighbor environments=0,
rank-deficient environments=0, and support-completeness failures=0. The minimum
case-scale 1st-percentile nonself neighbor count was 14, above the frozen gate 8.

The first execution reached observable serialization after the case compute but
stopped because the already-contracted `observable/` directory did not yet
exist. Creating that directory and replaying changed no protocol artifact. A
release audit then detected that six feature constants were initially created
with PyTorch's default float32 before matrix promotion. The executable was
corrected to construct them directly in float64, registries were confirmed
byte-identical, the executable was re-hashed before the sole release run, and
all target-blind artifacts were deterministically regenerated. This was a dtype
compliance correction before any target access, not a scientific amendment or
outcome-driven choice.

## Paired observables and representation audit

The observable store contains 221,184 particle rows. SS and MS share every case,
particle, particle-state hash, family, lineage, physics hash, base-operator
hash, and fold. All 384 paired-registry rows passed. The only formal difference
is the representation schema hash.

- SS feature dimension: 39.
- MS feature dimension: 110.
- Nonfinite values: zero in both arms.
- Exact constants: 5 in SS and 5 in MS (`mass`, `dx`, `rho0`, `c0`, and
  kinematic viscosity); they are retained.
- Exact duplicate columns: 0 in SS and 5 in MS. The five MS duplicates are the
  registered `S_1.00_1.50` component coordinates, which equal the registered
  `G_1.50` coordinates algebraically because `log(1)=0`; they are retained and
  explicitly audited.
- Pairwise exact scalar-dependency diagnostics: 4 flagged columns in each arm;
  diagnostic only.
- At least one training-fold IQR degeneracy occurred in 13 SS and 65 MS columns.
  All such columns remain present and use the prospectively frozen unit-divisor
  fallback in affected folds.

No historical DDO descriptor, target-inspired feature, continuum proxy,
reference-fitted coefficient, manufactured-field identity, lineage ID,
DESIGN_ONLY parameter, or target-derived scale entered a formal matrix.

## Splits, normalization, coverage, and bootstrap

The authoritative H-MSO-01 contract specifies six outer folds, so six complete
lineage-held-out folds were frozen before target access. Every family is present
in every fold, no lineage crosses folds, all particles from a case remain
together, and SS/MS assignments are identical.

Each arm/fold has target-blind training-side median/IQR constants from the other
five folds. Exact-zero IQR columns use divisor 1 and remain in place. No target,
reference, held-out statistic, PCA, or target RMS was used.

Observable-space Euclidean geometry, K=10 (K=5/20 sensitivity), same-case/seed/
lineage exclusions, training normalization, and leave-one-lineage-out p95
coverage-radius semantics are frozen. Target-blind 16-particle-per-case
geometry diagnostics were precomputed and finite in every arm/fold. DNN target
disagreement and conditional target variance were not computed.

Exactly 10,000 paired two-stage cluster-bootstrap identities were frozen in a
hash-bound compressed draw store: family-by-fold stratification, lineage-first
resampling, complete-case resampling within selected lineages, and identical
SS/MS draws. Case-equal, family-equal, fold-equal aggregation and the existing
maximum-studentized simultaneous correction remain unchanged.

## Scientific firewall

All controlled counts are zero:

- target file open=0; reference archive read=0; continuum operator read=0;
- defect generation=0; DNN target disagreement=0; conditional variance=0;
- oracle fit=0; H3 verdict=0; neural model=0; optimizer=0; training=0;
- integration=0; rollout=0; sealed test=0; ARC access=0.

No H-MSO-01 absolute gate, relative rescue threshold, confidence-bound rule,
scale, family, target, or claim boundary was modified.

## Required final answers

1. Formal fresh atlas exactly 384? **Yes.**
2. F1--F4 each 96? **Yes: 96/96/96/96.**
3. DDO/PIO historical lineage overlap? **Zero registered overlap.**
4. Primary numerical-preflight failures? **0.**
5. Reserve used? **No; 0 cases.**
6. Every formal case four-scale admissible? **Yes.**
7. Graph nesting/support/rank failure? **No; all counts zero.**
8. SS/MS case/particle/state pairing exact? **Yes, all 384 cases and 221,184 rows.**
9. SS/MS dimensions? **39 and 110.**
10. Constant/degenerate observables? **Yes, audited and retained:** 5 constants
    per arm; fold-IQR degeneracy in 13 SS and 65 MS columns; 5 registered exact
    duplicates in MS.
11. Folds frozen before target access? **Yes, six lineage-held-out folds.**
12. Normalization frozen target-blind? **Yes.**
13. Bootstrap identities frozen prospectively? **Yes, 10,000 paired draws.**
14. Target/reference/H3/oracle access all zero? **Yes.**
15. H-MSO-01 gate modified? **No.**
16. Git pre-science baseline? **`5869125a0a687db89e1beea4a2d077815c6228b0`.**
17. MSO-02B only eligibility? **Yes; it was not executed.**
18. Terminal status? **`MSO02A_FRESH_PAIRED_IDENTIFIABILITY_ATLAS_AND_REPRESENTATION_FROZEN`.**

Stop after MSO-02A.

