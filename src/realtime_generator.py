import random
from datetime import datetime
from location_resolver import load_location_data

EVENT_TYPES = ["planned", "unplanned"]
EVENT_CAUSES = [
    "public_event", "vip_movement", "protest", "procession",
    "construction", "congestion", "accident",
    "vehiclebreakdown", "waterlogging", "potholes",
]
ATTENDANCE_OPTIONS = [0, 500, 1000, 2000, 5000, 10000, 50000]
_SEEN = set()

def generate_raw_event():
    df = load_location_data()
    corridors = df["corridor"].dropna().astype(str).str.strip().unique().tolist()
    corridors = [c for c in corridors if c]
    if not corridors:
        return None
    corridor = random.choice(corridors)
    cr_norm = corridor.strip().lower()
    rows = df[df["corridor"].astype(str).str.strip().str.lower() == cr_norm]
    now = datetime.now()
    return {
        "event_type": random.choice(EVENT_TYPES),
        "event_cause": random.choice(EVENT_CAUSES),
        "latitude": float(rows["latitude"].median()) if not rows.empty and rows["latitude"].notna().any() else 12.9716,
        "longitude": float(rows["longitude"].median()) if not rows.empty and rows["longitude"].notna().any() else 77.5946,
        "corridor": corridor,
        "zone": str(rows["zone"].mode().iloc[0]) if not rows.empty and rows["zone"].notna().any() else "Unknown",
        "junction": str(rows["junction"].mode().iloc[0]) if not rows.empty and rows["junction"].notna().any() else "Unknown",
        "hour": now.hour,
        "day_of_week": now.weekday(),
        "month": now.month,
        "is_weekend": 1 if now.weekday() >= 5 else 0,
        "expected_attendance": random.choice(ATTENDANCE_OPTIONS),
    }
