#!/usr/bin/env python3
"""Summarize cross-system M5-C opacity initialization."""

import argparse
import csv
import math
from pathlib import Path
import numpy as np


def f(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else float("nan")
    except Exception:
        return float("nan")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv_path",type=Path)
    args=ap.parse_args()

    with args.csv_path.open(newline="") as fp:
        rows=list(csv.DictReader(fp))
    if not rows:
        raise RuntimeError(f"No rows in {args.csv_path}")

    applied=[r for r in rows if int(r["m5c_applied"])==1]
    alpha=np.asarray([f(r["alpha_init"]) for r in rows],dtype=np.float64)

    print("file:",args.csv_path)
    print("rows:",len(rows))
    print("m5c_applied_rows:",len(applied))
    print("m5c_applied_fraction:",len(applied)/len(rows))
    print(
        "alpha min/median/max:",
        float(np.nanmin(alpha)),
        float(np.nanmedian(alpha)),
        float(np.nanmax(alpha)),
    )
    if applied:
        aa=np.asarray([f(r["alpha_init"]) for r in applied],dtype=np.float64)
        cc=np.asarray([f(r["m5_confidence"]) for r in applied],dtype=np.float64)
        dd=np.asarray([f(r["direct_flow_median_px"]) for r in applied],dtype=np.float64)
        print(
            "applied alpha min/median/max:",
            float(np.nanmin(aa)),float(np.nanmedian(aa)),float(np.nanmax(aa)),
        )
        print(
            "confidence min/median/max:",
            float(np.nanmin(cc)),float(np.nanmedian(cc)),float(np.nanmax(cc)),
        )
        print(
            "direct flow min/median/max:",
            float(np.nanmin(dd)),float(np.nanmedian(dd)),float(np.nanmax(dd)),
        )
        print("attenuated_rows:",int(np.sum(aa < 0.5)))


if __name__=="__main__":
    main()
