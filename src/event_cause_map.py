"""
Normalizes raw event_cause strings from ASTraM data into standardized keys
used by models, inference, and resource tables.

Why: The raw data has inconsistent naming (vehicle_breakdown vs vehiclebreakdown,
pot_holes vs potholes, water_logging vs waterlogging, mixed case, debris vs Debris).
This module provides a single source of truth for the mapping.
"""

import re

# Map every observed raw cause to a standardized key
_RAW_TO_STANDARD = {
    "public_event":       "public_event",
    "procession":         "procession",
    "vip_movement":       "vip_movement",
    "protest":            "protest",
    "construction":       "construction",
    "congestion":         "congestion",
    "accident":           "accident",
    "vehicle_breakdown":  "vehiclebreakdown",
    "vehiclebreakdown":   "vehiclebreakdown",
    "pot_holes":          "potholes",
    "potholes":           "potholes",
    "water_logging":      "waterlogging",
    "waterlogging":       "waterlogging",
    "tree_fall":          "tree_fall",
    "road_conditions":    "road_conditions",
    "debris":             "debris",
    "Debris":             "debris",
    "fog_/_low_visibility": "fog_low_visibility",
    "fog_low_visibility":   "fog_low_visibility",
    "test_demo":          "test_demo",
    "others":             "others",
}

# Which standardized keys are treated as known (non-noise) for model training
KNOWN_CAUSES = [
    "public_event",
    "procession",
    "vip_movement",
    "protest",
    "construction",
    "congestion",
    "accident",
    "vehiclebreakdown",
    "potholes",
    "waterlogging",
    "tree_fall",
    "road_conditions",
    "debris",
    "fog_low_visibility",
]

# Mapping from standardized key -> broader grouping (for models with sparse data)
CAUSE_GROUP = {
    "public_event":       "public_event",
    "procession":         "procession",
    "vip_movement":       "vip_movement",
    "protest":            "protest",
    "construction":       "construction",
    "congestion":         "congestion",
    "accident":           "accident",
    "vehiclebreakdown":   "vehiclebreakdown",
    "potholes":           "road_hazard",
    "waterlogging":       "road_hazard",
    "tree_fall":          "road_hazard",
    "road_conditions":    "road_hazard",
    "debris":             "road_hazard",
    "fog_low_visibility": "road_hazard",
    "test_demo":          "others",
    "others":             "others",
}


def normalize_cause(raw_cause):
    if not raw_cause or pd.isna(raw_cause):
        return "others"
    cleaned = re.sub(r'[\s/\-]+', '_', str(raw_cause).strip().lower())
    return _RAW_TO_STANDARD.get(cleaned, "others")


def known_causes():
    return list(KNOWN_CAUSES)


def cause_group(standard_cause):
    return CAUSE_GROUP.get(standard_cause, "others")


# Lazy import to allow module-level definition
import pandas as pd  # noqa: E402
