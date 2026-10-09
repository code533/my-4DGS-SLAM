# M6-A rapid-development runbook

## Branch

    feature/m6a-reliability-pose-refinement

## Goal

Test whether the frozen direct-flow reliability cue is useful when applied
directly to camera pose tracking rather than Gaussian map construction.

Low-reliability frames receive 20 additional pose-only tracking iterations.

## Frozen trigger

    confidence < 0.20

Invalid/missing reliability does not trigger refinement.

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m6a-reliability-pose-refinement
    git pull

    python -m py_compile \
      utils/m5_flow_reliability.py \
      utils/slam_frontend.py \
      utils/camera_utils.py \
      scripts/summarize_m6a_refinement.py

Ensure the frozen ECDF reference is already present:

    ls -l results/m5_direct_flow_reference.json

Do not rebuild it.

## Step 1: shadow run

The shadow run computes the same per-frame reliability but does not add pose
iterations.

    python slam.py \
      --config configs/rgbd/tum/fr3_walking_xyz_m6a_shadow.yaml \
      --eval --dynamic

Expected outputs:

    <SHADOW_RUN>/m5_flow_reliability/
    <SHADOW_RUN>/m6a_pose_refinement.csv

Summarize:

    python scripts/summarize_m6a_refinement.py \
      <SHADOW_RUN>/m6a_pose_refinement.csv

Expected:

    triggered_frames: 0

Reliability itself should be valid on a useful fraction of frames.

## Step 2: refine run

    python slam.py \
      --config configs/rgbd/tum/fr3_walking_xyz_m6a_refine.yaml \
      --eval --dynamic

Then:

    python scripts/summarize_m6a_refinement.py \
      <REFINE_RUN>/m6a_pose_refinement.csv

Mechanism sanity requirements:
- triggered_frames > 0;
- every triggered frame has confidence < 0.20;
- every triggered frame has extra_iters = 20;
- at least some triggered frames have non-zero extra_delta_t_m or
  extra_delta_r_rad.

If no frame triggers, the sequence is uninformative under the frozen rule; do
not change the threshold on this sequence.

## Step 3: primary comparison

Primary:

    refine vs shadow

Primary metric:

    ATE RMSE

Lower is better.

Secondary:
- PSNR
- SSIM
- LPIPS
- FPS/runtime
- trigger fraction
- median extra translation change
- median extra rotation change.

The first question is whether additional pose effort on predicted-risky frames
actually changes and improves trajectory accuracy.

## Rapid-development decision

Promising:
- practically meaningful ATE improvement vs shadow;
- no material reconstruction degradation.

Null/negative:
- ATE essentially unchanged or worse.

If null/negative, stop M6-A v1 and do not tune:
- confidence threshold;
- 20 extra iterations;
- pose learning rate

on fr3_walking_xyz.

If promising, freeze the method and run one untouched confirmation sequence.

## Important runtime note

M6-A computes reliability on every trackable frame rather than only keyframes.
A flow cache reuses the previous frame's t->t-1 flow as the next frame's
(t-1)->(t-2) flow, preserving the exact score while avoiding one repeated RAFT
forward per frame.

The run will still be slower than baseline because reliability itself requires
additional RAFT inference.
