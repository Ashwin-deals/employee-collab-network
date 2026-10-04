"""
Stage 14: Daily rhythm
The monthly slices (stage 8) are 30-day bins with an arbitrary origin, so a
week-long break can be split across two months or diluted inside one. This
stage looks at daily email counts instead:

  - clock alignment: every department file starts at timestamp 0 (its own
    first email), so their clocks are offset by an unknown amount. Each one
    is cross-correlated hour by hour against the full dataset to measure
    the offset, which tells us whether month-by-month comparisons across
    departments are valid;
  - day-of-week profile: real weekdays are unknown, but a 7-day cycle with
    two near-silent days identifies the weekend. Measured on the full
    dataset, whose day boundaries fall at night (department files' day
    boundaries fall mid-day, which smears the weekend over three days);
  - low weeks: 7-day windows whose total volume (all four departments) falls
    below half the median weekly volume, merged into periods.

Only the continuous part of the data (up to the gap after ~day 527) is used.

Outputs: clock_offsets.csv, daily_volume.csv, low_weeks.csv, rhythm_summary.csv,
         fig_daily_rhythm.png
"""
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "email-Eu-core-temporal"
OUT_DIR = Path(__file__).resolve().parent
DEPTS = ["Dept1", "Dept2", "Dept3", "Dept4"]
SECONDS_PER_DAY = 86_400
SLICE_DAYS = 30
GAP_DAYS = 30          # a run of empty days at least this long ends the main window
LOW_FRACTION = 0.5     # low week = below this fraction of the median weekly volume

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SEC = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
LOW_SHADE = "#5b5ea6"
DEPT_COLOR = {"Dept1": "#2a78d6", "Dept2": "#eb6834", "Dept3": "#1baf7a", "Dept4": "#eda100"}

