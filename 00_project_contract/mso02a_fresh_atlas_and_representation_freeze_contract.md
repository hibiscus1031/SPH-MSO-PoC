# MSO-02A fresh atlas and representation freeze contract

Status before execution: `FROZEN_BEFORE_FRESH_CASE_OPERATOR_EVALUATION`.

## Scope and stop boundary

MSO-02A is limited to target-blind fresh-atlas generation, deployment-observable
static operator computation, case-level four-scale numerical admissibility, and
prospective representation/split/normalization/bootstrap freeze. It does not
generate or read a defect, reference field, continuum operator, target outcome,
H3 quantity, target-disagreement statistic, conditional target variance, oracle,
model, optimizer, trajectory, rollout, or sealed evidence. MSO-02B is not
executed.

The only possible terminal success label is
`MSO02A_FRESH_PAIRED_IDENTIFIABILITY_ATLAS_AND_REPRESENTATION_FROZEN`.
Success creates eligibility for MSO-02B only.

## Frozen provenance inputs

- MSO-00 and MSO-01 registered artifacts must pass their recorded SHA-256
  checks before this contract is executed.
- The local project must have a clean `main` baseline commit containing the
  complete frozen MSO-00/MSO-01 state and no remote.
- The MSO-00/MSO-01 contracts, manifests, scale ladder, gates, firewall, and
  claim boundary are immutable inputs.
- The immutable PIO Stage01C static vendor operator is used without edits.
- DDO registries are read only for target-free field semantics and lineage
  exclusion; DDO observable/target archives and all PIO target/reference
  payloads remain unopened.

## Deterministic seed and registry construction

Let `H00` and `H01` be the SHA-256 digests of the complete
`mso00_manifest.json` and `mso01_manifest.json` files. The single seed digest is

`SHA256(H00 || H01 || "MSO02A_FRESH_ATLAS")`.

All phase values, jitter seeds, tie breaks, case ordering, fold assignment,
particle diagnostic samples, and bootstrap draws are domain-separated hashes
of this digest. No seed or candidate is retried and selected by appearance or
outcome.

Before any fresh-case operator call, freeze and hash:

- 384 PRIMARY candidates, exactly 96 in each of F1--F4;
- 128 RESERVE candidates, exactly 32 in each of F1--F4;
- all case and lineage identities, parameters, disorder states, numerical
  parameters, family assignments, and orders;
- SS/MS feature allowlists and the candidate-lineage fold assignment; and
- this contract and the executable protocol.

The analytical fields use the frozen DDO two-dimensional periodic torus,
barotropic WCSPH state, EOS `p=c0^2*(rho-rho0)`, Wendland-C4 vendor kernel,
float64 CPU arithmetic, and target component scope. F1 is a single-mode
isolated probe; F2 is a deterministic multi-frequency isolated probe; F3 is an
oblique/anisotropic isolated probe; F4 is a controlled-disorder single-mode
probe. The field itself is sampled on the particle state; no analytical
derivative or continuum operator is evaluated in MSO-02A.

## Case admission and reserve policy

Every PRIMARY case is evaluated at support multipliers
`[0.75, 1.00, 1.25, 1.50]`. Admission requires, at all four scales:

1. finite state, graph, operator, and registered scale-response values;
2. deterministic graph construction;
3. reciprocal, deduplicated, in-bounds edges and exactly one self edge per
   particle;
4. correct periodic minimum-image and complete compact support;
5. nested directed edge sets in increasing multiplier order;
6. zero isolated particles and 1st-percentile nonself support at least 8;
7. full weighted-covariance rank and support-completeness fraction 1;
8. bitwise operator repeatability and component closure; and
9. bitwise equality between the lambda-one scaled call and the frozen vendor
   base-support call.

An inadmissible primary remains permanently recorded and is replaced only by
the next preordered same-family reserve. Reserve candidates are never reordered
or selected manually. No second reserve batch may be created.

## Frozen representations

Both arms contain the same case, particle, state, physics, base operator,
fold, normalization role, and later target identity. Join keys and design
governance fields are never formal inputs.

The SS allowlist is the frozen common deployment representation `B(q_h)`:
observable state/physical/numerical values, local minimum-image geometry and
centered velocity summaries, base-support kernel/support moments, and the five
scalar base-operator component coordinates (density rate and the two vector
coordinates of each acceleration component).

The MS allowlist contains every SS column plus only the registered nonbaseline
operator values, baseline differences, log-scale divided differences, the two
registered pair slopes, the two registered nonuniform curvatures, and
per-particle neighbor-count topology/support summaries at the qualified scales.
No DDO historical target or descriptor is copied as an ad hoc feature.

## Dimensionality and purely numerical amendment

Before target access, audit each arm for finite values, exact constants, exact
duplicates, pairwise exact scalar linear dependencies, numerical range, and
fold-training IQR degeneracy. These diagnostics do not delete columns.

The parent contract specifies training-side median/IQR scaling but does not
fully specify an exact-zero IQR fallback. The prospective target-blind rule is:

- compute the median and IQR from development-side deployment observables only;
- if the finite IQR is strictly positive, use it as the divisor;
- if the IQR is exactly zero, retain the column, use divisor `1.0`, and mark
  `UNIT_SCALE_RETAIN_COLUMN`;
- never inspect a target or remove a column based on a downstream result.

This amendment exists only to make the frozen matrix transformation total and
does not modify any H-MSO-01 scientific gate.

## Splits, normalization, coverage, and bootstrap

The authoritative `h_mso01_contract.md` requires six outer folds, so six
lineage-held-out folds are used. Complete lineages and complete cases stay in
one fold; every family has at least one lineage in every fold; SS/MS assignments
are identical. Each fold's normalization is derived from the other five folds
only and is frozen before target generation.

Observable-space geometry uses Euclidean distance after the arm-specific
training-fold median/IQR transform, excludes the same case/seed/lineage, and
freezes `K=10` (`K=5,20` sensitivity only) and a leave-one-lineage-out 95th
percentile development radius definition. No target disagreement or
conditional target variance is computed in MSO-02A.

Freeze 10,000 paired deterministic two-stage cluster-bootstrap identities,
stratified by family and fold: resample lineages first and complete cases within
each selected lineage when estimable. SS/MS consume identical draws. Formal
aggregation remains case-equal, family-equal, and fold-equal. One-sided 95%
simultaneous bounds use the frozen maximum-studentized correction across the
three primary components within each metric family. All existing absolute and
relative H-MSO-01 gates remain unchanged.

## Firewall and invalidation

Every prohibited activity counter must remain zero. Any target/reference/H3/
oracle access invalidates the stage with
`MSO02A_INFORMATION_FIREWALL_BREACH`. Pair mismatch, provenance conflict,
registry shortage, or case numerical inadmissibility uses the most specific
terminal failure state from the user authorization. No failure can be repaired
by changing a scale, family, gate, target, seed, or post-outcome feature.
