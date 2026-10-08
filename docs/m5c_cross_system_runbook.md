# M5-C cross-system reconstruction runbook

## Branch

    feature/m5c-flow-reliability-opacity

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m5c-flow-reliability-opacity
    git pull

    python -m py_compile \
      utils/m5_flow_reliability.py \
      utils/slam_frontend.py \
      utils/camera_utils.py \
      gaussian_splatting/scene/gaussian_model.py \
      scripts/import_m5_reference.py \
      scripts/summarize_m5c_opacity.py

## Step 1: import the frozen ECDF reference

From the old my-Flow4dgs working tree, use the already generated file:

    results/m5_direct_flow_reference.json

Example:

    python scripts/import_m5_reference.py \
      /path/to/my-Flow4dgs/results/m5_direct_flow_reference.json

The command should create:

    results/m5_direct_flow_reference.json

and print:

    method m5_direct_flow_ecdf_reference_v1

Do not rebuild this reference from TUM.

## Step 2: shadow run

    python slam.py \
      --config configs/rgbd/tum/fr3_walking_xyz_m5c_shadow.yaml \
      --eval --dynamic \
      --save_results 1

Expected outputs include:

    <RUN>/m5_flow_reliability/
    <RUN>/m5c_opacity_initialization.csv

In shadow, alpha_init should remain 0.5 even when M5 confidence is low.

## Step 3: inspect shadow reliability

Inspect an M5 payload:

    python - <<'PY'
    import glob, torch
    p=sorted(glob.glob("<SHADOW_RUN>/m5_flow_reliability/*.pt"))[0]
    d=torch.load(p,map_location="cpu")
    for k in [
        "frame","valid","num_valid_pixels","fb_valid_pixels",
        "static_fb_pixels","direct_flow_median_px",
        "training_ecdf","confidence","reference_file"
    ]:
        print(k,d.get(k))
    PY

Required sanity:
- valid=True on a useful fraction of keyframes;
- direct_flow_median_px finite and >=0;
- training_ecdf in [0,1];
- confidence in [0.001,1].

## Step 4: soft-opacity run

    python slam.py \
      --config configs/rgbd/tum/fr3_walking_xyz_m5c_soft_opacity.yaml \
      --eval --dynamic \
      --save_results 1

Then:

    python scripts/summarize_m5c_opacity.py \
      <SOFT_RUN>/m5c_opacity_initialization.csv

Required sanity:
- m5c_applied_rows > 0;
- alpha never exceeds 0.5;
- some valid low-confidence insertions have alpha < 0.5.

## Step 5: reconstruction comparison

Use the repository's own rendering evaluation outputs.

Compare shadow vs soft-opacity:

    PSNR      higher is better
    SSIM      higher is better
    LPIPS     lower is better
    L1 depth  lower is better

Also record:
- ATE
- FPS
- exact run directories
- M5 validity fraction
- applied opacity min/median/max.

The primary scientific question is reconstruction quality, not trajectory ATE.

## Decision

If soft-opacity shows a coherent reconstruction improvement, freeze the method
and validate on one additional sequence.

If performance is essentially unchanged or worse, stop the cross-system M5-C
test without tuning the opacity mapping on fr3_walking_xyz.
