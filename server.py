import os
import sys
import json
import queue
import math
import time
import webbrowser
import threading
import urllib.parse
from pathlib import Path
from collections import deque

import pandas as pd
from flask import Flask, jsonify, request, render_template, Response, stream_with_context

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from location_resolver import resolve_location_from_corridor, load_location_data, get_nearby_junctions
from noncorridor_roads import NAMED_CORRIDORS
from infer_event_profile import infer_event_profile
from spatial_engine import estimate_spatial_impact
from resource_optimizer import optimize_resources
from routing_engine import suggest_diversion_routes
from feedback_logger import log_prediction_event, update_ground_truth, append_feedback_row, delete_feedback_row, clear_all_feedback, LOG_FILE
from train_resource_model import train_and_save_resource_models
from retrain_pipeline import build_retraining_dataset
from realtime_generator import generate_raw_event
from datetime import datetime, timedelta, timezone
from realtime_ingest import TrafficEventSource

# Hardcode your API key here (or leave "" to configure via UI):
REALTIME_API_KEY = ""
REALTIME_API_URL = ""  # optional override if not Bing Maps
TOMTOM_BBOX = "77.50,12.87,77.72,13.10"  # Bangalore minLon,minLat,maxLon,maxLat

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/corridors")
def get_corridors():
    try:
        df = load_location_data()
        corridors = df["corridor"].dropna().astype(str).str.strip()
        corridors = corridors[corridors != ""].unique().tolist()
        named = {}
        noncorr = {}
        for c in sorted(corridors):
            if c == "Non-corridor":
                continue
            info = resolve_location_from_corridor(c)
            entry = {
                "zone": info.get("zone", "Unknown"),
                "junction": info.get("junction", "Unknown"),
                "lat": info.get("latitude", 12.9716),
                "lng": info.get("longitude", 77.5946),
            }
            if c in NAMED_CORRIDORS:
                named[c] = entry
            else:
                noncorr[c] = entry
        return jsonify({"named": named, "noncorridor": noncorr})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        sample = {
            "event_type": data.get("event_type", "unplanned"),
            "event_cause": data.get("event_cause", "public_event"),
            "latitude": data.get("latitude", 12.9716),
            "longitude": data.get("longitude", 77.5946),
            "corridor": data.get("corridor", "Non-corridor"),
            "zone": data.get("zone", "Unknown"),
            "junction": data.get("junction", "Unknown"),
            "hour": data.get("hour", 12),
            "day_of_week": data.get("day_of_week", 0),
            "month": data.get("month", 1),
            "is_weekend": 1 if data.get("day_of_week", 0) in [5, 6] else 0,
            "expected_attendance": data.get("expected_attendance") or data.get("attendance", 0),
        }

        inferred = infer_event_profile(sample)
        spatial = estimate_spatial_impact(sample["latitude"], sample["longitude"])
        resources = optimize_resources(
            inferred["severity_label"], inferred["severity_score"],
            sample["event_cause"], int(inferred["requires_road_closure"]),
            sample["latitude"], sample["longitude"],
            corridor=sample["corridor"],
            expected_attendance=sample["expected_attendance"]
        )
        routes = suggest_diversion_routes(
            sample["event_cause"], inferred["severity_label"],
            sample["latitude"], sample["longitude"],
            corridor=sample["corridor"]
        )

        nearby_junctions = get_nearby_junctions(sample["corridor"])

        prediction = {
            "severity_label": inferred["severity_label"],
            "severity_score": inferred["severity_score"],
            "duration_hours": inferred["duration_hours"],
            "duration_bucket": inferred["duration_bucket"],
            "recommended_action": inferred["recommended_action"],
        }
        log_ts = log_prediction_event(sample, prediction, spatial, resources, routes)

        return jsonify({
            "log_timestamp": log_ts,
            "severity_label": inferred["severity_label"],
            "severity_score": inferred["severity_score"],
            "priority": inferred["priority"],
            "road_closure": inferred["requires_road_closure"],
            "duration_hours": round(inferred["duration_hours"], 2),
            "duration_bucket": inferred["duration_bucket"],
            "recommended_action": inferred["recommended_action"],
            "zone": sample["zone"],
            "junction": sample["junction"],
            "resources": {
                "officers_required": resources["officers_required"],
                "barricades_required": resources["barricades_required"],
                "patrol_vehicles_required": resources["patrol_vehicles_required"],
                "monitoring_level": resources["monitoring_level"],
                "impact_radius_km": resources.get("impact_radius_km",
                                                  spatial.get("estimated_impact_radius_km", 1.0)),
                "deployment_points": resources["deployment_points"],
                "attendance_label": resources.get("attendance_label", "unknown"),
                "escalation_note": resources.get("escalation_note", ""),
                "resource_source": resources.get("resource_source", "rule"),
            },
            "routes": {
                "diversion_strategy": routes["diversion_strategy"],
                "alternate_routes": routes["alternate_routes"],
            },
            "nearby_junctions": nearby_junctions,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ground_truth", methods=["POST"])
def ground_truth():
    try:
        data = request.get_json()
        ts = data.get("log_timestamp", "")
        severity = data.get("actual_severity", "")
        duration = float(data.get("actual_duration", 0))
        notes = data.get("notes", "")

        if not severity:
            return jsonify({"ok": False, "error": "Missing actual_severity"}), 400

        bucket = "short"
        if duration >= 12:
            bucket = "extended"
        elif duration >= 1:
            bucket = "medium"

        actual_officers = data.get("actual_officers")
        actual_barricades = data.get("actual_barricades")
        actual_patrols = data.get("actual_patrols")

        if ts:
            ok = update_ground_truth(ts, severity, duration, bucket, notes,
                                     actual_officers, actual_barricades, actual_patrols)
        else:
            ok = append_feedback_row(severity, duration, bucket, notes,
                                     actual_officers, actual_barricades, actual_patrols)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/retrain", methods=["POST"])
def retrain():
    try:
        build_retraining_dataset()
        return jsonify({"ok": True, "message": "Retraining dataset built"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/retrain_resource_model", methods=["POST"])
def retrain_resource_model():
    try:
        metrics = train_and_save_resource_models()
        return jsonify({"ok": True, "metrics": metrics})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/feedback/<path:log_timestamp>", methods=["DELETE"])
def delete_feedback(log_timestamp):
    try:
        import urllib.parse
        ts = urllib.parse.unquote(log_timestamp)
        ok = delete_feedback_row(ts)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/feedback", methods=["DELETE"])
def clear_feedback():
    try:
        ok = clear_all_feedback()
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _clean_nan(val):
    import math
    if isinstance(val, float) and math.isnan(val):
        return None
    return val

@app.route("/api/feedback")
def get_feedback():
    try:
        if LOG_FILE.exists():
            df = pd.read_csv(LOG_FILE)
            rows = [{k: _clean_nan(v) for k, v in row.items()} for row in df.to_dict(orient="records")]
            return jsonify({"rows": rows, "total": len(df)})
        return jsonify({"rows": [], "total": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


RETRAINING_FILE = OUTPUTS_DIR / "retraining_dataset.csv"


@app.route("/api/retraining", methods=["GET", "DELETE"])
def handle_retraining():
    if request.method == "DELETE":
        try:
            if RETRAINING_FILE.exists():
                os.remove(RETRAINING_FILE)
                return jsonify({"ok": True, "message": "Retraining dataset cleared"})
            return jsonify({"ok": True, "message": "No retraining dataset to clear"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    try:
        if RETRAINING_FILE.exists():
            df = pd.read_csv(RETRAINING_FILE)
            rows = [{k: _clean_nan(v) for k, v in row.items()} for row in df.tail(50).to_dict(orient="records")]
            return jsonify({"rows": rows, "total": len(df)})
        return jsonify({"rows": [], "total": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ REAL-TIME MONITOR ============
_realtime_clients = []
_realtime_lock = threading.Lock()
_realtime_running = False
_realtime_interval = 15
_latest_events = deque(maxlen=30)
_rt_counter = 0
_realtime_source = "simulation"  # "simulation" | "traffic_api"
_traffic_source = None  # TrafficEventSource instance
_traffic_source_lock = threading.Lock()

def _get_traffic_source():
    global _traffic_source
    return _traffic_source

def _poll_source():
    """Returns a list of sample dicts from the configured source."""
    src = _realtime_source
    if src in ("traffic_api", "tomtom"):
        with _traffic_source_lock:
            ts = _traffic_source
        if ts:
            events = ts.poll()
            return [e.to_sample() for e in events if hasattr(e, 'to_sample')]
        return []
    else:
        sample = generate_raw_event()
        return [sample] if sample else []

def _process_event(sample):
    """Run full analysis on a sample and return the payload dict."""
    inferred = infer_event_profile(sample)
    spatial = estimate_spatial_impact(sample["latitude"], sample["longitude"])
    resources = optimize_resources(
        inferred["severity_label"], inferred["severity_score"],
        sample["event_cause"], int(inferred["requires_road_closure"]),
        sample["latitude"], sample["longitude"],
        corridor=sample["corridor"],
        expected_attendance=sample["expected_attendance"]
    )
    routes = suggest_diversion_routes(
        sample["event_cause"], inferred["severity_label"],
        sample["latitude"], sample["longitude"],
        corridor=sample["corridor"]
    )
    prediction = {
        "severity_label": inferred["severity_label"],
        "severity_score": inferred["severity_score"],
        "recommended_action": inferred["recommended_action"],
    }
    log_ts = log_prediction_event(sample, prediction, spatial, resources, routes)
    return {
        "_source": _realtime_source,
        "log_timestamp": log_ts,
        "event_type": sample["event_type"],
        "event_cause": sample["event_cause"],
        "corridor": sample["corridor"],
        "zone": sample["zone"],
        "junction": sample["junction"],
        "latitude": sample["latitude"],
        "longitude": sample["longitude"],
        "hour": sample["hour"],
        "day_of_week": sample["day_of_week"],
        "month": sample["month"],
        "expected_attendance": sample["expected_attendance"],
        "severity_label": inferred["severity_label"],
        "severity_score": inferred["severity_score"],
        "priority": inferred["priority"],
        "road_closure": inferred["requires_road_closure"],
        "duration_hours": round(inferred["duration_hours"], 2),
        "duration_bucket": inferred["duration_bucket"],
        "recommended_action": inferred["recommended_action"],
        "resources": {
            "officers_required": resources["officers_required"],
            "barricades_required": resources["barricades_required"],
            "patrol_vehicles_required": resources["patrol_vehicles_required"],
            "monitoring_level": resources["monitoring_level"],
            "impact_radius_km": resources.get("impact_radius_km", spatial.get("estimated_impact_radius_km", 1.0)),
            "deployment_points": resources["deployment_points"],
            "resource_source": resources.get("resource_source", "rule"),
        },
        "routes": {
            "diversion_strategy": routes["diversion_strategy"],
            "alternate_routes": routes["alternate_routes"],
        },
    }

def _realtime_broadcast(payload):
    with _realtime_lock:
        dead = []
        for q in _realtime_clients:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _realtime_clients.remove(q)

def _realtime_worker():
    global _realtime_running, _rt_counter
    while _realtime_running:
        try:
            samples = _poll_source()
            for sample in samples:
                payload = _process_event(sample)
                payload["id"] = _rt_counter + 1
                _rt_counter += 1
                _latest_events.append(payload)
                _realtime_broadcast(payload)
        except Exception as e:
            pass
        time.sleep(5 if _realtime_source in ("traffic_api", "tomtom") else _realtime_interval)

@app.route("/api/realtime/stream")
def realtime_stream():
    q = queue.Queue(maxsize=100)
    with _realtime_lock:
        _realtime_clients.append(q)
    def generate():
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            with _realtime_lock:
                if q in _realtime_clients:
                    _realtime_clients.remove(q)
    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

@app.route("/api/realtime/start", methods=["POST"])
def realtime_start():
    global _realtime_running, _realtime_source, _traffic_source
    if not _realtime_running:
        # Auto-init traffic source if hardcoded key exists and no source set yet
        if REALTIME_API_KEY and _realtime_source != "traffic_api":
            _realtime_source = "traffic_api"
            with _traffic_source_lock:
                _traffic_source = TrafficEventSource(api_key=REALTIME_API_KEY, api_url=REALTIME_API_URL, poll_interval=30)
                _traffic_source._last_poll = datetime.now(timezone.utc) - timedelta(seconds=31)
        _realtime_running = True
        t = threading.Thread(target=_realtime_worker, daemon=True)
        t.start()
    return jsonify({"ok": True, "running": True})

@app.route("/api/realtime/stop", methods=["POST"])
def realtime_stop():
    global _realtime_running
    _realtime_running = False
    return jsonify({"ok": True, "running": False})

@app.route("/api/realtime/status")
def realtime_status():
    return jsonify({
        "running": _realtime_running,
        "interval": _realtime_interval,
        "event_count": _rt_counter,
        "connected_clients": len(_realtime_clients),
    })

@app.route("/api/realtime/latest")
def realtime_latest():
    return jsonify({"events": list(_latest_events)})

@app.route("/api/realtime/config", methods=["GET", "POST"])
def realtime_config():
    global _realtime_source, _traffic_source
    if request.method == "POST":
        data = request.get_json() or {}
        new_source = data.get("source_type", _realtime_source)
        api_key = data.get("api_key", "") or REALTIME_API_KEY
        if new_source == "traffic_api" and api_key:
            url = REALTIME_API_URL or ""
            with _traffic_source_lock:
                _traffic_source = TrafficEventSource(api_key=api_key, api_url=url, poll_interval=30)
                _traffic_source._last_poll = datetime.now(timezone.utc) - timedelta(seconds=31)
            _realtime_source = "traffic_api"
        elif new_source == "tomtom" and api_key:
            url = (f"https://api.tomtom.com/traffic/services/5/incidentDetails"
                   f"?key={api_key}&bbox={TOMTOM_BBOX}&fields=incidentsOnly&language=en-GB")
            with _traffic_source_lock:
                _traffic_source = TrafficEventSource(api_key=api_key, api_url=url, poll_interval=30)
                _traffic_source._last_poll = datetime.now(timezone.utc) - timedelta(seconds=31)
            _realtime_source = "tomtom"
        elif new_source == "simulation":
            _realtime_source = "simulation"
        return jsonify({
            "ok": True,
            "source_type": _realtime_source,
            "configured": _traffic_source is not None,
        })
    ts = _get_traffic_source()
    return jsonify({
        "source_type": _realtime_source,
        "configured": ts is not None,
        "error": getattr(ts, "_error", None) if ts else None,
    })


if __name__ == "__main__":
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5555")).start()
    app.run(debug=False, threaded=True, port=5555)
