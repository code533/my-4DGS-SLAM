"""Cross-system M5-C direct-flow reliability for 4DGS-SLAM.

This ports the frozen direct-flow reliability idea from my-Flow4dgs while
keeping the runtime score causal.  The direct cue is the median magnitude of
flow t->t-2 over a temporal-cycle-compatible support.  Confidence is obtained
from a frozen development-only ECDF reference.
"""

import bisect
import json
from pathlib import Path

import torch
import torch.nn.functional as F

from RAFT.raft import RAFT
from RAFT.utils.utils import InputPadder


class _RaftArgs:
    def __init__(self, model_path):
        self.model = str(model_path)
        self.small = False
        self.mixed_precision = False
        self.alternate_corr = False


def _mesh(height, width, device, dtype):
    y, x = torch.meshgrid(
        torch.arange(height, device=device, dtype=dtype),
        torch.arange(width, device=device, dtype=dtype),
        indexing="ij",
    )
    return x, y


def _sample_flow(flow_px, x, y):
    """Bilinearly sample [2,H,W] pixel flow at pixel coordinates x,y."""
    _, H, W = flow_px.shape
    gx = 2.0 * x / max(W - 1, 1) - 1.0
    gy = 2.0 * y / max(H - 1, 1) - 1.0
    grid = torch.stack([gx, gy], dim=-1)[None]
    return F.grid_sample(
        flow_px[None],
        grid,
        mode="bilinear",
        padding_mode="zeros",
        align_corners=True,
    )[0]


def fb_valid_mask(flow_ab_px, flow_ba_px, alpha1=0.5, alpha2=0.5):
    """Forward/backward consistency mask in pixel units.

    This mirrors the threshold already used by 4DGS-SLAM Camera.compute_fwdbwd_mask,
    but is evaluated in torch so it can be combined directly with the M5 support.
    """
    f_ab = flow_ab_px.double()
    f_ba = flow_ba_px.double()
    _, H, W = f_ab.shape
    x, y = _mesh(H, W, f_ab.device, f_ab.dtype)

    qx = x + f_ab[0]
    qy = y + f_ab[1]
    q_in = (
        (qx >= 0.0) & (qx <= W - 1)
        & (qy >= 0.0) & (qy <= H - 1)
    )

    f_ba_q = _sample_flow(f_ba, qx, qy)
    err = torch.linalg.norm(f_ab + f_ba_q, dim=0)
    mag = torch.linalg.norm(f_ab, dim=0) + torch.linalg.norm(f_ba_q, dim=0)
    finite = torch.isfinite(f_ab).all(dim=0) & torch.isfinite(f_ba_q).all(dim=0)
    return q_in & finite & (err < float(alpha1) * mag + float(alpha2))


def direct_flow_on_temporal_support(
    flow_t_to_tm1_px,
    flow_tm1_to_tm2_px,
    flow_t_to_tm2_px,
    static_fb_mask,
):
    """Return direct-flow magnitude and M5 temporal valid support."""
    f10 = flow_t_to_tm1_px.double()
    f21 = flow_tm1_to_tm2_px.double()
    f20 = flow_t_to_tm2_px.double()

    if f10.shape != f21.shape or f10.shape != f20.shape:
        raise ValueError("M5 flows must share shape [2,H,W]")
    if f10.ndim != 3 or f10.shape[0] != 2:
        raise ValueError("M5 flows must have shape [2,H,W]")

    _, H, W = f10.shape
    if tuple(static_fb_mask.shape) != (H, W):
        raise ValueError("static_fb_mask must have shape [H,W]")

    x, y = _mesh(H, W, f10.device, f10.dtype)
    qx = x + f10[0]
    qy = y + f10[1]
    q_in = (
        (qx >= 0.0) & (qx <= W - 1)
        & (qy >= 0.0) & (qy <= H - 1)
    )

    f21_q = _sample_flow(f21, qx, qy)
    q2x = qx + f21_q[0]
    q2y = qy + f21_q[1]
    composed_in = (
        (q2x >= 0.0) & (q2x <= W - 1)
        & (q2y >= 0.0) & (q2y <= H - 1)
    )

    direct_x = x + f20[0]
    direct_y = y + f20[1]
    direct_in = (
        (direct_x >= 0.0) & (direct_x <= W - 1)
        & (direct_y >= 0.0) & (direct_y <= H - 1)
    )

    finite = (
        torch.isfinite(f10).all(dim=0)
        & torch.isfinite(f21_q).all(dim=0)
        & torch.isfinite(f20).all(dim=0)
    )
    valid = static_fb_mask.bool() & q_in & composed_in & direct_in & finite
    return torch.linalg.norm(f20, dim=0), valid


