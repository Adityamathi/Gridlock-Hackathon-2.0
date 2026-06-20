import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from config import OUTPUT_DIR
from corridor_network import CORRIDOR_GRAPH

DATA_FILE = OUTPUT_DIR / "processed_theme3.csv"

# Corridor centroids (approximate lat/lon of each corridor's midpoint)
CORRIDOR_CENTROIDS = {
    "Mysore Road":        (12.9413, 77.5200),
    "Bellary Road 1":     (13.0320, 77.6050),
    "Bellary Road 2":     (13.0600, 77.6100),
    "Tumkur Road":        (13.0100, 77.5400),
    "Old Airport Road":   (12.9600, 77.6500),
    "Varthur Road":       (12.9400, 77.7100),
    "Hosur Road":         (12.9000, 77.6300),
    "Old Madras Road":    (12.9900, 77.6800),
    "ORR East 1":         (12.9600, 77.6800),
    "ORR East 2":         (12.9300, 77.7000),
    "ORR North 1":        (13.0400, 77.6300),
    "ORR North 2":        (13.0300, 77.6500),
    "ORR West 1":         (12.9300, 77.5700),
    "Bannerghata Road":   (12.9100, 77.5900),
    "West of Chord Road": (12.9700, 77.5500),
    "CBD 1":              (12.9750, 77.6050),
    "CBD 2":              (12.9650, 77.6150),
    "Non-corridor":       (12.9716, 77.5946),
}


def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def nearest_corridor(lat, lon):
    """Find the nearest known corridor to a point by straight-line distance."""
    best = "Non-corridor"
    best_dist = float("inf")
    for name, (clat, clon) in CORRIDOR_CENTROIDS.items():
        d = haversine(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best = name
    return best, round(best_dist, 3)


def load_spatial_data():
    df = pd.read_csv(DATA_FILE)
    df = df.dropna(subset=["latitude", "longitude"])
    return df


def estimate_spatial_impact(lat, lon, top_k=10):
    df = load_spatial_data().copy()

    # Haversine distance to all historical events
    df["distance_km"] = df.apply(
        lambda row: haversine(lat, lon, row["latitude"], row["longitude"]), axis=1
    )

    nearest = df.sort_values("distance_km").head(top_k).copy()

    top_corridors = nearest["corridor"].value_counts().head(3).index.tolist()
    top_zones = nearest["zone"].value_counts().head(3).index.tolist()
    top_junctions = nearest["junction"].value_counts().head(5).index.tolist()

    avg_distance = nearest["distance_km"].mean()
    avg_duration = nearest["duration_hours"].mean()
    avg_severity = nearest["severity_score"].mean()

    # Also compute the nearest corridor name for network-aware routing
    nearest_corr, nearest_corr_dist = nearest_corridor(lat, lon)

    # Impact radius: severity-based, but also expands when close to a major corridor
    if avg_severity >= 70:
        impact_radius_km = 3.0
    elif avg_severity >= 40:
        impact_radius_km = 2.0
    else:
        impact_radius_km = 1.0

    # Expand radius if event is on a major corridor (network effect)
    if nearest_corr != "Non-corridor" and nearest_corr_dist < 2.0:
        impact_radius_km *= 1.3

    return {
        "top_corridors": top_corridors,
        "top_zones": top_zones,
        "top_junctions": top_junctions,
        "avg_nearby_distance_km": round(avg_distance, 3),
        "avg_nearby_duration_hours": round(avg_duration, 2),
        "avg_nearby_severity": round(avg_severity, 2),
        "estimated_impact_radius_km": round(impact_radius_km, 2),
        "nearest_corridor": nearest_corr,
        "nearest_corridor_distance_km": nearest_corr_dist,
    }


if __name__ == "__main__":
    result = estimate_spatial_impact(12.9611, 77.5937)
    print(result)
