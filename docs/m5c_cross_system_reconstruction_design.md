# Cross-system M5-C reconstruction experiment

Status: implementation ready; first experiment frozen before outcomes.

## Goal

Port the M5-C reliability-aware Gaussian initial-opacity mechanism from
my-Flow4dgs into my-4DGS-SLAM and test whether it improves dynamic
reconstruction quality.

The question is deliberately different from the previous downstream test:

> Does the confirmed direct-flow reliability cue improve rendering/depth
> reconstruction when used to modulate the initial trust of newly inserted
> Gaussians in a different 4DGS-SLAM architecture?

## Reliability source

Reuse the frozen development-only ECDF created in my-Flow4dgs:

    m5_direct_flow_reference.json

Do not rebuild it from my-4DGS-SLAM outcomes.

At runtime, for keyframe t:

    F10 = flow(t -> t-1)
    F01 = flow(t-1 -> t)
    F21 = flow(t-1 -> t-2)
    F20 = flow(t -> t-2)

All flows are RAFT pixel flows.

The valid support contains:
- the 4DGS-SLAM system-native static/mapping mask;
- forward/backward consistency for t <-> t-1;
- valid t->t-1 coordinates;
- valid temporally composed coordinates;
- valid direct t->t-2 coordinates;
- finite flow values.

The reliability cue is:

    d_t = median ||F20||

over that support.

Confidence:

    q_t = ECDF_train(d_t)
    c_t = max(1 - q_t, 1e-3).

Note: the temporal/direct-flow geometry and FB consistency are ported directly.
The spatial static prior is necessarily adapted to this system's own
motion_mask semantics rather than the Flow4DGS residual-refit mask.

## Intervention

Baseline new-Gaussian opacity:

    alpha_base = 0.5

M5-C soft-opacity run:

    alpha_0 = min(0.5, c_t)

for ordinary keyframe Gaussian insertion with a valid M5 score.

Baseline 0.5 is retained for:
- system initialization;
- dynamic-object initialization;
- invalid/missing M5 score;
- shadow run.

M5-C does not change:
- camera tracking;
- keyframe selection;
- map loss;
- Gaussian position/scale/rotation/color;
- deformation network;
- densification/pruning.

## First sequence

Frozen rapid-development sequence:

    TUM fr3_walking_xyz

This sequence is selected before M5-C reconstruction outcomes are inspected.

## Groups

Only two runs are needed:

1. shadow
   - M5 reliability computation ON
   - soft opacity OFF

2. soft-opacity
   - identical M5 computation ON
   - soft opacity ON

Primary causal comparison:

    soft-opacity vs shadow

## Primary reconstruction metrics

Primary:
- PSNR
- SSIM
- LPIPS
- L1 depth

Secondary:
- ATE
- FPS/runtime
- M5 confidence distribution
- opacity-initialization distribution

The configs explicitly enable repository rendering evaluation.

## Rapid-development decision

M5-C is interesting if reconstruction metrics improve coherently, e.g.:
- PSNR/SSIM increase and LPIPS/depth error decrease; or
- a clear improvement in one major reconstruction axis without meaningful
  degradation in the others.

A tiny fluctuation at the scale of run-to-run noise is not treated as a
positive result.

If the first sequence is promising, freeze the implementation and validate on
one additional sequence. If it is null/negative, do not tune the opacity
mapping on the same sequence.