class M5CrossSystemReliability:
    """Frozen-ECDF direct-flow confidence with a persistent RAFT model."""

    def __init__(
        self,
        reference_file,
        raft_model="pretrained/raft-things.pth",
        device="cuda:0",
        eps=1e-3,
        min_pixels=500,
        raft_iters=20,
    ):
        self.reference_file = Path(reference_file).expanduser()
        self.device = torch.device(device)
        self.eps = float(eps)
        self.min_pixels = max(int(min_pixels), 1)
        self.raft_iters = int(raft_iters)

        with self.reference_file.open("r") as f:
            ref = json.load(f)
        if ref.get("method") != "m5_direct_flow_ecdf_reference_v1":
            raise ValueError(
                "Expected m5_direct_flow_ecdf_reference_v1, got "
                f"{ref.get('method')!r}"
            )
        values = [float(v) for v in ref.get("sorted_direct_flow_median_px", [])]
        if len(values) < 20:
            raise ValueError("M5 reference needs at least 20 direct-flow values")
        if values != sorted(values):
            raise ValueError("M5 reference values must be sorted")
        self.values = values
        self.n = len(values)

        args = _RaftArgs(raft_model)
        model = torch.nn.DataParallel(RAFT(args))
        model.load_state_dict(torch.load(args.model, map_location="cpu"))
        self.raft = model.module.to(self.device)
        self.raft.eval()

    def ecdf(self, direct_flow_median_px):
        idx = bisect.bisect_right(self.values, float(direct_flow_median_px))
        return float(idx / self.n)

    def confidence_from_direct_flow(self, direct_flow_median_px):
        q = self.ecdf(direct_flow_median_px)
        return q, max(1.0 - q, self.eps)

    @torch.no_grad()
    def _flow(self, image_from, image_to):
        """RAFT flow from image_from to image_to in pixel units [2,H,W]."""
        a = image_from.to(self.device).detach() * 255.0
        b = image_to.to(self.device).detach() * 255.0
        a, b = a[None], b[None]
        padder = InputPadder(a.shape)
        a_pad, b_pad = padder.pad(a, b)
        _, flow = self.raft(a_pad, b_pad, iters=self.raft_iters, test_mode=True)
        return padder.unpad(flow[0])

    @torch.no_grad()
    def evaluate_images(self, image_t, image_tm1, image_tm2, static_mask):
        f10 = self._flow(image_t, image_tm1)
        f01 = self._flow(image_tm1, image_t)
        f21 = self._flow(image_tm1, image_tm2)
        f20 = self._flow(image_t, image_tm2)

        fb_valid = fb_valid_mask(f10, f01)
        static = static_mask.to(device=f10.device, dtype=torch.bool)
        static_fb = static & fb_valid

        direct_mag, valid = direct_flow_on_temporal_support(
            f10, f21, f20, static_fb
        )
        n = int(valid.sum().item())
        out = {
            "valid": n >= self.min_pixels,
            "num_valid_pixels": n,
            "direct_flow_median_px": None,
            "training_ecdf": None,
            "confidence": 0.5,
            "fb_valid_pixels": int(fb_valid.sum().item()),
            "static_fb_pixels": int(static_fb.sum().item()),
        }
        if n < self.min_pixels:
            return out

        d = float(direct_mag[valid].median().cpu())
        q, confidence = self.confidence_from_direct_flow(d)
        out.update(
            {
                "direct_flow_median_px": d,
                "training_ecdf": q,
                "confidence": confidence,
            }
        )
        return out

    def save(self, payload, frame, save_dir):
        out_dir = Path(save_dir) / "m5_flow_reliability"
        out_dir.mkdir(parents=True, exist_ok=True)
        d = dict(payload)
        d.update(
            {
                "method": "m5_cross_system_direct_flow_v1",
                "frame": int(frame),
                "reference_file": str(self.reference_file),
            }
        )
        torch.save(d, out_dir / f"{int(frame):06d}.pt")
