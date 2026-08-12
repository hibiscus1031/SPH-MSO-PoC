# Paired SS-versus-MS ablation contract

## Causal estimand

The estimand is the change in prospectively defined ambiguity and oracle metrics caused by replacing `SINGLE_SCALE_CONTROL` with `MULTISCALE_RESPONSE`, on identical fresh evidence.

## Frozen arm definitions

| Attribute | SS | MS |
|---|---|---|
| base deployment field family | identical \(B(q_h)\) | identical \(B(q_h)\) |
| base operator | \(\mathcal L_h(q_h)\) | same \(\mathcal L_h(q_h)\) |
| extra support evaluations | none exposed | qualified \(\mathcal L_{\lambda h}(q_h)\), \(\lambda\in\{0.75,1.25,1.50\}\) |
| response features | none | frozen \(\Delta O,G,S,C\) and topology summaries |
| target | same \(d_h^*\) | same \(d_h^*\) |

The sole formal variation is the exposed representation. The operator cache may compute all candidate scales once for efficiency, but the SS design matrix is constructed by an audited column allowlist and cannot see nonbaseline values, missingness, scale qualification flags, or filenames encoding MS outcomes.

## Variables held fixed

- complete case/particle identities and particle weights;
- continuum and SPH physics, EOS, viscosity, kernel formula family, support convention, domain, boundary handling, self-edge and accumulation semantics;
- field families and parameter axes;
- dtype and hardware/software execution policy;
- target-generation code, reference hierarchy, uncertainty checks and signed components;
- six lineage-held-out folds and all nested splits;
- case-equal and fold-equal aggregation;
- bootstrap seeds/draws and multiplicity correction;
- metric definitions, K values, oracle class grid, polynomial subset rule, and target-magnitude floors;
- target-blind feature normalization policy and coverage construction;
- missing/invalid case policy.

## Prohibited confounding

Do not:

- use historical DDO H3 as SS;
- give MS different cases, fields, targets, precision, splits, oracle families, tuning budget, or aggregation;
- change particle resolution in MS;
- learn/retune the kernel or operator in MS;
- select candidate scales or response columns from target correlations;
- add absolute coordinates, analytical field identity, lineage, reference-minus-low-cost features, or targets to either arm;
- remove a family because one arm performs poorly;
- impute a failed scale only in MS; a case numerically invalid for the frozen ladder is invalid for the paired comparison;
- interpret extra dimensionality alone as causal evidence without the preregistered held-out/coverage gates.

## Paired statistical comparison

For positive error/ambiguity metric \(M\), define

\[
R_M=M^{MS}/M^{SS},\qquad A_M=M^{SS}-M^{MS}.
\]

Compute both from paired case/fold summaries. Ratio inference uses paired bootstrap on `log(R_M)` with a small denominator diagnostic; if an SS metric is within 100 times its deterministic numerical floor, the ratio is marked unstable and the preregistered absolute-difference noninferiority rule is used. Never add an arbitrary target-dependent epsilon to force a ratio.

## Missingness and failure

All exclusions are target-blind and paired. Reasons are frozen categories: invalid density, invalid periodic support, nonfinite static operator, failed graph invariant, absent component excitation under a target-blind rule, or corrupt artifact. Report exclusion counts by arm (which must match), family, and fold. More than 5% paired case exclusion overall or more than 10% in any family invalidates confirmatory status.

## Decision labels

- `H_MSO01_PASS_ALL_PRIMARY`: all absolute and relative gates pass for all three primary components.
- `H_MSO01_PARTIAL_COMPONENT_ONLY`: one or two components pass; global hypothesis does not pass.
- `H_MSO01_ABSOLUTE_FAIL`: at least one component fails an absolute gate.
- `H_MSO01_RELATIVE_RESCUE_FAIL`: absolute gates may pass but paired rescue does not.
- `H_MSO01_COMPARISON_INVALID`: firewall, pairing, missingness, split, or provenance violation.

No decision label authorizes neural training or rollout automatically.
