import pandas as pd
import numpy as np

from config import OUTPUT_DIR
from load_data import load_dataset
from event_cause_map import normalize_cause, known_causes, cause_group

def build_features():
    df = load_dataset().copy()

    # Normalize event cause to standardized keys
    df["event_cause"] = df["event_cause"].apply(normalize_cause)

    # Filter out noise (test_demo, others) but keep everything else
    df = df[df["event_cause"].isin(known_causes())].copy()

    df["hour"] = df["start_datetime"].dt.hour
    df["day_of_week"] = df["start_datetime"].dt.dayofweek
    df["month"] = df["start_datetime"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    df["duration_hours"] = (
        (df["closed_datetime"] - df["start_datetime"]).dt.total_seconds() / 3600
    )

    df["duration_hours"] = df["duration_hours"].clip(lower=0)
    df["duration_known"] = df["duration_hours"].notna().astype(int)
    df["duration_hours"] = df["duration_hours"].fillna(df["duration_hours"].median())

    def duration_bucket(h):
        if h < 1:
            return "short"
        elif h < 12:
            return "medium"
        else:
            return "extended"
    df["duration_bucket"] = df["duration_hours"].apply(duration_bucket)

    df["is_high_priority"] = (df["priority"] == "High").astype(int)
    df["road_closure"] = df["requires_road_closure"].astype(int)

    # LABELLING HEURISTIC: severity is derived from road_closure, priority,
    # event_cause, and duration_hours. IMPORTANT: the ML model that predicts
    # severity_label must NOT use road_closure, priority, or duration_hours as
    # features — doing so would let it reverse-engineer this formula instead
    # of learning from actual event properties (cause, location, time).
    df["severity_score"] = (
        40 * df["road_closure"] +
        25 * df["is_high_priority"] +
        15 * (df["event_cause"].isin(["vip_movement", "public_event", "protest"])).astype(int) +
        20 * (df["duration_hours"] > 2).astype(int)
    )

    df["severity_score"] = df["severity_score"].clip(0, 100)

    def severity_label(score):
        if score >= 70:
            return "High"
        elif score >= 40:
            return "Medium"
        return "Low"

    df["severity_label"] = df["severity_score"].apply(severity_label)

    keep_cols = [
        "id",
        "event_type",
        "event_cause",
        "start_datetime",
        "latitude",
        "longitude",
        "corridor",
        "zone",
        "junction",
        "priority",
        "requires_road_closure",
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
        "duration_hours",
        "duration_known",
        "duration_bucket",
        "is_high_priority",
        "road_closure",
        "severity_score",
        "severity_label",
        "police_station",
        "veh_type"
    ]

    df = df[keep_cols].copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "processed_theme3.csv"
    df.to_csv(output_file, index=False)

    print("Processed shape:", df.shape)
    print("Saved to:", output_file)
    print("Event causes:", df["event_cause"].value_counts().to_dict())
    print(df["severity_label"].value_counts())

if __name__ == "__main__":
    build_features()
