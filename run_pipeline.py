"""
Run the full analysis pipeline in dependency order.

    python3 run_pipeline.py

Stage numbers follow the order the stages were written, not the order they
must run in: stage 7 (the conclusion) reads the outputs of stages 8-11 and
14, so it runs after them. Stops at the first stage that fails.
"""
import subprocess
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent / "analysis"

ORDER = [
    "stage1_build_graphs.py",
    "stage2_structural.py",
    "stage3_centrality.py",
    "stage4_community.py",
    "stage5_cross_dept.py",
    "stage6_visualization.py",
    "stage8_temporal_slices.py",
    "stage9_temporal_structural.py",
    "stage10_temporal_bursts.py",
    "stage11_temporal_visualization.py",
    "stage14_daily_rhythm.py",
    "stage7_conclusion.py",
    "stage12_export_gephi.py",
    "stage13_export_gephi_dynamic.py",
]

for script in ORDER:
    print(f"── {script}", flush=True)
    result = subprocess.run([sys.executable, str(ANALYSIS / script)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:], file=sys.stderr)
        sys.exit(f"{script} failed")

print("\nAll stages finished. Outputs are in analysis/; the summary is analysis/conclusion.txt.")
