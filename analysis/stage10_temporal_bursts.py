"""
Stage 10: Burst Detection
Identifies months where email volume exceeds (mean + Z_THRESH * std) within
each department — signalling an unusual spike in communication activity.
Uses a rolling window to compute a local baseline so slow long-term trends
don't mask short bursts.

Reads:   temporal_structural_evolution.csv
Outputs: temporal_bursts.csv
         columns: Department, Month, MonthIdx, EmailVolume,
                  RollingMean, RollingStd, ZScore, IsBurst
"""
from pathlib import Path

import pandas as pd
import numpy as np

OUT_DIR   = Path(__file__).resolve().parent
Z_THRESH  = 1.0      # standard deviations above rolling mean → high-activity month
WINDOW    = 5        # rolling window width (months), min_periods=3

df = pd.read_csv(OUT_DIR / "temporal_structural_evolution.csv")

burst_rows = []

for dept, grp in df.groupby("Department"):
    grp = grp.sort_values("MonthIdx").copy()

    # exclude trailing zero-volume months (end of observation period, not real gaps)
    active = grp[grp["EmailVolume"] > 0].copy()
    vol    = active["EmailVolume"].astype(float)

    rolling_mean = vol.rolling(WINDOW, min_periods=3, center=True).mean()
    rolling_std  = vol.rolling(WINDOW, min_periods=3, center=True).std()

    global_mean = vol.mean()
    global_std  = vol.std()
    rolling_mean = rolling_mean.fillna(global_mean)
    rolling_std  = rolling_std.fillna(global_std).replace(0, global_std)

    z_scores  = (vol - rolling_mean) / rolling_std
    is_burst  = z_scores >  Z_THRESH
    is_quiet  = z_scores < -Z_THRESH

    for _, row in grp.iterrows():
        i = row.name
        if i in active.index:
            rm  = rolling_mean[i]
            rs  = rolling_std[i]
            z   = z_scores[i]
            ib  = bool(is_burst[i])
            iq  = bool(is_quiet[i])
        else:
            rm = rs = z = 0.0
            ib = iq = False
        burst_rows.append({
            "Department":   dept,
            "Month":        row["Month"],
            "MonthIdx":     int(row["MonthIdx"]),
            "EmailVolume":  int(row["EmailVolume"]),
            "RollingMean":  round(rm, 1),
            "RollingStd":   round(rs, 1),
            "ZScore":       round(z, 3),
            "IsBurst":      ib,
            "IsQuiet":      iq,
        })

result = pd.DataFrame(burst_rows)
result.to_csv(OUT_DIR / "temporal_bursts.csv", index=False)

# summary
for dept, grp in result.groupby("Department"):
    high   = grp[grp["IsBurst"]]
    quiet  = grp[grp["IsQuiet"] & (grp["EmailVolume"] > 0)]
    print(f"{dept}:  high-activity (Z>{Z_THRESH}): {list(high['Month'])}  |  "
          f"low-activity (Z<-{Z_THRESH}): {list(quiet['Month'])}")

print("\nSaved analysis/temporal_bursts.csv")
