import math
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from event_cause_map import normalize_cause
from train_resource_model import predict_resources as model_predict_resources

CAUSE_OFFICER_BASE = {
    "vip_movement": 20,
    "protest": 18,
    "public_event": 14,
    "procession": 10,
    "construction": 6,
    "accident": 6,
    "congestion": 4,
    "waterlogging": 3,
    "vehiclebreakdown": 3,
    "potholes": 2,
    "tree_fall": 4,
    "road_conditions": 3,
    "debris": 2,
    "fog_low_visibility": 3,
    "others": 2,
}

CAUSE_BARRICADE_BASE = {
    "vip_movement": 20,
    "protest": 15,
    "public_event": 12,
    "procession": 8,
    "construction": 6,
    "accident": 4,
    "congestion": 2,
    "waterlogging": 2,
    "vehiclebreakdown": 1,
    "potholes": 1,
    "tree_fall": 2,
    "road_conditions": 2,
    "debris": 1,
    "fog_low_visibility": 2,
    "others": 1,
}

CAUSE_PATROL_BASE = {
    "vip_movement": 6,
    "protest": 5,
    "public_event": 4,
    "procession": 3,
    "construction": 2,
    "accident": 2,
    "congestion": 2,
    "waterlogging": 1,
    "vehiclebreakdown": 1,
    "potholes": 1,
    "tree_fall": 1,
    "road_conditions": 1,
    "debris": 1,
    "fog_low_visibility": 1,
    "others": 1,
}

CORRIDOR_RADIUS_KM = {
    "Mysore Road": 2.0,
    "Bellary Road 1": 1.8,
    "Bellary Road 2": 1.5,
    "Tumkur Road": 1.5,
    "Old Airport Road": 2.2,
    "Varthur Road": 1.8,
    "Hosur Road": 2.0,
    "Old Madras Road": 2.5,
    "ORR East 1": 1.5,
    "ORR East 2": 2.0,
    "ORR North 1": 1.5,
    "ORR North 2": 1.8,
    "ORR West 1": 1.5,
    "Bannerghata Road": 2.0,
    "West of Chord Road": 1.5,
    "CBD 1": 3.0,
    "CBD 2": 2.5,
    "Non-corridor": 0.8,
}


def _attendance_multiplier(attendance):
    if attendance <= 0:
        return 1.0
    if attendance < 500:
        return 0.7
    elif attendance < 2000:
        return 1.0
    elif attendance < 10000:
        return 1.5
    elif attendance < 50000:
        return 2.5
    else:
        return 4.0


def _attendance_label(attendance):
    if attendance <= 0:
        return "unknown"
    if attendance < 500:
        return "small"
    elif attendance < 2000:
        return "medium"
    elif attendance < 10000:
        return "large"
    elif attendance < 50000:
        return "very large"
    else:
        return "massive"


