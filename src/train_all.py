"""
train_all.py — Unified training pipeline for 3 models.
Run this once after features.py to train and save all models.

Priority is NOT modeled here — it is a deterministic rule (every named
corridor = High, 'Non-corridor' = Low), confirmed by exhaustive analysis
of all 22 corridors in the training data (100% pure mapping, zero exceptions).
Handled by infer_event_profile.assign_priority_rule().

Models trained:
  1. closure_model.joblib      — Road closure classifier
  2. duration_model.joblib     — Event duration bucket classifier (short/medium/extended)
                               Trained ONLY on actual (non-imputed) duration records.
                               Public_event & vip_movement fall back to rule-based formula.
  3. severity_model.joblib     — Severity label classifier (High/Medium/Low)

All saved to: outputs/models/
Metrics saved to: outputs/metrics.txt
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, accuracy_score, f1_score,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from config import OUTPUT_DIR

DATA_FILE = OUTPUT_DIR / "processed_theme3.csv"
MODEL_DIR = OUTPUT_DIR / "models"
METRICS_FILE = OUTPUT_DIR / "metrics.txt"

# NOTE: junction excluded from all models — 95/96 junctions map to a single
# fixed priority value in the training data (near row-ID leak / too high
# cardinality for 807 rows). corridor/zone are kept since they generalize
# across many junctions.
CAT_FEATURES = ["event_cause", "corridor", "zone", "police_station", "veh_type"]
NUM_FEATURES_BASE = ["latitude", "longitude", "hour", "day_of_week", "month", "is_weekend"]


def build_preprocessor(cat_cols, num_cols):
    return ColumnTransformer(transformers=[
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), num_cols),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]), cat_cols),
    ])


def load_data():
    df = pd.read_csv(DATA_FILE)
    print(f"Loaded processed dataset: {df.shape[0]} rows, {df.shape[1]} cols")
    return df


def train_closure(df, metrics_lines):
    print("\n--- [1/3] Training closure_model ---")
    target = "road_closure"
    num_cols = NUM_FEATURES_BASE + ["duration_hours"]
    cat_cols = list(CAT_FEATURES)

    df_clean = df.dropna(subset=[target])
    X = df_clean[num_cols + cat_cols]
    y = df_clean[target].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("prep", build_preprocessor(cat_cols, num_cols)),
        ("model", RandomForestClassifier(n_estimators=250, max_depth=12,
                                         min_samples_split=5, min_samples_leaf=2,
                                         class_weight="balanced",
                                         random_state=42, n_jobs=-1))
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="weighted")
    print(f"  Accuracy: {acc:.4f}  |  F1: {f1:.4f}")
    print(classification_report(y_test, preds))

    path = MODEL_DIR / "closure_model.joblib"
    joblib.dump(pipeline, path)
    print(f"  Saved: {path}")

    metrics_lines.append(f"[closure_model]   Accuracy={acc:.4f}  F1={f1:.4f}")
    metrics_lines.append(classification_report(y_test, preds))
    return pipeline


def train_duration(df, metrics_lines):
    print("\n--- [2/3] Training duration_model ---")
    # Regression on hours is unreliable: 80% of duration targets are imputed
    # (median = 8.12 hrs) and extreme outliers reach 3039 hrs.
    # Switching to 3-class classifier trained only on actual (non-imputed)
    # duration records. Public_event and vip_movement have ZERO actual duration
    # records — they are handled by rule-based fallback at inference time.
    target = "duration_bucket"
    num_cols = list(NUM_FEATURES_BASE)
    cat_cols = list(CAT_FEATURES)

    df_actual = df[df["duration_known"] == 1].copy()
    print(f"  Training on {len(df_actual)} events with actual (non-imputed) duration "
          f"({len(df) - len(df_actual)} events with imputed duration excluded)")

    if len(df_actual) == 0:
        print("  WARNING: No actual duration records. Skipping duration model training.")
        metrics_lines.append("[duration_model]  SKIPPED — no actual duration records")
        return None

    X = df_actual[num_cols + cat_cols]
    y = df_actual[target].astype(str)

    # Use stratified split since classes are imbalanced
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("prep", build_preprocessor(cat_cols, num_cols)),
        ("model", RandomForestClassifier(n_estimators=200, max_depth=8,
                                         min_samples_split=5, min_samples_leaf=3,
                                         class_weight="balanced",
                                         random_state=42, n_jobs=-1))
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="weighted")
    print(f"  Accuracy: {acc:.4f}  |  Weighted F1: {f1:.4f}")
    print(classification_report(y_test, preds))
    print(f"  Classes: {sorted(y.unique())}")

    path = MODEL_DIR / "duration_model.joblib"
    joblib.dump(pipeline, path)
    print(f"  Saved: {path}")

    metrics_lines.append(f"[duration_model]  Accuracy={acc:.4f}  F1={f1:.4f}  "
                         f"(3-class classifier on {len(df_actual)} actual-duration rows)")
    metrics_lines.append(classification_report(y_test, preds))
    return pipeline


def train_severity(df, metrics_lines):
    print("\n--- [3/3] Training severity_model ---")
    target = "severity_label"
    # NOTE: road_closure, priority, and duration_hours are intentionally excluded
    # here. The severity label is derived FROM these fields in features.py,
    # so including them would let the model reverse-engineer the formula
    # (circular reasoning). The model must learn to predict severity solely
    # from event properties (cause, location, time).
    num_cols = list(NUM_FEATURES_BASE)
    cat_cols = list(CAT_FEATURES)

    df_clean = df.dropna(subset=[target])
    X = df_clean[num_cols + cat_cols]
    y = df_clean[target].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("prep", build_preprocessor(cat_cols, num_cols)),
        ("model", RandomForestClassifier(n_estimators=250, max_depth=12,
                                         min_samples_split=5, min_samples_leaf=2,
                                         class_weight="balanced",
                                         random_state=42, n_jobs=-1))
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="weighted")
    print(f"  Accuracy: {acc:.4f}  |  F1: {f1:.4f}")
    print(classification_report(y_test, preds))

    path = MODEL_DIR / "severity_model.joblib"
    joblib.dump(pipeline, path)
    print(f"  Saved: {path}")

    metrics_lines.append(f"[severity_model]  Accuracy={acc:.4f}  F1={f1:.4f}")
    metrics_lines.append(classification_report(y_test, preds))
    return pipeline


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        print(f"ERROR: Processed data not found at {DATA_FILE}")
        print("Run features.py first.")
        sys.exit(1)

    df = load_data()
    metrics_lines = ["=" * 60, "MODEL TRAINING METRICS", "=" * 60, ""]
    metrics_lines.append(
        "[priority] NOT MODELED — priority is a deterministic rule: "
        "every named corridor = High, 'Non-corridor' = Low (confirmed 100% pure "
        "mapping across all 22 corridors in training data). Handled in "
        "infer_event_profile.assign_priority_rule()."
    )
    metrics_lines.append("")

    train_closure(df, metrics_lines)
    train_duration(df, metrics_lines)
    train_severity(df, metrics_lines)

    METRICS_FILE.write_text("\n".join(metrics_lines))
    print(f"\n{'='*60}")
    print(f"All 3 models trained and saved to: {MODEL_DIR}")
    print(f"Priority handled by rule (no model needed) — see metrics.txt")
    print(f"Metrics saved to: {METRICS_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()