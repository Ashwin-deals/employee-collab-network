"""
Stage 10: Burst Detection
Identifies months where email volume exceeds (mean + Z_THRESH * std) within
each department — signalling an unusual spike in communication activity.
Uses a rolling window to compute a local baseline so slow long-term trends
don't mask short bursts.

Only complete months are analysed: the contiguous run of active months
from M01, minus its last month. The data stops at day 525, partway through
M18 (days 510-539), and resumes only for a 7-day fragment (days 797-803) in
M27. Both are partial slices whose low volume reflects missing days, not
low activity, so they are excluded rather than flagged as quiet.

Synchrony test: a |Z| > 1 cut-off flags roughly a third of months even in
random data, so one department's flags mean little on their own. The
evidence is that departments flag the same months. To test that, each
department's Z-score series is circularly shifted by an independent random
offset (keeping its own flags and month-to-month pattern but breaking the
alignment between departments), and we count how often at least as many
months are flagged in the same direction in every department as observed.

Reads:   temporal_structural_evolution.csv
Outputs: temporal_bursts.csv, temporal_synchrony.csv
         columns: Department, Month, MonthIdx, EmailVolume,
                  RollingMean, RollingStd, ZScore, IsBurst, IsQuiet,
                  InMainWindow
"""
from pathlib import Path

import pandas as pd
import numpy as np

OUT_DIR   = Path(__file__).resolve().parent
Z_THRESH  = 1.0      # standard deviations above rolling mean → high-activity month
WINDOW    = 5        # rolling window width (months), min_periods=3
N_PERM    = 10_000   # random circular shifts for the synchrony test
SEED      = 42

df = pd.read_csv(OUT_DIR / "temporal_structural_evolution.csv")

burst_rows = []

for dept, grp in df.groupby("Department"):
    grp = grp.sort_values("MonthIdx").copy()

    # main window = months before the first empty month, dropping the last one
    # because the data cuts off partway through it
    empty = grp.loc[grp["EmailVolume"] == 0, "MonthIdx"]
    last_main = (empty.min() if not empty.empty else grp["MonthIdx"].max() + 1) - 2
    active = grp[(grp["EmailVolume"] > 0) & (grp["MonthIdx"] <= last_main)].copy()
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
            "InMainWindow": i in active.index,
        })

result = pd.DataFrame(burst_rows)
result.to_csv(OUT_DIR / "temporal_bursts.csv", index=False)

# summary
for dept, grp in result.groupby("Department"):
    high   = grp[grp["IsBurst"]]
    quiet  = grp[grp["IsQuiet"]]
    print(f"{dept}:  high-activity (Z>{Z_THRESH}): {list(high['Month'])}  |  "
          f"low-activity (Z<-{Z_THRESH}): {list(quiet['Month'])}")

print("\nSaved analysis/temporal_bursts.csv")

# ── synchrony test ──────────────────────────────────────────────────────────
main = result[result["InMainWindow"]]
z = main.pivot(index="MonthIdx", columns="Department", values="ZScore").dropna()
flags = np.sign(z.values) * (np.abs(z.values) > Z_THRESH)   # +1 high, -1 low, 0 neither


def shared_months(f):
    """Months flagged in the same direction in every department."""
    return int(np.sum(np.all(f == 1, axis=1) | np.all(f == -1, axis=1)))


observed = shared_months(flags)
rng = np.random.default_rng(SEED)
n_months, n_depts = flags.shape
null = np.empty(N_PERM, dtype=int)
for i in range(N_PERM):
    shifted = np.column_stack([np.roll(flags[:, j], rng.integers(n_months)) for j in range(n_depts)])
    null[i] = shared_months(shifted)
p_value = (np.sum(null >= observed) + 1) / (N_PERM + 1)

flagged_share = float(np.mean(flags != 0))
sync = pd.Series({
    "MonthsAnalysed": n_months,
    "ShareOfMonthsFlagged": round(flagged_share, 3),
    "SharedFlaggedMonthsObserved": observed,
    "SharedFlaggedMonthsExpected": round(float(null.mean()), 2),
    "PValue": round(float(p_value), 4),
    "Permutations": N_PERM,
})
sync.to_csv(OUT_DIR / "temporal_synchrony.csv", header=["Value"])
print(f"\nSynchrony: {observed} months flagged the same way in all departments "
      f"(expected {null.mean():.2f} by chance, p = {p_value:.4f}); "
      f"{100 * flagged_share:.0f}% of department-months are flagged overall")
print("Saved analysis/temporal_synchrony.csv")