def optimize_resources(severity_label, severity_score, event_cause, requires_road_closure,
                       latitude, longitude, corridor="Non-corridor", expected_attendance=0):
    cause_key = normalize_cause(event_cause)

    # Try data-driven model predictions first
    model_pred = model_predict_resources(
        event_cause=cause_key, severity_label=severity_label,
        severity_score=severity_score,
        requires_road_closure=requires_road_closure,
        expected_attendance=expected_attendance,
        corridor=corridor, zone="", priority="",
        hour=12, day_of_week=0, month=1, is_weekend=0,
    )
    use_model = model_pred and all(v is not None for v in model_pred.values())

    if use_model:
        officers = model_pred["officers"]
        barricades = model_pred["barricades"]
        patrols = model_pred["patrols"]
        source = "model"
    else:
        base_officers = CAUSE_OFFICER_BASE.get(cause_key, 4)
        base_barricades = CAUSE_BARRICADE_BASE.get(cause_key, 2)
        base_patrols = CAUSE_PATROL_BASE.get(cause_key, 1)

        sev_mult = 1.0 + (float(severity_score) / 100.0) * 1.5
        closure_mult = 1.3 if requires_road_closure else 1.0
        attend_mult = _attendance_multiplier(expected_attendance)

        officers = math.ceil(base_officers * sev_mult * closure_mult * attend_mult)
        barricades = math.ceil(base_barricades * sev_mult * closure_mult * attend_mult)
        patrols = math.ceil(base_patrols * sev_mult * closure_mult * attend_mult)
        source = "rule"

    if severity_label == "High" or cause_key in ["vip_movement", "protest"]:
        monitoring = "ACTIVE COMMAND MONITORING"
    elif severity_label == "Medium":
        monitoring = "ELEVATED MONITORING"
    else:
        monitoring = "STANDARD MONITORING"

    deployment_points = _get_deployment_points(cause_key, severity_label, requires_road_closure,
                                                expected_attendance)

    escalation_note = None
    attend_label = _attendance_label(expected_attendance)
    if expected_attendance > 0 and attend_label in ("large", "very large", "massive"):
        escalation_note = (
            f"ATTENDANCE ESCALATION: {expected_attendance:,} expected attendees "
            f"({attend_label} event). Estimated {officers} traffic officers is a "
            "minimum — coordinate with public-order units for crowd management."
        )
    elif expected_attendance <= 0 and cause_key in ["protest", "public_event", "procession", "vip_movement"]:
        escalation_note = (
            f"NOTE: {officers} officers is the minimum traffic deployment estimate. "
            "Crowd size is unknown — specify expected attendance for more accurate "
            "resource planning."
        )

    impact_radius_km = CORRIDOR_RADIUS_KM.get(corridor, 1.0)
    if severity_label == "High":
        impact_radius_km *= 1.3
    elif severity_label == "Medium":
        impact_radius_km *= 1.1
    if requires_road_closure:
        impact_radius_km *= 1.2
    if cause_key in ["vip_movement", "protest", "public_event"]:
        impact_radius_km *= 1.15
    # Attendance expands the impact zone
    if attend_label == "large":
        impact_radius_km *= 1.2
    elif attend_label in ("very large", "massive"):
        impact_radius_km *= 1.5
    impact_radius_km = round(min(max(impact_radius_km, 0.5), 8.0), 2)

    return {
        "officers_required": officers,
        "barricades_required": barricades,
        "patrol_vehicles_required": patrols,
        "monitoring_level": monitoring,
        "deployment_points": deployment_points,
        "escalation_note": escalation_note,
        "impact_radius_km": impact_radius_km,
        "expected_attendance": expected_attendance,
        "attendance_label": attend_label,
        "resource_source": source,
    }


def _get_deployment_points(cause_key, severity_label, requires_road_closure, expected_attendance=0):
    base = ["Event Entry Point", "Primary Intersection"]
    attend_label = _attendance_label(expected_attendance)

    if cause_key == "vip_movement":
        pts = ["VIP Route Entry", "VIP Route Exit", "Flanking Junctions", "Alternate Route 1", "Alternate Route 2"]
        if attend_label in ("large", "very large", "massive"):
            pts += ["Crowd Holding Area", "Emergency Vehicle Access Point"]
        return pts

    if cause_key in ["protest", "public_event"]:
        pts = ["Event Entry Gate", "Main Arterial Junction", "Nearest Diversion Point"]
        if requires_road_closure:
            pts += ["Road Closure Point A", "Road Closure Point B"]
        if severity_label == "High":
            pts += ["Backup Staging Area"]
        if attend_label in ("large", "very large", "massive"):
            pts += ["Overflow Parking Zone", "Emergency Access Lane", "Crowd Control Staging"]
        return pts

    if cause_key == "procession":
        pts = ["Procession Start", "Mid-Route Junction", "Procession End Point", "Parallel Road Entry"]
        if attend_label in ("large", "very large", "massive"):
            pts += ["Crowd Viewing Area", "Medical Aid Station Point"]
        return pts

    if cause_key == "construction":
        pts = ["Construction Zone Entry", "Taper Zone", "Merge Point"]
        if requires_road_closure:
            pts.append("Detour Entry")
        return pts

    if cause_key in ["accident", "vehiclebreakdown"]:
        pts = ["Incident Location", "50m Upstream Buffer"]
        if requires_road_closure:
            pts.append("Lane Closure Taper")
        return pts

    if severity_label == "High":
        return base + ["Secondary Junction", "Diversion Route"]
    return base