plt.rcParams.update({
    "font.family": "sans-serif",
    "text.color": TEXT_PRIMARY,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_SEC,
    "xtick.color": TEXT_SEC,
    "ytick.color": TEXT_SEC,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

def read_timestamps(stem):
    with open(DATA_DIR / f"{stem}.csv") as f:
        return np.array([int(line.split()[2]) for line in f if line.strip()])


ts = {dept: read_timestamps(f"email-Eu-core-temporal-{dept}") for dept in DEPTS}
ts_full = read_timestamps("email-Eu-core-temporal")

# ── daily counts per department ─────────────────────────────────────────────
counts = {dept: Counter(t // SECONDS_PER_DAY for t in ts[dept]) for dept in DEPTS}

last_day = max(max(c) for c in counts.values())
daily = pd.DataFrame({d: [counts[d].get(i, 0) for i in range(last_day + 1)] for d in DEPTS})
daily.index.name = "Day"
daily["Total"] = daily[DEPTS].sum(axis=1)

# end of the main window = last active day before the first long empty run
active_days = daily.index[daily["Total"] > 0]
gaps = np.diff(active_days)
main_end = int(active_days[np.argmax(gaps >= GAP_DAYS)]) if (gaps >= GAP_DAYS).any() else last_day
main = daily.loc[:main_end].copy()
main["Rolling7"] = main["Total"].rolling(7, center=True, min_periods=7).sum()
main["Month"] = [f"M{d // SLICE_DAYS + 1:02d}" for d in main.index]
main.to_csv(OUT_DIR / "daily_volume.csv")

print(f"Main window: days 0-{main_end} ({main_end + 1} days); "
      f"data resumes on day {int(active_days[active_days > main_end].min())}"
      if main_end < last_day else f"Main window: days 0-{main_end}")

# ── clock alignment against the full dataset ────────────────────────────────
MAX_SHIFT_H = 24 * 7
n_hours = (main_end + 1) * 24
hourly_full = np.bincount(ts_full[ts_full < n_hours * 3600] // 3600, minlength=n_hours).astype(float)
offset_rows = []
for dept in DEPTS:
    t = ts[dept]
    hourly = np.bincount(t[t < n_hours * 3600] // 3600, minlength=n_hours).astype(float)
    trim = slice(MAX_SHIFT_H, -MAX_SHIFT_H)   # ignore hours wrapped round by np.roll
    corr = {s_: np.corrcoef(np.roll(hourly, s_)[trim], hourly_full[trim])[0, 1]
            for s_ in range(-MAX_SHIFT_H, MAX_SHIFT_H + 1)}
    best = max(corr, key=corr.get)
    offset_rows.append({"Department": dept, "OffsetHours": best, "Correlation": round(corr[best], 3)})
offsets = pd.DataFrame(offset_rows).set_index("Department")
offsets.to_csv(OUT_DIR / "clock_offsets.csv")
spread = offsets["OffsetHours"].max() - offsets["OffsetHours"].min()
print("\nClock offset vs full dataset (hours to add to each department's timestamps):")
print(offsets.to_string())
print(f"Departments agree with each other to within {spread} hours")

# ── day-of-week profile (full dataset) ──────────────────────────────────────
full_days = ts_full[ts_full < (main_end + 1) * SECONDS_PER_DAY] // SECONDS_PER_DAY
full_daily = pd.Series(np.bincount(full_days, minlength=main_end + 1))
weekday = full_daily.groupby(full_daily.index % 7).mean()
weekend = weekday.nsmallest(2).index.tolist()
weekend_ratio = weekday[weekend].mean() / weekday.drop(weekend).mean()
print(f"\nDay-of-cycle means (full dataset): {weekday.round(0).astype(int).to_dict()}")
print(f"Weekend (day mod 7 in {sorted(weekend)}) volume = {100 * weekend_ratio:.0f}% of weekdays")

# ── low weeks ───────────────────────────────────────────────────────────────
threshold = LOW_FRACTION * main["Rolling7"].median()
is_low = main["Rolling7"] < threshold
# the rolling window is centred, so a low centre day d covers days d-3..d+3;
# merge windows that touch into one period
periods = []
for day in main.index[is_low]:
    start, end = max(day - 3, 0), min(day + 3, main_end)
    if periods and start <= periods[-1][1] + 1:
        periods[-1][1] = end
    else:
        periods.append([start, end])

low_rows = []
for start, end in periods:
    window = main.loc[start:end, "Total"]
    low_rows.append({
        "StartDay": start,
        "EndDay": end,
        "Months": sorted(set(main.loc[start:end, "Month"])),
        "EmailsPerDay": round(window.mean(), 1),
        "PctOfTypicalDay": round(100 * window.mean() / main["Total"].mean(), 1),
    })
low = pd.DataFrame(low_rows)
low.to_csv(OUT_DIR / "low_weeks.csv", index=False)
print(f"\nLow periods (7-day volume < {LOW_FRACTION:.0%} of median week):")
print(low.to_string(index=False))

# ── summary ─────────────────────────────────────────────────────────────────
median_week = main["Rolling7"].median()
peak_day = int(main["Rolling7"].idxmax())
annual = [(a, b) for a in low["StartDay"] for b in low["StartDay"] if 350 <= b - a <= 380]
summary = pd.Series({
    "MainWindowLastDay": main_end,
    "DataResumesDay": int(active_days[active_days > main_end].min()) if main_end < last_day else None,
    "DeptClockSpreadHours": int(spread),
    "WeekendDays": sorted(weekend),
    "WeekendPctOfWeekday": round(100 * weekend_ratio, 1),
    "MedianWeekEmails": int(median_week),
    "PeakWeekCentreDay": peak_day,
    "PeakWeekMonth": main.loc[peak_day, "Month"],
    "PeakWeekEmails": int(main.loc[peak_day, "Rolling7"]),
    "PeakWeekVsMedian": round(main.loc[peak_day, "Rolling7"] / median_week, 2),
    "LongestLowPeriodDays": int((low["EndDay"] - low["StartDay"] + 1).max()),
    "LowPeriodsAboutOneYearApart": annual,
})
summary.to_csv(OUT_DIR / "rhythm_summary.csv", header=["Value"])
print("\n" + summary.to_string())

# ── figure ──────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 4.8), gridspec_kw={"width_ratios": [4, 1]})

for _, r in low.iterrows():
    ax1.axvspan(r["StartDay"], r["EndDay"], color=LOW_SHADE, alpha=0.15, lw=0)
for b in range(SLICE_DAYS, main_end + 1, SLICE_DAYS):
    ax1.axvline(b, color=GRID, lw=0.6, zorder=0)
for m in range(0, main_end + 1, SLICE_DAYS):
    ax1.text(m + SLICE_DAYS / 2, 1.0, f"M{m // SLICE_DAYS + 1:02d}", transform=ax1.get_xaxis_transform(),
             ha="center", va="bottom", fontsize=7, color=MUTED)

ax1.plot(main.index, main["Rolling7"], color=TEXT_PRIMARY, lw=1.6, label="All four departments")
for dept in DEPTS:
    ax1.plot(main.index, main[dept].rolling(7, center=True, min_periods=7).sum(),
             color=DEPT_COLOR[dept], lw=0.9, alpha=0.8, label=dept)
ax1.set_xlim(0, main_end)
ax1.set_xlabel("Day since first email", fontsize=9)
ax1.set_ylabel("Emails in surrounding 7 days", fontsize=9)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax1.spines[["top", "right"]].set_visible(False)
ax1.legend(fontsize=8, frameon=False, ncol=5, loc="upper left", bbox_to_anchor=(0, -0.14))
ax1.set_title("Weekly email volume (shaded = low weeks, below half the median week)",
              fontsize=11, loc="left", pad=16)

bars = ax2.bar(weekday.index, weekday.values,
               color=[MUTED if d in weekend else TEXT_SEC for d in weekday.index], width=0.65)
ax2.set_xticks(weekday.index)
ax2.set_xticklabels([f"{d}" for d in weekday.index], fontsize=9)
ax2.set_xlabel("Day of 7-day cycle (day mod 7, full dataset)", fontsize=9)
ax2.set_yticks([])
ax2.spines[["top", "right", "left"]].set_visible(False)
for rect, v in zip(bars, weekday.values):
    ax2.text(rect.get_x() + rect.get_width() / 2, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8.5)
ax2.set_title(f"Avg emails per day\n(weekend ≈ {100 * weekend_ratio:.0f}% of a weekday)",
              fontsize=11, loc="left")

fig.tight_layout()
fig.savefig(OUT_DIR / "fig_daily_rhythm.png", dpi=160)
print("\nSaved analysis/daily_volume.csv, analysis/low_weeks.csv, analysis/fig_daily_rhythm.png")
