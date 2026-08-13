# Publication-stage literature verification — 2026-08-13

## Status and boundary

This is an additive publication-stage verification. It does not modify the frozen 2026-08-12 literature files, any scientific value, gate or verdict. The current full matrix is `publication/literature_gap_matrix_2026-08-13.csv`.

The check targeted learned SPH kernels, differentiable SPH, Neural SPH, momentum-conserving particle networks, multiscale particle models, learned mesh-free operators, point-cloud neural operators, local/global particle attention or Transformers, and work explicitly reporting a qualification-first prelearning identifiability test. Primary paper or proceedings pages were preferred. The search is a claim-boundary audit, not an exhaustive systematic review.

## New high-relevance records since the frozen baseline

1. Starepravo et al. introduce a self-supervised graph framework that maps local irregular stencils to mesh-free differential-operator weights using polynomial moment constraints; the operators are local and resolution agnostic and are tested against SPH and a higher-order mesh-free method ([arXiv:2603.24641](https://arxiv.org/abs/2603.24641)). This is a **high** threat to any broad “learned mesh-free operator” novelty claim. It differs from MSO because MSO freezes the operator and tests whether deployment-observable support-scale responses qualify defect identifiability before learning.
2. Li et al. introduce a Gaussian Particle Operator with learned modal windows and global cross-scale Gaussian attention on a mesh-agnostic particle representation ([arXiv:2602.21551](https://arxiv.org/abs/2602.21551)). This is a **high** threat to particle-representation, cross-scale, neural-operator and attention priority claims. MSO neither trains such an operator nor evaluates attention.
3. Mehranfar and Shakibaeinia learn solid-boundary correction terms from local geometry, states and kernel properties for a meshfree particle method, with stated extensibility from MPS to SPH ([arXiv:2510.17813](https://arxiv.org/abs/2510.17813)). This narrows any broad claim about learned particle correction but addresses a different boundary-treatment target.
4. Li et al. report hybrid quantum-classical networks integrated with SPH particle topology ([arXiv:2604.24159](https://arxiv.org/abs/2604.24159)). Direct overlap with MSO's prelearning qualification question is low, but it further blocks broad neural-SPH priority wording.

## Topic-level finding

| Topic | Current finding | Consequence for MSO wording |
|---|---|---|
| Learned SPH kernels/corrections | Established adjacent literature exists | No first learned-kernel/correction claim |
| Differentiable SPH | JAX-SPH and diffSPH establish differentiable implementations and optimization/ML adjacency | No first differentiable-SPH claim; differentiability is not identifiability |
| Neural SPH and particle simulation | Neural SPH and several learned particle simulators already exist | MSO is not a neural-solver paper |
| Momentum-conserving particle networks | Conservation-by-construction particle learning has prior art | No first structure-preserving learned-particle claim |
| Multiscale particle/graph models | Multi-resolution graph fluid models predate MSO | No first multiscale particle representation/model claim |
| Learned mesh-free operators | GMLS-Nets and 2026 NeMDO are direct prior art | Position MSO around frozen-operator qualification, not operator learning |
| Point-cloud neural operators | Multipole GNO and Gaussian Particle Operator cover multilevel/particle operator learning | No first point-cloud neural-operator claim |
| Local/global particle attention | FluidFormer and Gaussian Particle Operator provide direct prior art | Attention/Transformer must not be a protagonist or claimed as necessary |
| Qualification-first prelearning defect identifiability | No exact match was located in this bounded search among the reviewed primary records | May state that this study **uses** a prospective qualification-first design; do not state “first-ever” without a systematic search |

## Defensible publication gap

The narrow working gap is not “learning on SPH particles” or “using multiple scales.” It is the prospective separation of:

1. target-blind numerical admissibility of scale responses;
2. a fresh paired SS/MS deployment-observable representation;
3. formal metric evaluability;
4. componentwise local operational-identifiability qualification; and
5. global cross-fitted prediction versus local-neighborhood ambiguity before any neural correction is authorized.

The frozen evidence then adds a component-resolved result: density qualifies while two momentum components do not, despite strong oracle improvement. This may be framed as the study's contribution under its registered scope, not as a universal or priority claim.

## Approved novelty phrasing

- “We introduce a prospective qualification-first workflow for the tested SPH defect-correction representation.”
- “We provide component-resolved evidence that support-scale responses can improve operational identifiability without doing so uniformly across defect components.”
- “Within the frozen representation, global predictive improvement and local operational-identifiability rescue were empirically separable.”
- “The study evaluates representation eligibility before authorizing a learned correction.”

## Phrasing not supported

- first learned SPH kernel/operator;
- first multiscale particle or point-cloud model;
- first particle Transformer or local/global attention architecture;
- first structure-preserving particle network;
- first-ever qualification-first identifiability study;
- neural SPH or Transformers cannot work;
- temporal or directional information is required.

## Publication-use note

The manuscript should cite the nearest learned-operator and particle-attention work when distinguishing its object. Literature verifies positioning only; it cannot strengthen, weaken or repair H-MSO-01, H-MSO-01R, Route A/B/C or F-MS6.
