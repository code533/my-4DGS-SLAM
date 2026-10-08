#!/usr/bin/env python3
"""Validate and copy the frozen M5 direct-flow ECDF reference into this repo."""

import argparse
import json
import math
import shutil
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path,help="Existing m5_direct_flow_reference.json from my-Flow4dgs")
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("results/m5_direct_flow_reference.json"),
    )
    args=ap.parse_args()

    ref=json.loads(args.source.read_text())
    if ref.get("method")!="m5_direct_flow_ecdf_reference_v1":
        raise ValueError(
            f"Unexpected method {ref.get('method')!r}; "
            "expected m5_direct_flow_ecdf_reference_v1"
        )
    vals=[float(v) for v in ref.get("sorted_direct_flow_median_px",[])]
    if len(vals)<20:
        raise ValueError("Reference contains too few direct-flow values")
    if vals!=sorted(vals):
        raise ValueError("Reference direct-flow values are not sorted")
    if any((not math.isfinite(v)) or v<0 for v in vals):
        raise ValueError("Reference values must be finite and non-negative")

    args.output.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(args.source,args.output)

    print("Saved",args.output)
    print("method",ref["method"])
    print("n",len(vals))
    print("min/median/max",vals[0],vals[len(vals)//2],vals[-1])
    print("development_sequences",ref.get("development_sequences"))


if __name__=="__main__":
    main()
