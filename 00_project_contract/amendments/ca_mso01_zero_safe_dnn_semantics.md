# CA-MSO-01: prospective zero-safe DNN semantics

Status: `FROZEN_PROSPECTIVELY_BEFORE_ANY_CONSUMED_REPLAY_OR_H_MSO01R_TARGET_ACCESS`.

## Immutable scientific boundary

The old hypotheses remain permanently unchanged:

- `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE`
- `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`

This amendment creates only the future hypothesis `H-MSO-01R`. Consumed MSO-02B and G1 A/B evidence had already been seen. One over-broad old-metric text search was disclosed before protocol freeze; its matched-file count was not recorded and no numeric value from it was used. G2 performed no real candidate metric computation, store payload read, or consumed replay.

## Prospective DNN statistic

For arm `a`, component `q`, case `c`, and registered particle `i`, retain frozen K=10 neighbours, matched-random comparators, exclusions, features, normalization, and Euclidean distance. Let `n[a,q,c,i]` and `b[q,c,i]` be their squared target-disagreement energies. First average all particles within each case to `N[a,q,c]` and `B[q,c]`. Then apply

`W(x) = mean_fold mean_family mean_lineage mean_case-within-lineage x[c]`.

The H-MSO-01R DNN statistic is exactly `D[a,q]=W(N[a,q])/W(B[q])`. It is not a mean of particle, case, lineage, family, or fold ratios. No registered particle, case, lineage, family, or fold is deleted. If `W(B)==0`, the statistic is `NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE`; no epsilon, tolerance, clipping, or automatic PASS is allowed.

## Gates

The absolute DNN gate requires both point `D<1` and the three-component simultaneous one-sided 95% UCB `<1`; equality is random-equivalent and does not qualify. For positive SS, the relative gate requires point `D_MS/D_SS<=0.80` and simultaneous UCB `<=0.90`. If SS is zero, relative rescue is `RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE`. If SS is positive and MS is zero, exact-zero dominance requires every otherwise-valid paired draw to retain that branch.

Bootstrap uses 10,000 fresh target-blind paired lineage-first draws, the same draw for SS/MS and all components, and recomputes W(N), W(B), and their ratio from case primitives in every draw. More than 200 degenerate draws or fewer than two valid draws makes the DNN metric family NOT_EVALUABLE; max-studentized one-sided 95% multiplicity correction spans the three components.

All non-DNN gates remain unchanged. H-MSO-01R requires a completely fresh 384-case atlas, 96 per family, zero lineage overlap, fresh target-blind SS/MS freeze, folds, normalization, bootstrap, and only then target access. This amendment authorizes no replay, execution, MSO-03, attention, neural training, or learned operator.
