# M6-A: reliability-triggered extra pose refinement

Status: design frozen before M6-A outcomes.

## Motivation

M4-B established that direct-flow magnitude is predictive of local pose error.
M5-A/M5-B/M5-C tested map-side interventions and did not show clear gains,
including a cross-system M5-C reconstruction test in my-4DGS-SLAM.

M6-A moves the intervention to the quantity actually predicted by the cue:
camera tracking.

## Frozen reliability source

Reuse the existing cross-system direct-flow reliability:

    d_t = median ||F(t -> t-2)||

on the temporal/FB/static valid support, with the frozen Bonn development ECDF:

    q_t = ECDF_train(d_t)
    c_t = max(1 - q_t, 1e-3)

The reference file is not rebuilt from M6-A outcomes.

## Trigger

A frame is considered low reliability when:

    c_t < 0.20

The 0.20 threshold is inherited from the already frozen M5 reliability
experiments and is not tuned on M6-A.

Invalid/missing reliability never triggers extra refinement.

## Baseline tracking

The repository baseline tracking is unchanged:
- pose initialized from the previous frame;
- Adam optimizes pose and exposure;
- at most Training.tracking_itr_num iterations;
- early stop via the existing update_pose convergence test.

## M6-A intervention

After the baseline tracking loop completes, low-reliability frames receive:

    20 additional pose-only iterations

using:
- the same rendering path;
- the same get_loss_tracking objective;
- the same pose optimizer and optimizer state;
- the same pose learning rates.

During these 20 extra iterations:
- exposure_a/exposure_b are frozen;
- map/Gaussian parameters remain untouched as in baseline tracking;
- no new keyframe/map decision is made until refinement finishes.

The extra stage is fixed-length: it does not terminate early on the baseline
convergence flag. This ensures the intervention actually adds refinement effort
rather than immediately exiting for the same convergence condition.

## What M6-A does not change

- Gaussian insertion;
- opacity;
- mapping loss;
- keyframe policy;
- deformation network;
- motion masks;
- baseline tracking iterations;
- pose initialization.

Only low-reliability frames receive extra pose-only optimization effort.

## Rapid-development protocol

Use one development sequence only:

    TUM fr3_walking_xyz

Two groups:

1. shadow
   - reliability computed on every trackable frame;
   - no extra pose refinement.

2. refine
   - identical reliability computation;
   - 20 extra pose-only iterations if c < 0.20.

Primary comparison:

    refine vs shadow

Primary metric:

    ATE

Secondary:
- PSNR / SSIM / LPIPS;
- runtime/FPS;
- trigger fraction;
- per-trigger pose change introduced by the extra stage.

Because M6-A was designed after observing this sequence in the M5-C study,
fr3_walking_xyz is a development/screening sequence, not untouched
confirmation.

## Screening decision

M6-A is promising only if:
- ATE improves by a practically meaningful amount relative to shadow; and
- reconstruction metrics do not materially degrade.

If the change is null or negative, stop M6-A v1 without tuning the 0.20 trigger
or extra-iteration count on this sequence.

If promising, freeze the method and validate on an untouched sequence.
