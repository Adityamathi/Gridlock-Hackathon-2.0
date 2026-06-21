import pandas as pd
from config import OUTPUT_DIR

PROCESSED_FILE = OUTPUT_DIR / "processed_theme3.csv"
FEEDBACK_FILE = OUTPUT_DIR / "event_feedback_log.csv"
MERGED_FILE = OUTPUT_DIR / "retraining_dataset.csv"

def build_retraining_dataset():
    base_df = pd.read_csv(PROCESSED_FILE)

    if not FEEDBACK_FILE.exists():
        print("No feedback log found. Using only base processed dataset.")
        base_df.to_csv(MERGED_FILE, index=False)
        print(f"Saved: {MERGED_FILE}")
        return

    feedback_df = pd.read_csv(FEEDBACK_FILE)

    # Split feedback into rows WITH ground truth and WITHOUT
    has_truth = feedback_df["actual_severity_label"].notna() & (feedback_df["actual_severity_label"] != "")
    truth_df = feedback_df[has_truth].copy()
    pending_df = feedback_df[~has_truth].copy()

    print(f"Feedback log: {len(feedback_df)} total, {len(truth_df)} with ground truth, {len(pending_df)} pending")

    # Build enriched training rows from ground-truth feedback
    if len(truth_df) > 0:
        truth_df = truth_df.rename(columns={
            "predicted_severity_label": "severity_label",
            "predicted_severity_score": "severity_score"
        })

        # Use actual values where available, fall back to predictions
        truth_df["severity_label"] = truth_df.apply(
            lambda r: r["actual_severity_label"] if pd.notna(r.get("actual_severity_label")) and r.get("actual_severity_label") != "" else r["severity_label"],
            axis=1
        )
        truth_df["duration_hours"] = truth_df.apply(
            lambda r: float(str(r["actual_duration_hours"])) if pd.notna(r.get("actual_duration_hours")) and str(r.get("actual_duration_hours")).strip() != "" else 1.0,
            axis=1
        )
        truth_df["duration_bucket"] = truth_df.apply(
            lambda r: r["actual_duration_bucket"] if pd.notna(r.get("actual_duration_bucket")) and r.get("actual_duration_bucket") != "" else "medium",
            axis=1
        )

        truth_df["is_high_priority"] = (truth_df["priority"] == "High").astype(int)
        truth_df["road_closure"] = pd.to_numeric(truth_df["requires_road_closure"], errors="coerce").fillna(0).astype(int)
        truth_df["id"] = -1

        # Keep only columns that match the base dataset
        common_cols = base_df.columns.intersection(truth_df.columns).tolist()
        truth_df = truth_df[common_cols]

        merged = pd.concat([base_df, truth_df], ignore_index=True)
        print(f"Base rows: {len(base_df)}")
        print(f"Ground-truth feedback rows added: {len(truth_df)}")
        print(f"Merged rows: {len(merged)}")
    else:
        merged = base_df
        print("No ground-truth feedback available. Using only base dataset.")

    merged.to_csv(MERGED_FILE, index=False)
    print(f"Saved: {MERGED_FILE}")

    # Also train resource models from feedback data
    try:
        from train_resource_model import train_and_save_resource_models
        print("\n--- Training resource models from feedback data ---")
        metrics = train_and_save_resource_models()
        print(f"Resource models trained: {metrics}")
    except Exception as e:
        print(f"Resource model training skipped: {e}")

if __name__ == "__main__":
    build_retraining_dataset()
