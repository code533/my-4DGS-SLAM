# Cross-system M5-C result: no meaningful reconstruction gain

Status: **STOP — cross-system soft-opacity intervention unsupported**

Date: 2026-10-09

Branch:

    feature/m5c-flow-reliability-opacity

System:

    my-4DGS-SLAM

Intervention:

    alpha_0 = min(0.5, M5 direct-flow reliability confidence)

Primary question:

> Does the previously confirmed direct-flow reliability cue improve 4DGS
> reconstruction quality when transferred to a different SLAM architecture and
> used to modulate newly inserted Gaussian opacity?

## Outcome

The user-reported final system performance remained essentially unchanged after
enabling the M5-C soft-opacity intervention.

No meaningful improvement was observed in the reconstruction quality metrics.

Exact metric values were not supplied with this stage report, so this document
does not invent numeric deltas.

## Cross-system interpretation

This null result is consistent with the earlier M5-C result in my-Flow4dgs.

Across two different 4D Gaussian SLAM architectures, changing the initial
opacity of new Gaussians according to the same frame-level reliability cue did
not produce a clear downstream benefit.

This strengthens the conclusion that:

    Gaussian initial opacity is not a sensitive downstream control variable for
    the confirmed direct-flow reliability cue.

The result does **not** invalidate the earlier M4-B finding that direct-flow
magnitude predicts local pose reliability.

Instead, it separates two claims:

1. predictive claim:
       direct-flow magnitude is informative about local pose error;

2. intervention claim:
       using that scalar to attenuate initial Gaussian opacity improves the
       final SLAM/reconstruction result.

The first claim remains supported by fresh-sequence validation.
The second claim is not supported.

## Why the null result is informative

The lack of change is unlikely to be explained solely by a weak intervention:
the corresponding Flow4DGS M5-C experiment previously attenuated a large
fraction of insertion events while final performance stayed nearly unchanged.

A plausible mechanism is that initial opacity is rapidly absorbed by later
optimization:
- opacity is trainable;
- mapping/refinement can recover useful Gaussians;
- densification/pruning can compensate for initialization differences;
- frame-level reliability is too coarse to identify which individual map
  updates are actually harmful.

## Decision

Stop M5-C.

Do not tune:
- opacity floor;
- confidence exponent;
- nonlinear confidence-to-opacity mapping;
- system-specific opacity thresholds

on the same sequences.

## Recommended next direction

Move the reliability cue closer to the quantity it actually predicts: camera
tracking error.

Preferred next stage:

    M6-A: reliability-triggered extra pose refinement

Minimal intervention:
- tracking/keyframe/map logic remains baseline;
- only low-reliability frames receive additional pose-only refinement effort;
- high-reliability frames remain unchanged.

This directly tests whether the cue is useful where its predictive relationship
was originally established.
