import pandas as pd
import threading
from config import OUTPUT_DIR

DATA_FILE = OUTPUT_DIR / "processed_theme3.csv"
_cache = None
_cache_lock = threading.Lock()

def normalize_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower()

def load_location_data():
    global _cache
    if _cache is not None:
        return _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
        if not DATA_FILE.exists():
            _cache = pd.DataFrame(columns=["corridor", "zone", "junction", "latitude", "longitude"])
            return _cache
        df = pd.read_csv(DATA_FILE)

        needed = ["corridor", "zone", "junction", "latitude", "longitude"]
        for col in needed:
            if col not in df.columns:
                df[col] = None

        df = df.dropna(subset=["corridor"])
        _cache = df
        return _cache

def resolve_location_from_corridor(corridor_input):
    df = load_location_data().copy()
    corridor_input_norm = normalize_text(corridor_input)

    df["corridor_norm"] = df["corridor"].apply(normalize_text)

    exact = df[df["corridor_norm"] == corridor_input_norm].copy()

    if exact.empty:
        partial = df[df["corridor_norm"].str.contains(corridor_input_norm, na=False)].copy()
    else:
        partial = exact

    if partial.empty:
        return {
            "matched": False,
            "corridor": corridor_input,
            "zone": "Unknown",
            "junction": "Unknown",
            "latitude": 12.9716,
            "longitude": 77.5946
        }

    top_zone = partial["zone"].mode().iloc[0] if partial["zone"].notna().any() else "Unknown"
    top_junction = partial["junction"].mode().iloc[0] if partial["junction"].notna().any() else "Unknown"

    # Use mode junction events for more accurate road-level coordinates
    if top_junction != "Unknown":
        junc_rows = partial[partial["junction"] == top_junction]
        lat = junc_rows["latitude"].median() if junc_rows["latitude"].notna().any() else 12.9716
        lon = junc_rows["longitude"].median() if junc_rows["longitude"].notna().any() else 77.5946
    else:
        lat = partial["latitude"].median() if partial["latitude"].notna().any() else 12.9716
        lon = partial["longitude"].median() if partial["longitude"].notna().any() else 77.5946

    matched_corridor = partial["corridor"].mode().iloc[0]

    return {
        "matched": True,
        "corridor": matched_corridor,
        "zone": top_zone,
        "junction": top_junction,
        "latitude": round(float(lat), 5),
        "longitude": round(float(lon), 5)
    }

def get_nearby_junctions(corridor_input, limit=6):
    df = load_location_data()
    corridor_norm = normalize_text(corridor_input)
    rows = df[df["corridor"].apply(normalize_text) == corridor_norm]

    if rows.empty:
        return []

    junc_counts = rows.groupby("junction").agg(
        count=("latitude", "size"),
        lat=("latitude", "median"),
        lng=("longitude", "median"),
        zone=("zone", lambda x: x.mode().iloc[0] if x.notna().any() else "Unknown")
    ).reset_index()
    junc_counts = junc_counts.sort_values("count", ascending=False).head(limit)

    return [
        {
            "name": str(r["junction"]),
            "lat": round(float(r["lat"]), 5),
            "lng": round(float(r["lng"]), 5),
            "zone": str(r["zone"]),
            "event_count": int(r["count"])
        }
        for _, r in junc_counts.iterrows()
        if str(r["junction"]).strip()
    ]

if __name__ == "__main__":
    print(resolve_location_from_corridor("Mysore Road"))
    print(resolve_location_from_corridor("MG Road"))