# Prospective gate proposal

Status: `CONTRACT_PROPOSAL_FROZEN_MSO00`. These are decision thresholds for the future fresh paired atlas, not universal constants.

## Design basis

DDO historical context shows why median-only ambiguity is unsafe: fresh DDO-02B DNN medians were small for density/pressure while p90 disagreement was 8.202/45.54, and pressure/viscosity oracle NRMSE was approximately 1.01/1.049. Thus MSO emphasizes tail, conditional variance, out-of-lineage oracle performance, and worst family simultaneously.

A 5–10% point change is vulnerable to fold/lineage uncertainty and would be weak practical rescue against DDO-scale failures. The primary ambiguity reduction is therefore 20% in point estimate, with a simultaneous upper bound demonstrating at least 10% reduction. Oracle NRMSE receives a 15% practical threshold because it is downstream of both representation and regularized finite-sample fitting, with a simultaneous bound demonstrating at least 5% reduction. Multiplicity is handled with paired maximum-statistic bounds rather than by lowering thresholds after outcomes.

## A. Absolute MS identifiability gates

Every gate must pass for each primary component.

| Family | Frozen absolute requirement |
|---|---|
| DNN median | fold-equal point estimate `<= 0.20`; simultaneous one-sided UCB `<= 0.25` |
| DNN p90 | fold-equal point estimate `<= 0.50`; simultaneous UCB `<= 0.60` |
| conditional variance | point estimate `<= 0.25`; simultaneous UCB `<= 0.35` |
| simple oracle NRMSE | point estimate `<= 0.60`; simultaneous UCB `<= 0.70` |
| improvement over mean-target baseline | point estimate `>= 25%`; simultaneous one-sided LCB `>= 15%` |
| worst-family NRMSE | every family point estimate `<= 0.85`; no family UCB may exceed `1.00` |
| feature coverage | overall `>= 90%`; every family `>= 80%` |
| eligible folds | all 6 folds valid; fold-equal estimate reported |

The main oracle is the nested-development-selected member of the preregistered non-neural grid. Reporting the best test-fold oracle after inspection is forbidden.

## B. Paired SS-versus-MS relative rescue gates

For every primary component, using paired case/fold estimates:

| Family | Practical point threshold | Simultaneous evidence threshold |
|---|---|---|
| DNN p90 | `MS/SS <= 0.80` (at least 20% reduction) | one-sided UCB of ratio `<= 0.90` |
| conditional variance | `MS/SS <= 0.80` | one-sided UCB `<= 0.90` |
| oracle NRMSE | `MS/SS <= 0.85` (at least 15% reduction) | one-sided UCB `<= 0.95` |

All three primary relative families must pass. In addition:

- DNN median must not worsen by more than `0.02` absolute or `5%` relative when the ratio is numerically stable;
- MS worst-family NRMSE must not exceed SS by more than `0.05` absolute and must pass the absolute gate;
- MS overall/per-family coverage must pass the absolute gate and may not fall more than `0.05` absolute below SS;
- no valid fold may reverse all three primary relative effects;
- mean-target baseline definitions and target RMS denominators are identical across arms.

## C. Uncertainty and multiplicity

- Use 10,000 paired deterministic cluster-bootstrap resamples, resampling lineages first and complete cases within lineage when estimable.
- Construct one-sided 95% simultaneous bounds by the maximum studentized statistic across the three primary components within each metric family.
- The three metric families form an intersection requirement; all must pass. No “two out of three” substitution is allowed.
- Report unadjusted intervals as descriptive supplements only.
- If bootstrap effective lineage count is insufficient or more than 2% resamples are degenerate, the inferential gate is `NOT_EVALUABLE`, not pass.

## D. Case-equal/fold-equal semantics

Particle metrics are first summarized within each complete case. Cases receive equal weight within family/fold, families receive equal weight in the macro summary, and six outer folds receive equal weight. A particle-pooled result can be diagnostic only and cannot overrule the formal result.

## E. Decision matrix

- **Absolute pass + relative pass for all components:** H-MSO-01 global pass.
- **Relative improvement but any absolute fail:** route remains non-identifiable; no architecture selection.
- **Absolute pass but relative fail:** MS may be descriptively adequate, but the causal multiscale-rescue hypothesis fails.
- **Only some components pass:** componentwise evidence only; global fail.
- **Coverage, pairing, firewall, provenance, or fresh-role failure:** comparison invalid.

## F. Freeze rule

These values must be manifest-hashed before any fresh defect generation. If simulation-budget/power analysis later shows the bounds cannot be estimated, change the sample design before target access; do not loosen the scientific thresholds. Any post-outcome threshold change creates a new exploratory contract and cannot qualify the original H-MSO-01.
