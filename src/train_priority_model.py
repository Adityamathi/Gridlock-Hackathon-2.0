"""
PRIORITY IS NOT MODELED — it is a deterministic rule confirmed by exhaustive
analysis of all 22 corridors in the ASTraM training data:
  - Every named corridor maps to High priority (100% pure mapping)
  - 'Non-corridor' maps to Low priority
  - Zero exceptions across all 807 training rows

This file exists as documentation. The logic lives in:
  infer_event_profile.assign_priority_rule()

Do NOT attempt to model priority with ML — it would overfit to corridor
names and add no value over the deterministic lookup.
"""
import pandas as pd
from config import OUTPUT_DIR

DATA_FILE = OUTPUT_DIR / "processed_theme3.csv"

def verify_priority_rule():
    df = pd.read_csv(DATA_FILE)
    violations = df[(df["corridor"] != "Non-corridor") & (df["priority"] != "High")]
    violations = pd.concat([
        violations,
        df[(df["corridor"] == "Non-corridor") & (df["priority"] != "Low")]
    ])
    if len(violations) == 0:
        print(f"✓ Priority rule CONFIRMED: {len(df)} rows, zero violations.")
        print(f"  Named corridors → High: {len(df[df['corridor'] != 'Non-corridor'])} rows")
        print(f"  Non-corridor    → Low:  {len(df[df['corridor'] == 'Non-corridor'])} rows")
    else:
        print(f"✗ Priority rule VIOLATED: {len(violations)} exceptions found")
        print(violations[["corridor", "priority"]].drop_duplicates())

if __name__ == "__main__":
    verify_priority_rule()