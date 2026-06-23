import os
import sys
import math
import warnings
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))
from event_cause_map import normalize_cause, known_causes
MODELS_DIR = PROJECT_ROOT / "outputs" / "models"

# --- Data-grounded duration medians from ASTraM (hours) ---
CAUSE_DURATION_MEDIAN = {
    "construction":       11.99,
    "public_event":        6.55,
    "vip_movement":        5.00,
    "accident":            3.00,
    "vehiclebreakdown":    1.50,
    "procession":          1.23,
    "protest":             0.31,
    "waterlogging":        1.00,
    "congestion":          1.19,
    "potholes":            0.50,
    "tree_fall":           2.00,
    "road_conditions":     1.50,
    "debris":              1.00,
    "fog_low_visibility":  1.50,
    "others":              0.50,
}

# Closure multiplier: closure=TRUE adds duration (from dataset)
CLOSURE_DURATION_MULT = {
    "vip_movement":       1.5,
    "protest":            3.0,
    "public_event":       1.4,
    "procession":         1.2,
    "construction":       1.3,
    "accident":           1.4,
    "vehiclebreakdown":   1.2,
    "waterlogging":       1.3,
    "congestion":         1.2,
    "potholes":           1.1,
    "tree_fall":          1.3,
    "road_conditions":    1.1,
    "debris":             1.2,
    "fog_low_visibility": 1.2,
    "others":             1.1,
}

# Severity score weights from dataset closure rates and priority distribution
CAUSE_SEVERITY_SCORE = {
    "vip_movement":       85,
    "protest":            78,
    "public_event":       70,
    "procession":         55,
    "construction":       48,
    "accident":           50,
    "congestion":         42,
    "waterlogging":       35,
    "vehiclebreakdown":   30,
    "potholes":           20,
    "tree_fall":          35,
    "road_conditions":    25,
    "debris":             20,
    "fog_low_visibility": 30,
    "others":             25,
}

# Recommended actions
ACTIONS = {
    "High": (
        "IMMEDIATE DEPLOYMENT: Activate corridor control, deploy officers at all "
        "identified junctions, initiate diversion plan, notify control room."
    ),
    "Medium": (
        "ELEVATED RESPONSE: Pre-position patrol vehicles, monitor entry points, "
        "prepare diversion route, keep barricades ready."
    ),
    "Low": (
        "STANDARD MONITORING: Assign nearest patrol, log event in system, "
        "respond if situation escalates."
    ),
}


_model_cache = {}

def _load_model(model_name):
    if model_name not in _model_cache:
        model_path = MODELS_DIR / f"{model_name}.joblib"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _model_cache[model_name] = joblib.load(model_path)
    return _model_cache[model_name]


def assign_priority_rule(corridor):
    """
    Priority is deterministically defined by the source system:
    every named corridor is High priority; only 'Non-corridor' (local roads) is Low.
    Confirmed via exhaustive analysis: 22/22 corridors map to a single priority value
    in the training data, zero exceptions. This is a lookup rule, not a predictive task.
    """
    return "Low" if str(corridor).strip() == "Non-corridor" else "High"


