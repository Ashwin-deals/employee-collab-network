"""
Stage 5: Merge structural + community metrics into one cross-department
comparison table to support interpretation.
"""
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent

structural = pd.read_csv(OUT_DIR / "structural_comparison.csv", index_col="Department")
community = pd.read_csv(OUT_DIR / "community_summary.csv", index_col="Department")

merged = structural.join(community[["Num sub-communities", "Modularity (Q)",
                                     "Largest community (% nodes)"]])

# fragmentation ratio: communities found per weakly-connected component
merged["Communities per WCC"] = (merged["Num sub-communities"] /
                                  merged["Weakly conn. components"]).round(2)

pd.set_option("display.width", 160)
print(merged.to_string())

merged.to_csv(OUT_DIR / "cross_department_master.csv")
print("\nSaved analysis/cross_department_master.csv")
