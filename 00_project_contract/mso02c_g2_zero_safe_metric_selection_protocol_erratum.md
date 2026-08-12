# MSO-02C G2 pre-synthetic protocol erratum 01

Status: `FROZEN_BEFORE_ANY_SYNTHETIC_CANDIDATE_COMPARISON`.

Protocol commit:
`22879748a2a813108ff7ce667f9b4c2366aca006`.

No S1--S18 candidate computation, synthetic bootstrap, real-target replay, or
real store access occurred before this erratum.

## Corrected ambiguity

The original protocol used one ratio branch for both particlewise Candidate A
and aggregate Candidates B--D. That conflicted with the user's explicit rule:
when the aggregate random-disagreement denominator is zero, the aggregate
statistic is `NOT_EVALUABLE` and must not auto-PASS.

The authoritative prospective rules are now:

- Candidate A particlewise `0/0` is
  `NO_TARGET_CONTRAST_NOT_EVALUABLE`;
- Candidate A particlewise `positive/0` is
  `POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED`;
- for Candidates B, C, and D, any zero aggregate denominator is
  `NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE`, with a separate non-gating
  auxiliary flag recording whether its aggregate numerator was zero or
  positive;
- no epsilon, tolerance, deletion, clipping, or automatic PASS is introduced.

This is a definition-only correction made before observing any synthetic
candidate output. All other formulas, fixtures, criteria, thresholds, and
firewall rules in the protocol remain unchanged.
