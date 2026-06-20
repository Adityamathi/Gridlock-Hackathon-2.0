"""
train_resource_model.py — Data-driven resource optimization models.

Trains 3 RandomForest regressors from feedback log data:
  1. officer_model.joblib   → predicts officers_required
  2. barricade_model.joblib → predicts barricades_required
  3. patrol_model.joblib    → predicts patrol_vehicles_required

When actual resource ground truth exists, the model learns from real outcomes.
Otherwise, it learns the rule-based mapping, enabling non-linear interactions
and smooth generalization across event causes, severity, and attendance levels.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from config import OUTPUT_DIR

FEEDBACK_FILE = OUTPUT_DIR / "event_feedback_log.csv"
MODEL_DIR = OUTPUT_DIR / "models"

TARGETS = {
    "officers":  ("officers_required",  "actual_officers_used"),
    "barricades": ("barricades_required", "actual_barricades_used"),
    "patrols":  ("patrol_vehicles_required", "actual_patrols_used"),
}

FEATURE_COLS = [
    "event_type", "event_cause", "corridor", "zone",
    "hour", "day_of_week", "month", "is_weekend",
    "priority", "requires_road_closure", "expected_attendance",
    "predicted_severity_score",
]


def _safe_float(val):
    try:
        f = float(val)
        return f if np.isfinite(f) else np.nan
    except (ValueError, TypeError):
        return np.nan


def _safe_int(val):
    try:
        f = float(val)
        return int(f) if np.isfinite(f) else np.nan
    except (ValueError, TypeError):
        return np.nan


def load_training_data():
    if not FEEDBACK_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(FEEDBACK_FILE)

    # Ensure feature columns exist
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"  WARNING: Missing feature columns: {missing}")
        return pd.DataFrame()

    # Convert numeric features
    for col in ["hour", "day_of_week", "month", "is_weekend", "expected_attendance",
                "predicted_severity_score"]:
        df[col] = df[col].apply(_safe_float)

    # Fill missing required_road_closure (default False)
    df["requires_road_closure"] = df["requires_road_closure"].apply(
        lambda x: 1 if str(x).lower() in ("true", "1", "yes") else 0
    )

    return df


def build_preprocessor():
    cat_cols = ["event_type", "event_cause", "corridor", "zone", "priority"]
    num_cols = ["hour", "day_of_week", "month", "is_weekend",
                "requires_road_closure", "expected_attendance",
                "predicted_severity_score"]
    return ColumnTransformer(transformers=[
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
        ]), num_cols),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), cat_cols),
    ])


def _build_target(df, pred_col, actual_col):
    """
    Build target array: use actual ground truth where available,
    otherwise fall back to predicted values.
    """
    targets = df[pred_col].apply(_safe_float).values.copy()
    if actual_col in df.columns:
        actuals = df[actual_col].apply(_safe_float).values
        mask = ~np.isnan(actuals)
        targets[mask] = actuals[mask]
        n_actual = int(mask.sum())
    else:
        n_actual = 0
    return targets, n_actual


def train_single_model(df, pred_col, actual_col, model_name):
    targets, n_actual = _build_target(df, pred_col, actual_col)
    valid_mask = ~np.isnan(targets)
    df_clean = df[valid_mask].copy()
    targets_clean = targets[valid_mask]

    if len(df_clean) < 10:
        print(f"  SKIPPED {model_name}: only {len(df_clean)} valid rows")
        return None, {"rows": int(len(df_clean)), "actual": n_actual}

    X = df_clean[FEATURE_COLS]
    y = targets_clean

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = Pipeline([
        ("prep", build_preprocessor()),
        ("model", RandomForestRegressor(
            n_estimators=200, max_depth=10,
            min_samples_split=5, min_samples_leaf=2,
            random_state=42, n_jobs=-1,
        )),
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    path = MODEL_DIR / f"{model_name}.joblib"
    joblib.dump(pipeline, path)

    metrics = {
        "model": model_name,
        "mae": round(mae, 2),
        "r2": round(r2, 3),
        "rows": len(df_clean),
        "actual_gt_rows": n_actual,
    }

    print(f"  {model_name}: MAE={mae:.2f}  R²={r2:.3f}  "
          f"rows={len(df_clean)} (actual_gt={n_actual})  saved={path}")
    return pipeline, metrics


def train_and_save_resource_models():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Resource Model Training")
    print("=" * 60)

    df = load_training_data()
    if len(df) == 0:
        print("  No feedback data available. Models not trained.")
        return {"error": "no feedback data"}

    print(f"  Loaded {len(df)} feedback rows, {len(df.columns)} columns")

    all_metrics = []
    for key, (pred_col, actual_col) in TARGETS.items():
        model_name = f"{key}_model"
        _, metrics = train_single_model(df, pred_col, actual_col, model_name)
        if metrics:
            all_metrics.append(metrics)

    print(f"\n  Trained {len(all_metrics)} / 3 resource models")
    print("=" * 60)

    return {"models": all_metrics, "total_feedback_rows": len(df)}


def load_resource_model(model_name):
    path = MODEL_DIR / f"{model_name}.joblib"
    if path.exists():
        return joblib.load(path)
    return None


def predict_resources(event_cause, severity_label, severity_score,
                      requires_road_closure, expected_attendance,
                      corridor, zone, priority,
                      hour=12, day_of_week=0, month=1, is_weekend=0):
    """
    Prediction helper: build a single-row DataFrame and predict via each model.
    Returns dict with officer/barricade/patrol predictions or None if models
    don't exist.
    """
    row = pd.DataFrame([{
        "event_type": "planned",
        "event_cause": event_cause,
        "corridor": corridor,
        "zone": zone,
        "hour": float(hour),
        "day_of_week": float(day_of_week),
        "month": float(month),
        "is_weekend": float(is_weekend),
        "priority": priority,
        "requires_road_closure": 1 if requires_road_closure else 0,
        "expected_attendance": float(expected_attendance),
        "predicted_severity_score": float(severity_score),
    }])

    result = {}
    for key in ["officers", "barricades", "patrols"]:
        model = load_resource_model(f"{key}_model")
        if model is None:
            result[key] = None
        else:
            try:
                pred = float(model.predict(row)[0])
                result[key] = max(1, round(pred))
            except Exception:
                result[key] = None
    return result


if __name__ == "__main__":
    train_and_save_resource_models()