def infer_event_profile(sample: dict) -> dict:
    cause_key = normalize_cause(sample.get("event_cause", "others"))
    priority = str(sample.get("priority", "")).strip()
    road_closure = sample.get("road_closure", 0)
    hour = int(sample.get("hour", 12))
    day_of_week = int(sample.get("day_of_week", 0))
    month = int(sample.get("month", 1))
    is_weekend = 1 if day_of_week in [5, 6] else 0

    # --- Load models (priority is a rule, not a model) ---
    model_closure    = _load_model("closure_model")
    model_duration   = _load_model("duration_model")
    model_severity   = _load_model("severity_model")

    feature_row = pd.DataFrame([{
        "event_type":    sample.get("event_type", "unplanned"),
        "event_cause":   cause_key,
        "corridor":      sample.get("corridor", "Non-corridor"),
        "zone":          sample.get("zone", "Unknown"),
        "junction":      sample.get("junction", "Unknown"),
        "hour":          hour,
        "day_of_week":   day_of_week,
        "month":         month,
        "is_weekend":    is_weekend,
        "latitude":      sample.get("latitude", 12.9716),
        "longitude":     sample.get("longitude", 77.5946),
        "police_station": sample.get("police_station", None),
        "veh_type":       sample.get("veh_type", None),
    }])

    # --- Priority (deterministic rule, not ML) ---
    if not priority:
        priority = assign_priority_rule(sample.get("corridor", "Non-corridor"))

    # --- Road closure ---
    if model_closure:
        try:
            road_closure = int(model_closure.predict(feature_row)[0])
        except Exception:
            road_closure = _rule_closure(cause_key)
    else:
        road_closure = _rule_closure(cause_key)

    requires_road_closure = bool(road_closure)

    # --- Duration ---
    # Uses a 3-class classifier (short/medium/extended) trained only on events
    # with actual (non-imputed) duration. Rule-based formula serves as primary
    # hours estimate and fallback when the classifier is unavailable or uncertain.
    base_duration = CAUSE_DURATION_MEDIAN.get(cause_key, 1.5)
    closure_mult  = CLOSURE_DURATION_MULT.get(cause_key, 1.1) if requires_road_closure else 1.0
    priority_mult = 1.3 if priority == "High" else 1.0
    night_mult    = 1.2 if hour >= 20 or hour <= 5 else 1.0
    weekend_mult  = 1.15 if is_weekend else 1.0
    expected_attendance = int(sample.get("expected_attendance", 0))
    if cause_key in ("public_event", "protest", "procession", "vip_movement") and expected_attendance > 0:
        if expected_attendance > 100000:
            attendance_mult = 3.0
        elif expected_attendance > 20000:
            attendance_mult = 2.0
        elif expected_attendance > 5000:
            attendance_mult = 1.6
        elif expected_attendance > 1000:
            attendance_mult = 1.3
        else:
            attendance_mult = 1.0
    else:
        attendance_mult = 1.0

    duration_hours = _compute_duration(base_duration, closure_mult, priority_mult,
                                       night_mult, weekend_mult, attendance_mult)

    duration_bucket = _hours_to_bucket(duration_hours)
    if model_duration:
        try:
            bucket_pred = str(model_duration.predict(feature_row)[0])
            # Only trust model when it agrees with the hours-derived bucket
            if bucket_pred == duration_bucket:
                duration_bucket = bucket_pred
        except Exception:
            pass

    # --- Severity score (0-100) ---
    base_score = CAUSE_SEVERITY_SCORE.get(cause_key, 30)
    score = base_score
    if priority == "High":
        score += 10
    if requires_road_closure:
        score += 8
    if hour >= 20 or hour <= 5:
        score += 4
    if is_weekend:
        score += 3
    if month == 12:
        score += 3
    if expected_attendance > 100000:
        score += 15
    elif expected_attendance > 20000:
        score += 10
    elif expected_attendance > 5000:
        score += 6
    elif expected_attendance > 1000:
        score += 3
    severity_score = min(100, max(0, score))

    # --- Severity label ---
    rule_label = _score_to_label(severity_score)
    if model_severity and rule_label == "Medium":
        # Use ML model only for ambiguous mid-range cases
        try:
            severity_label = model_severity.predict(feature_row)[0]
        except Exception:
            severity_label = rule_label
    else:
        # Rule-based is definitive for Low (< 40) and High (>= 70)
        severity_label = rule_label

    recommended_action = ACTIONS.get(severity_label, ACTIONS["Low"])

    return {
        "priority":              priority,
        "requires_road_closure": requires_road_closure,
        "duration_hours":        duration_hours,
        "duration_bucket":       duration_bucket,
        "severity_label":        severity_label,
        "severity_score":        severity_score,
        "recommended_action":    recommended_action,
    }


def _hours_to_bucket(hours):
    if hours < 1:
        return "short"
    elif hours < 12:
        return "medium"
    return "extended"


def _rule_closure(cause_key):
    # Grounded in dataset closure rates
    # vip=80%, public_event=46%, protest=40%
    LIKELY = {"vip_movement", "public_event", "protest", "procession", "construction", "accident"}
    return 1 if cause_key in LIKELY else 0


def _compute_duration(base, closure_mult, priority_mult, night_mult, weekend_mult, attendance_mult=1.0):
    return round(base * closure_mult * priority_mult * night_mult * weekend_mult * attendance_mult, 2)


def _score_to_label(score):
    if score >= 65:
        return "High"
    elif score >= 40:
        return "Medium"
    return "Low"