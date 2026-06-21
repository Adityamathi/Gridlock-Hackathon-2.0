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
    '100 Feet Road, Kanteerava Studio Circle': 0.8,
    '10th Main Road, Achaiah Chetty Layout': 0.8,
    '11th Cross Road, Acharya Sri Ramanuja Circle': 0.8,
    '11th Main Road, Sri Aurobindo Circle': 0.8,
    '12th Cross Road, Lakksandra Extension': 0.8,
    '13th Cross Road, Bashyam Circle': 0.8,
    '1st Cross Road, Koramangala Water Tank Junction': 0.8,
    '1st Main Road, Sri Vijayamaruthi Circle': 0.8,
    '24th Main Road, Sarakki Agrahara': 0.8,
    '27th Cross Road, Dr BR Ambedkar Circle': 0.8,
    '2nd Cross Road, MTB Area': 0.8,
    '2nd Main Road, Abdul Patel Syed Layout': 0.8,
    '3rd Cross Road, Bommanahalli Circle': 0.8,
    '3rd Main Road, Chakkasandra': 0.8,
    '46th Cross Road, Sri Aurobindo Circle': 0.8,
    '4th Cross Road, Papareddypalya Circle': 0.8,
    '4th Main Road, Shri Satya Sai Circle': 0.8,
    '5th Cross Road, Uday Nagar': 0.8,
    '5th Main Road, Anandgiri Extension': 0.8,
    '60 Feet Road, KK Layout': 0.8,
    '6th Main Road, BDA Industrial Suburb': 0.8,
    '7th Cross Road, BDA Junction': 0.8,
    '7th Main Road, Balaji Layout': 0.8,
    '80 Feet Ring Road, Harikara Vidvan Sri R Gururajulu Naidu Circle': 0.8,
    '80 Feet Road, Block 2': 0.8,
    '8th Cross Road, RR Palace': 0.8,
    '9th Cross Road, Kaniyar Colony': 0.8,
    '9th Main Road, Shri Satya Sai Circle': 0.8,
    'Adugodi Road, Krupanidhi College Junction': 0.8,
    'Airport New South Road': 2.5,
    'Amrutha College Road, Sri Venkateshwara Circle': 0.8,
    'Ashok Nagar Road, Ashirwadam Junction': 0.8,
    'Assayee Road, Sham Mansion Apartment': 0.8,
    'Banashankari Road, Sarbandapalya': 0.8,
    'Banaswadi Road, Gopalan Signature Mall': 0.8,
    'Bannerghata Road': 2.5,
    'Basavanagudi Road, Cauvery Circle': 0.8,
    'Begur Main Road, Alpine Park Apartment': 0.8,
    'Bellandur Road, Kasavanahalli': 0.8,
    'Bellary Road 1': 2.5,
    'Bellary Road 2': 2.5,
    'Broadway Road, Chandni Chowk': 0.8,
    'Byatarayanapura Road, Nagarabavi Circle': 0.8,
    'CBD 1': 2.5,
    'CBD 2': 2.5,
    'CV Raman Road, SBD Township Sector B': 0.8,
    'Chamarajpet Road, Sangolli Rayanna Circle': 0.8,
    'Chikkabanavara Road, Nagasandra': 0.8,
    'Chikkajala Road, Phase 2A': 0.8,
    'City Market Road, Santhusapete': 0.8,
    'Cubbon Park Road, Krishna Rajendra Circle': 0.8,
    'Devanahalli Airport Road, Sri Kanakadasa Circle': 0.8,
    'Dhanvanthri Road, Ayurvedic Hospital Junction': 0.8,
    'Dinnur Main Road, Southern Residency Apartment': 0.8,
    'Doddaballapur Main Road, East Colony': 0.8,
    'Dr Ambedkar Road, Krishna Rajendra Circle': 0.8,
    'Dr MH Ambarish Road, C Ranga Swamy Circle': 0.8,
    'Dr Rajgopal Road, Ashwath Nagar': 0.8,
    'Dr Rajkumar Puniya Bhoomi Road, Block 6': 0.8,
    'Dr TCM Royan Road, Cottonpet Circle': 0.8,
    'Electronic City Road, Pramuk Aqua Heights': 0.8,
    'Electronics City Flyover, Bommanahalli Circle': 0.8,
    'Halasur Road, Agaram': 0.8,
    'Halasuru Gate Road, Ashirwadam Junction': 0.8,
    'Hennur Main Road': 2.5,
    'High Ground Road, Karnataka Bhavan Junction': 0.8,
    'Hoodi Main Road, ESI Road Junction': 0.8,
    'Hosur Road': 2.5,
    'Hulimavu Road, Anjaneya Swami Circle': 0.8,
    'IRR(Thanisandra road)': 2.5,
    'JP Nagar Road, Sri Aurobindo Circle': 0.8,
    'Jalahalli Road, Gangamma Circle': 0.8,
    'Jayamahal Main Road, Enayathulla Mehkri Circle': 0.8,
    'Jayanagara Road, MTB Area': 0.8,
    'Jeevanbheemanagar Road, Thimmaiah Reddy Colony': 0.8,
    'Jnanabharathi Road, Kengunte Circle': 0.8,
    'K.R. Pura Road, Zero Tolerance Junction': 0.8,
    'KG Halli Road, Bilal Nagar': 0.8,
    'KH Road, Ashirwadam Junction': 0.8,
    'KR Main Road, Professor P Shivshankar Circle': 0.8,
    'KS Layout Road, Muneshwara Nagar': 0.8,
    'Kamakshipalya Road, Sattva Anugraha': 0.8,
    'Kempegowda Road, Skyline Retreat': 0.8,
    'Kengeri Main Road, Kengunte Circle': 0.8,
    'Kengeri Road, Ideal Home Township': 0.8,
    'Kodigehalli Road, Pillappa Layout': 0.8,
    'Konanakunte Main Road, Jagathguru Shri Sivaratripura Circle': 0.8,
    'Kumar Krupa Road, Make In India Circle': 0.8,
    'Lalbagh Main Road, Dr Sri Shantaveera Swami Circle': 0.8,
    'MBT Road, Block 5 Stage 1': 0.8,
    'MS Ramaiah Road, BEL Circle': 0.8,
    'Madiwala Road, Krishna Reddy Layout': 0.8,
    'Magadi Road': 2.5,
    'Magadi Road (Local), Okalipuram Junction': 0.8,
    'Mahadevapura Road, Sadaramangala Industrial Area': 0.8,
    'Malleshwaram Road, Sri Maramma Temple Circle': 0.8,
    'Mico Layout Road, 29th BTM Road Junction': 0.8,
    'Millers Road, Chavundaraya Circle': 0.8,
    'Mumbai Bengaluru Highway, Nadaprabhu Kempegowda Circle': 0.8,
    'Muthsandra Main Road, KSRTC Travel House Junction': 0.8,
    'Mysore Road': 2.5,
    'NICE Road, Madavara': 0.8,
    'Nagarabhavi Main Road, Block 12': 0.8,
    'Netaji Road, Puttanna Junction': 0.8,
    'Nice Road, Sunbeam 1': 0.8,
    'Non-corridor': 5.0,
    'ORR East 1': 2.5,
    'ORR East 2': 2.5,
    'ORR North 1': 2.5,
    'ORR North 2': 2.5,
    'ORR West 1': 2.5,
    'Old Airport Road': 2.5,
    'Old Madras Road': 2.5,
    'Padmabhushan Dr RK Srikantan Road, Kalpataru Kalpavriksha': 0.8,
    'Padmasri CK Venkata Ramaiah Road, Sadashivanagar Junction': 0.8,
    'Peenya Road, Sobha Garrison': 0.8,
    'Pulikeshinagar Road, Sindhi Colony': 0.8,
    'RT Nagar Road, Vasanth Enclave': 0.8,
    'Rajajinagar Road, Narasimhaswamy Layout': 0.8,
    'SM Road, Patel Shamanna Layout': 0.8,
    'Sadashivanagar Road, Sadashivanagar Junction': 0.8,
    'Sankey Road, RV Layout': 0.8,
    'Sarjapur Marathahalli Road, Koramangala Water Tank Junction': 0.8,
    'Sarjapura Main Road, Dommasandra Anekal Taluka': 0.8,
    'Seshadri Road, Ayurvedic Hospital Junction': 0.8,
    'Sheshadripuram Road, Sangolli Rayanna Circle': 0.8,
    'Shivajinagar Road, Shivaji Nagar': 0.8,
    'Siddavanahalli Krishna Sharma Road, Sri Maramma Temple Circle': 0.8,
    'Silk Board Double Decker Flyover, Central Silk Board Staff Quarters': 0.8,
    'Sir CV Raman Road, Enayathulla Mehkri Circle': 0.8,
    'Sri Venkataranga Ayangar Road, Acharya Sri Ramanuja Circle': 0.8,
    'Sri Venkataranga Iyengar Road, Mill Corner Junction': 0.8,
    'Srinivagilu Main Road, KR Garden': 0.8,
    'Subedar Chatram Road, Shri Rajiv Gandhi Circle': 0.8,
    'Thalagattapura Road, Hosahalli South Taluka': 0.8,
    'Tumkur Road': 2.5,
    'Upparpet Road, Mysore Bank Circle': 0.8,
    'VV Puram Road, Professor P Shivshankar Circle': 0.8,
    'Varthur Road': 2.5,
    'Vijayanagara Road, Binny Layout': 0.8,
    'Vinoba Nagar Main Road, Narasimha Block': 0.8,
    'West of Chord Road': 2.5,
    'Whitefield Main Road, HBK Layout': 0.8,
    'Whitefield Road, Sadaramangala Industrial Area': 0.8,
    'Wilson Garden Road, Dr Ambedkar Social Welfare Association': 0.8,
    'Yelahanka Road, Nagarjuna Aster Park': 0.8,
    'Yeshwanthpura Road, Nada Prabhu Kempegowda Circle': 0.8,
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
