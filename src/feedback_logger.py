import os
import tempfile
import pandas as pd
from pathlib import Path
from datetime import datetime
from config import OUTPUT_DIR

LOG_FILE = OUTPUT_DIR / "event_feedback_log.csv"

def log_prediction_event(input_data, prediction, spatial, resources, routes):
    log_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "log_timestamp": log_timestamp,
        "event_type": input_data.get("event_type"),
        "event_cause": input_data.get("event_cause"),
        "latitude": input_data.get("latitude"),
        "longitude": input_data.get("longitude"),
        "corridor": input_data.get("corridor"),
        "zone": input_data.get("zone"),
        "junction": input_data.get("junction"),
        "hour": input_data.get("hour"),
        "day_of_week": input_data.get("day_of_week"),
        "month": input_data.get("month"),
        "is_weekend": input_data.get("is_weekend"),
        "priority": input_data.get("priority"),
        "requires_road_closure": input_data.get("requires_road_closure"),
        "expected_attendance": input_data.get("expected_attendance", 0),
        "predicted_severity_label": prediction.get("severity_label"),
        "predicted_severity_score": prediction.get("severity_score"),
        "predicted_duration_hours": prediction.get("duration_hours"),
        "predicted_duration_bucket": prediction.get("duration_bucket"),
        "recommended_action": prediction.get("recommended_action"),
        "impact_radius_km": spatial.get("estimated_impact_radius_km"),
        "avg_nearby_duration_hours": spatial.get("avg_nearby_duration_hours"),
        "officers_required": resources.get("officers_required"),
        "barricades_required": resources.get("barricades_required"),
        "patrol_vehicles_required": resources.get("patrol_vehicles_required"),
        "deployment_points": " | ".join(resources.get("deployment_points", [])),
        "diversion_strategy": routes.get("diversion_strategy"),
        "alternate_routes": " | ".join(routes.get("alternate_routes", [])),
        "actual_severity_label": "",
        "actual_duration_hours": "",
        "actual_duration_bucket": "",
        "actual_officers_used": "",
        "actual_barricades_used": "",
        "actual_patrols_used": "",
        "actual_notes": "",
        "ground_truth_submitted_at": ""
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if LOG_FILE.exists():
        existing = pd.read_csv(LOG_FILE)
        existing = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
        fd, tmp = tempfile.mkstemp(dir=OUTPUT_DIR, suffix=".csv")
        try:
            existing.to_csv(tmp, index=False)
            os.close(fd)
            os.replace(tmp, LOG_FILE)
        except BaseException:
            os.close(fd)
            os.unlink(tmp)
            raise
    else:
        pd.DataFrame([row]).to_csv(LOG_FILE, index=False)

    return log_timestamp


def update_ground_truth(log_timestamp, actual_severity_label, actual_duration_hours,
                        actual_duration_bucket, actual_notes,
                        actual_officers_used=None, actual_barricades_used=None,
                        actual_patrols_used=None):
    if not LOG_FILE.exists():
        return False

    df = pd.read_csv(LOG_FILE)

    mask = df["log_timestamp"] == log_timestamp
    if not mask.any():
        return False

    idx = df[mask].index[0]
    df.at[idx, "actual_severity_label"] = str(actual_severity_label)
    df.at[idx, "actual_duration_hours"] = str(actual_duration_hours)
    df.at[idx, "actual_duration_bucket"] = str(actual_duration_bucket)
    df.at[idx, "actual_notes"] = str(actual_notes)
    if actual_officers_used is not None:
        df.at[idx, "actual_officers_used"] = str(actual_officers_used)
    if actual_barricades_used is not None:
        df.at[idx, "actual_barricades_used"] = str(actual_barricades_used)
    if actual_patrols_used is not None:
        df.at[idx, "actual_patrols_used"] = str(actual_patrols_used)
    df.at[idx, "ground_truth_submitted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fd, tmp = tempfile.mkstemp(dir=OUTPUT_DIR, suffix=".csv")
    try:
        df.to_csv(tmp, index=False)
        os.close(fd)
        os.replace(tmp, LOG_FILE)
    except BaseException:
        os.close(fd)
        os.unlink(tmp)
        raise
    return True


def get_unreviewed_predictions():
    if not LOG_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(LOG_FILE)
    unreviewed = df[df["actual_severity_label"].isna() | (df["actual_severity_label"] == "")]
    return unreviewed.tail(20)


def delete_feedback_row(log_timestamp):
    if not LOG_FILE.exists():
        return False
    df = pd.read_csv(LOG_FILE)
    mask = df["log_timestamp"] == log_timestamp
    if not mask.any():
        return False
    df = df[~mask]
    fd, tmp = tempfile.mkstemp(dir=OUTPUT_DIR, suffix=".csv")
    try:
        df.to_csv(tmp, index=False)
        os.close(fd)
        os.replace(tmp, LOG_FILE)
    except BaseException:
        os.close(fd)
        os.unlink(tmp)
        raise
    return True


def clear_all_feedback():
    if not LOG_FILE.exists():
        return True
    # Truncate the file, keeping only the header row
    try:
        df = pd.read_csv(LOG_FILE)
        if len(df) > 0:
            header_df = df.iloc[:0]
            header_df.to_csv(LOG_FILE, index=False)
        return True
    except Exception:
        # Fallback: write empty file with header
        pd.DataFrame().to_csv(LOG_FILE, index=False)
        return True


def append_feedback_row(actual_severity_label, actual_duration_hours,
                        actual_duration_bucket, actual_notes,
                        actual_officers_used=None, actual_barricades_used=None,
                        actual_patrols_used=None):
    from datetime import datetime
    row = {
        "log_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "",
        "event_cause": "",
        "latitude": "",
        "longitude": "",
        "corridor": "",
        "zone": "",
        "junction": "",
        "hour": "",
        "day_of_week": "",
        "month": "",
        "is_weekend": "",
        "priority": "",
        "requires_road_closure": "",
        "expected_attendance": 0,
        "predicted_severity_label": "",
        "predicted_severity_score": "",
        "predicted_duration_bucket": "",
        "recommended_action": "",
        "impact_radius_km": "",
        "avg_nearby_duration_hours": "",
        "officers_required": "",
        "barricades_required": "",
        "patrol_vehicles_required": "",
        "deployment_points": "",
        "diversion_strategy": "",
        "alternate_routes": "",
        "actual_severity_label": actual_severity_label,
        "actual_duration_hours": str(actual_duration_hours),
        "actual_duration_bucket": actual_duration_bucket,
        "actual_officers_used": str(actual_officers_used) if actual_officers_used is not None else "",
        "actual_barricades_used": str(actual_barricades_used) if actual_barricades_used is not None else "",
        "actual_patrols_used": str(actual_patrols_used) if actual_patrols_used is not None else "",
        "actual_notes": actual_notes,
        "ground_truth_submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists():
        existing = pd.read_csv(LOG_FILE)
        existing = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        existing = pd.DataFrame([row])
    fd, tmp = tempfile.mkstemp(dir=OUTPUT_DIR, suffix=".csv")
    try:
        existing.to_csv(tmp, index=False)
        os.close(fd)
        os.replace(tmp, LOG_FILE)
    except BaseException:
        os.close(fd)
        os.unlink(tmp)
        raise
    return True
