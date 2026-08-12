# Prospective multiscale-response definition

Status: `SCHEMA_AND_SEMANTICS_FROZEN_MSO00`; numerical admissibility remains `PENDING_MSO01_TARGET_BLIND_QUALIFICATION`.

## Fixed state and scale intervention

Let the deployment state be

\[
q_h=\{\mathbf x_i,m_i,\rho_i,\mathbf v_i,h_i;\theta_{EOS},\nu,\Omega,\text{kernel-id},\text{dtype}\}_{i=1}^N.
\]

For candidate multiplier \(\lambda_k\), define \(q_h^{(\lambda_k)}\) as the **same** state and parameters except that support values supplied to the same semidiscrete implementation are \(\lambda_k h_i\). Particle number, positions, masses, sampled density/velocity, particle resolution, physical model, EOS, viscosity, kernel family/formula, dtype, domain, boundary convention, self-edge policy, and accumulation rule do not change.

Define

\[
\mathbf O_k(q_h)=\mathcal L_{\lambda_k h}(q_h),
\]

with separately labeled components `density_rate`, `pressure_gradient_acceleration`, and `viscosity_laplacian_acceleration`. \(\mathbf O_0=\mathcal L_h(q_h)\) denotes the \(\lambda=1\) baseline. No time step is taken.

This is a numerical support-scale intervention, not a particle-resolution ladder and not a learned kernel.

## Candidate ladder

\[
\lambda_{candidate}=(0.75,1.00,1.25,1.50).
\]

All four values are candidates only. They remain jointly frozen during MSO-01. MSO-01 may accept/reject the entire ladder or flag individual numerical inadmissibility using only the preregistered target-blind checks. It may not substitute a new value after seeing any defect/identifiability outcome. A replacement requires a new pre-target contract version.

## Response quantities

For every component and particle:

### Raw scale evaluation

\[
O_k=\mathcal L_{\lambda_k h}(q_h).
\]

### Baseline difference

\[
\Delta O_k=O_k-O_0,\qquad \Delta O_{\lambda=1}=0.
\]

### Log-scale secant response

With \(z_k=\log\lambda_k\), for \(\lambda_k\ne1\),

\[
G_k=\frac{O_k-O_0}{z_k}.
\]

### Pairwise log-scale slope

For preregistered \(a<b\),

\[
S_{ab}=\frac{O_b-O_a}{z_b-z_a}.
\]

The formal first-order bracket is `S_0.75_1.25`. `S_1.00_1.50` is a secondary diagnostic.

### Nonuniform second log-scale divided difference

For \(a<b<c\),

\[
C_{abc}=\frac{2}{z_c-z_a}
\left[
\frac{O_c-O_b}{z_c-z_b}-
\frac{O_b-O_a}{z_b-z_a}
\right].
\]

Formal curvature candidates are `C_0.75_1.00_1.25` and `C_1.00_1.25_1.50`.

These are finite differences over a candidate ladder. They are not derivatives unless a later study establishes the necessary fixed-topology/smoothness conditions. Neighbor topology may change with support; topology-change counts are mandatory observables.

## Deployment-derived normalization

Raw dimensional quantities are retained for audit and outcome metrics. Formal features may additionally use

\[
\widetilde O=O/s_{obs},\quad
\widetilde{\Delta O}=\Delta O/s_{obs},
\]

where \(s_{obs}\) is constructed only from development-fold deployment observables of the same physical component (robust median/IQR or a frozen dimensional scale using \(h,c_0,\nu,\rho\)). The exact rule is fitted within each development fold and then applied unchanged. Target RMS, defect magnitude, reference fields, held-out statistics, and target outcomes are forbidden in normalization.

## SS and MS representations

Let \(B(q_h)\) be the common deployment field family:

- density, mass/volume, support and frozen numerical parameters;
- minimum-image relative geometry normalized by base \(h\);
- velocity differences/local centered velocity moments (not absolute global coordinates or a hidden field identity);
- base-support neighbor count and kernel moment summaries;
- the three labeled base operator outputs \(O_0\).

Then

\[
\Phi_{SS}=B(q_h),
\]

and

\[
\Phi_{MS}=B(q_h)\oplus\{O_k,\Delta O_k,G_k,S_{ab},C_{abc},
\text{topology summaries}\}_{\lambda_k\ne1}.
\]

MS repeats the same numerical field/operator family across support scales. It does not add reference information, new physical fields, target-derived fields, lineage labels, architecture embeddings, or a different receptive-field source. The representation column set is frozen before target generation and hashed in the experiment manifest.

## Storage firewall

Observable artifacts live under `06_experiments/<stage>/observable/` and use the prefix `obs__`. Reference and target artifacts live under `06_experiments/<stage>/reference_target/` and use `target_ref__` or `target__`. No table, normalization fit, neighborhood search, or oracle design matrix may mix these schemas before a firewall audit.

## MSO-01 target-blind numerical qualification

MSO-01 may use only deployment-state/static qualification fixtures and may:

1. bind source paths/hashes, dtype, domain, support convention, kernel, self-edge and accumulation semantics;
2. verify deterministic graph hashes, reciprocal/deduplicated edges, minimum-image geometry, and nested edge sets for increasing scalar support;
3. verify all supports remain positive and below half the periodic extent;
4. require no isolated particle and a 1st-percentile nonself neighbor count of at least 8 at every candidate scale on every admissible fixture;
5. verify finite operator values and response quantities;
6. verify uniform-velocity continuity and viscosity responses at dtype-scaled tolerance, while not requiring disordered constant-pressure per-particle acceleration to vanish;
7. verify pressure/viscosity reciprocal pair-force residuals and total internal force at `256*eps` times the declared force scale; verify viscosity pair power is nonpositive within `256*eps` tolerance;
8. verify the \(\lambda=1\) path is bitwise identical to the frozen baseline call and \(\Delta O_1=0\);
9. quantify topology changes and require each nonbaseline component response RMS to exceed `100` times deterministic repeat/accumulation noise on at least two target-blind excitation fixtures; and
10. run AD/FD interface checks only if an implementation exposes scale differentiation, with the explicit warning that derivatives across topology changes are not qualified.

MSO-01 may not read/generate \(d_h^*\), continuum reference terms, H3 outcomes, or sealed data; choose a scale by target behavior; train; optimize; integrate; or roll out.
