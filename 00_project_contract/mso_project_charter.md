# SPH-MSO project charter

## Project identity

- Project: **SPH-MSO — Multiscale State and Operator Qualification for Structure-Preserving SPH Learning**.
- Stage: **MSO-00 — Prospective Project Contract, Literature Boundary, Provenance and Identifiability Design Freeze**.
- Root: `/Users/xiejinbo/Documents/SPH-MSO-PoC`.
- Scientific parents, read-only historical sources only:
  - `/Users/xiejinbo/Documents/SPH-DDO-PoC` at audited HEAD `d76d29ae51e8104641b710371f0fcb248d5ea268`;
  - `/Users/xiejinbo/Documents/SPH-PIO-PoC` at audited HEAD `a0556093070f7f069ca6bea64b5f83d37bea9c76`.
- SPH-ARC is not a scientific parent and contributes zero scientific evidence, code, parameters, qualifications, outcomes, or conclusions.

SPH-MSO is independent. It is not DDO-03, PIO Stage09, an ARC stage, or a branch of any of them.

## Primary research question

Can an explicitly scale-sensitive, deployment-compatible SPH numerical representation reduce the operational conditional ambiguity observed for instantaneous SPH spatial discretization defects in SPH-DDO?

The question is about **prelearning numerical representation and identifiability**, not whether a Transformer, attention mechanism, learned kernel, neural operator, or retrained PIO model performs better.

## Frozen first learning object

For continuum state \(q^*\), continuum spatial operator \(\mathcal L\), sampling map \(R_h\), and frozen SPH semidiscrete operator \(\mathcal L_h\),

\[
d_h^*=R_h\mathcal L(q^*)-\mathcal L_h(R_hq^*).
\]

The sign means “add to the low-cost semidiscrete RHS.” Evaluation is fixed-time and spatial only. The DDO continuum/SPH modeled-term alignment, EOS, periodic domain, support convention, component semantics, and reference firewall are unchanged. `HIGH_RESOLUTION_SPH_IS_TRUTH=false`.

Primary components are:

1. `density_rate`;
2. `pressure_gradient_acceleration`;
3. `viscosity_laplacian_acceleration`.

`interpolation_density` is `DIAGNOSTIC_ONLY`. `total_acceleration` is `DERIVED_DIAGNOSTIC_ONLY` and has no independent qualification route.

## Frozen causal contrast

H-MSO-01 compares two entirely fresh, paired arms:

- `SS = SINGLE_SCALE_CONTROL`;
- `MS = MULTISCALE_RESPONSE`.

Both arms use the same fresh cases, particles, target records, field family, SPH physical model, kernel family, precision, split assignments, folds, bootstrap draws, normalizations fitted without target access, and statistical aggregation. The only formal intervention is:

`representation: SS -> MS`.

Historical DDO H3 outcomes are context for design and threshold scale only. They are not the SS result.

## First multiscale boundary

MS uses the same deployment particle state \(q_h\), evaluated with the same qualified SPH semidiscrete formulas at candidate support radii \(\lambda h\). It neither changes particle resolution nor learns a kernel. The candidate ladder is prospectively registered as `[0.75, 1.00, 1.25, 1.50]` and is not authorized for scientific target evaluation until MSO-01 passes target-blind numerical qualification.

## Information firewall

`REFERENCE_IN_FORMAL_INPUT=false`.

Formal inputs may be constructed only from the deployment state and frozen numerical parameters. No reference field, defect target, reference-minus-low-cost proxy, manufactured-field identity, hidden lineage label, design-only information, or target-derived choice/normalization may enter inputs, neighborhoods, feature selection, scale selection, splits, or normalization.

Observable data and reference/target data must be physically separate stores with disjoint schemas. The formal registry is authoritative.

## MSO-00 activity boundary

Allowed: read-only repository audit, target-blind interface inspection, provenance tracing, contract drafting, literature registration, and prospective experimental design.

Forbidden in MSO-00:

- new scientific target evaluation or access;
- neural model instantiation or training;
- optimizer creation/execution;
- time integration, solver-in-loop execution, or rollout;
- sealed-test access;
- selection of scales, descriptors, gates, or architectures from fresh outcomes.

## Governance

- Gates and the candidate scale ladder are frozen before any fresh target generation.
- Any amendment records old/new values, reason, timestamp, data already seen, and affected evidence. A post-outcome amendment cannot retroactively qualify the original contract.
- All results are case-equal and fold-equal; particles are never treated as independent cases.
- Full field lineages are held out. Fresh requalification cannot reuse consumed cases or target outcomes.
- Failure is retained. Failure does not authorize architecture search.

## Terminal state

MSO-00 terminal state: `MSO_PROJECT_AND_PRELEARNING_MULTISCALE_IDENTIFIABILITY_CONTRACT_FROZEN`.

MSO-01 is authorized only for the target-blind numerical qualification listed in `07_reports/mso00_final_report.md`. Scientific SS/MS target evaluation, neural learning, optimization, integration, and rollout remain unauthorized.
