import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from config import OUTPUT_DIR
from corridor_network import CORRIDOR_GRAPH

DATA_FILE = OUTPUT_DIR / "processed_theme3.csv"
_spatial_data_cache = None

CORRIDOR_CENTROIDS = {
    '100 Feet Road, Kanteerava Studio Circle': (13.021037, 77.528271),
    '10th Main Road, Achaiah Chetty Layout': (12.936723, 77.584169),
    '11th Cross Road, Acharya Sri Ramanuja Circle': (12.990048, 77.588305),
    '11th Main Road, Sri Aurobindo Circle': (12.920233, 77.585864),
    '12th Cross Road, Lakksandra Extension': (12.947109, 77.597369),
    '13th Cross Road, Bashyam Circle': (12.929445, 77.598246),
    '1st Cross Road, Koramangala Water Tank Junction': (12.962528, 77.601287),
    '1st Main Road, Sri Vijayamaruthi Circle': (13.011711, 77.584925),
    '24th Main Road, Sarakki Agrahara': (12.906159, 77.585733),
    '27th Cross Road, Dr BR Ambedkar Circle': (12.938229, 77.746727),
    '2nd Cross Road, MTB Area': (12.918617, 77.58946),
    '2nd Main Road, Abdul Patel Syed Layout': (13.03336, 77.581667),
    '3rd Cross Road, Bommanahalli Circle': (12.989559, 77.573515),
    '3rd Main Road, Chakkasandra': (13.022925, 77.589606),
    '46th Cross Road, Sri Aurobindo Circle': (12.917027, 77.585271),
    '4th Cross Road, Papareddypalya Circle': (12.993402, 77.605613),
    '4th Main Road, Shri Satya Sai Circle': (12.964056, 77.580339),
    '5th Cross Road, Uday Nagar': (12.959837, 77.620765),
    '5th Main Road, Anandgiri Extension': (12.961081, 77.580677),
    '60 Feet Road, KK Layout': (12.968843, 77.503677),
    '6th Main Road, BDA Industrial Suburb': (12.899413, 77.622178),
    '7th Cross Road, BDA Junction': (12.922468, 77.603662),
    '7th Main Road, Balaji Layout': (12.985429, 77.548411),
    '80 Feet Ring Road, Harikara Vidvan Sri R Gururajulu Naidu Circle': (12.997965, 77.554068),
    '80 Feet Road, Block 2': (12.99335, 77.576376),
    '8th Cross Road, RR Palace': (13.05616, 77.602548),
    '9th Cross Road, Kaniyar Colony': (12.9355, 77.570887),
    '9th Main Road, Shri Satya Sai Circle': (12.92757, 77.583563),
    'Adugodi Road, Krupanidhi College Junction': (12.935309, 77.624087),
    'Airport New South Road': (13.029204, 77.632328),
    'Amrutha College Road, Sri Venkateshwara Circle': (12.878553, 77.672052),
    'Ashok Nagar Road, Ashirwadam Junction': (12.962596, 77.61434),
    'Assayee Road, Sham Mansion Apartment': (12.993901, 77.619056),
    'Banashankari Road, Sarbandapalya': (12.917007, 77.570275),
    'Banaswadi Road, Gopalan Signature Mall': (12.993693, 77.661914),
    'Bannerghata Road': (12.899662, 77.599962),
    'Basavanagudi Road, Cauvery Circle': (12.943637, 77.575194),
    'Begur Main Road, Alpine Park Apartment': (12.898018, 77.626445),
    'Bellandur Road, Kasavanahalli': (12.908248, 77.675117),
    'Bellary Road 1': (13.014564, 77.584794),
    'Bellary Road 2': (13.099002, 77.598905),
    'Broadway Road, Chandni Chowk': (12.985821, 77.605095),
    'Byatarayanapura Road, Nagarabavi Circle': (12.957991, 77.518978),
    'CBD 1': (12.980948, 77.608524),
    'CBD 2': (12.983263, 77.597007),
    'CV Raman Road, SBD Township Sector B': (13.016134, 77.561538),
    'Chamarajpet Road, Sangolli Rayanna Circle': (12.974681, 77.570448),
    'Chikkabanavara Road, Nagasandra': (13.049595, 77.501076),
    'Chikkajala Road, Phase 2A': (13.160778, 77.652603),
    'City Market Road, Santhusapete': (12.954954, 77.580428),
    'Cubbon Park Road, Krishna Rajendra Circle': (12.976582, 77.587908),
    'Devanahalli Airport Road, Sri Kanakadasa Circle': (13.243519, 77.707075),
    'Dhanvanthri Road, Ayurvedic Hospital Junction': (12.979621, 77.572791),
    'Dinnur Main Road, Southern Residency Apartment': (13.021911, 77.603049),
    'Doddaballapur Main Road, East Colony': (13.12554, 77.574009),
    'Dr Ambedkar Road, Krishna Rajendra Circle': (12.980173, 77.592988),
    'Dr MH Ambarish Road, C Ranga Swamy Circle': (12.983883, 77.582601),
    'Dr Rajgopal Road, Ashwath Nagar': (13.027322, 77.579494),
    'Dr Rajkumar Puniya Bhoomi Road, Block 6': (12.960448, 77.536945),
    'Dr TCM Royan Road, Cottonpet Circle': (12.972822, 77.569006),
    'Electronic City Road, Pramuk Aqua Heights': (12.839975, 77.676175),
    'Electronics City Flyover, Bommanahalli Circle': (12.879438, 77.64595),
    'Halasur Road, Agaram': (12.962255, 77.629695),
    'Halasuru Gate Road, Ashirwadam Junction': (12.972195, 77.587393),
    'Hennur Main Road': (13.048908, 77.632988),
    'High Ground Road, Karnataka Bhavan Junction': (12.983206, 77.585952),
    'Hoodi Main Road, ESI Road Junction': (12.987853, 77.711047),
    'Hosur Road': (12.913383, 77.624692),
    'Hulimavu Road, Anjaneya Swami Circle': (12.876115, 77.616529),
    'IRR(Thanisandra road)': (12.927679, 77.621417),
    'JP Nagar Road, Sri Aurobindo Circle': (12.912208, 77.58468),
    'Jalahalli Road, Gangamma Circle': (13.052145, 77.546563),
    'Jayamahal Main Road, Enayathulla Mehkri Circle': (13.014434, 77.585354),
    'Jayanagara Road, MTB Area': (12.918617, 77.587258),
    'Jeevanbheemanagar Road, Thimmaiah Reddy Colony': (12.966706, 77.659884),
    'Jnanabharathi Road, Kengunte Circle': (12.963808, 77.504976),
    'K.R. Pura Road, Zero Tolerance Junction': (13.016205, 77.708795),
    'KG Halli Road, Bilal Nagar': (13.01079, 77.615294),
    'KH Road, Ashirwadam Junction': (12.958609, 77.593152),
    'KR Main Road, Professor P Shivshankar Circle': (12.958052, 77.573858),
    'KS Layout Road, Muneshwara Nagar': (12.906977, 77.549643),
    'Kamakshipalya Road, Sattva Anugraha': (12.988449, 77.495102),
    'Kempegowda Road, Skyline Retreat': (12.975272, 77.579927),
    'Kengeri Main Road, Kengunte Circle': (12.957441, 77.503195),
    'Kengeri Road, Ideal Home Township': (12.928597, 77.516732),
    'Kodigehalli Road, Pillappa Layout': (13.062051, 77.57671),
    'Konanakunte Main Road, Jagathguru Shri Sivaratripura Circle': (12.89804, 77.571869),
    'Kumar Krupa Road, Make In India Circle': (12.990617, 77.582223),
    'Lalbagh Main Road, Dr Sri Shantaveera Swami Circle': (12.956105, 77.585761),
    'MBT Road, Block 5 Stage 1': (13.031636, 77.643119),
    'MS Ramaiah Road, BEL Circle': (13.04314, 77.557137),
    'Madiwala Road, Krishna Reddy Layout': (12.900538, 77.626098),
    'Magadi Road': (12.987821, 77.509899),
    'Magadi Road (Local), Okalipuram Junction': (12.98207, 77.5643),
    'Mahadevapura Road, Sadaramangala Industrial Area': (12.992418, 77.735038),
    'Malleshwaram Road, Sri Maramma Temple Circle': (13.000867, 77.571337),
    'Mico Layout Road, 29th BTM Road Junction': (12.91857, 77.608861),
    'Millers Road, Chavundaraya Circle': (12.99324, 77.595445),
    'Mumbai Bengaluru Highway, Nadaprabhu Kempegowda Circle': (13.048897, 77.497147),
    'Muthsandra Main Road, KSRTC Travel House Junction': (12.942487, 77.747296),
    'Mysore Road': (12.963736, 77.583887),
    'NICE Road, Madavara': (12.945876, 77.475418),
    'Nagarabhavi Main Road, Block 12': (12.960267, 77.514285),
    'Netaji Road, Puttanna Junction': (12.997005, 77.60824),
    'Nice Road, Sunbeam 1': (13.056925, 77.47755),
    'Non-corridor': (12.964287, 77.590126),
    'ORR East 1': (12.943792, 77.682199),
    'ORR East 2': (12.969596, 77.700585),
    'ORR North 1': (13.023186, 77.646855),
    'ORR North 2': (13.042767, 77.549398),
    'ORR West 1': (12.923394, 77.554292),
    'Old Airport Road': (12.959188, 77.656934),
    'Old Madras Road': (12.98372, 77.63983),
    'Padmabhushan Dr RK Srikantan Road, Kalpataru Kalpavriksha': (12.984774, 77.574658),
    'Padmasri CK Venkata Ramaiah Road, Sadashivanagar Junction': (13.031321, 77.570012),
    'Peenya Road, Sobha Garrison': (13.046562, 77.502009),
    'Pulikeshinagar Road, Sindhi Colony': (12.994925, 77.614902),
    'RT Nagar Road, Vasanth Enclave': (13.005848, 77.595031),
    'Rajajinagar Road, Narasimhaswamy Layout': (13.009269, 77.52991),
    'SM Road, Patel Shamanna Layout': (13.054714, 77.53504),
    'Sadashivanagar Road, Sadashivanagar Junction': (13.014543, 77.572656),
    'Sankey Road, RV Layout': (12.992609, 77.585271),
    'Sarjapur Marathahalli Road, Koramangala Water Tank Junction': (12.927464, 77.621236),
    'Sarjapura Main Road, Dommasandra Anekal Taluka': (12.882886, 77.75426),
    'Seshadri Road, Ayurvedic Hospital Junction': (12.980011, 77.573705),
    'Sheshadripuram Road, Sangolli Rayanna Circle': (12.984555, 77.571693),
    'Shivajinagar Road, Shivaji Nagar': (12.98717, 77.599443),
    'Siddavanahalli Krishna Sharma Road, Sri Maramma Temple Circle': (13.008705, 77.569096),
    'Silk Board Double Decker Flyover, Central Silk Board Staff Quarters': (12.9168, 77.621364),
    'Sir CV Raman Road, Enayathulla Mehkri Circle': (13.014562, 77.583516),
    'Sri Venkataranga Ayangar Road, Acharya Sri Ramanuja Circle': (13.006155, 77.571196),
    'Sri Venkataranga Iyengar Road, Mill Corner Junction': (12.99244, 77.571428),
    'Srinivagilu Main Road, KR Garden': (12.943119, 77.621951),
    'Subedar Chatram Road, Shri Rajiv Gandhi Circle': (12.989593, 77.572312),
    'Thalagattapura Road, Hosahalli South Taluka': (12.87449, 77.539264),
    'Tumkur Road': (13.034429, 77.530266),
    'Upparpet Road, Mysore Bank Circle': (12.97529, 77.578041),
    'VV Puram Road, Professor P Shivshankar Circle': (12.957145, 77.573975),
    'Varthur Road': (12.955186, 77.736844),
    'Vijayanagara Road, Binny Layout': (12.975658, 77.541101),
    'Vinoba Nagar Main Road, Narasimha Block': (13.020097, 77.618895),
    'West of Chord Road': (12.995731, 77.549),
    'Whitefield Main Road, HBK Layout': (12.979765, 77.751575),
    'Whitefield Road, Sadaramangala Industrial Area': (12.964677, 77.741828),
    'Wilson Garden Road, Dr Ambedkar Social Welfare Association': (12.948593, 77.592818),
    'Yelahanka Road, Nagarjuna Aster Park': (13.100726, 77.580448),
    'Yeshwanthpura Road, Nada Prabhu Kempegowda Circle': (13.033956, 77.557356),
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
    best = "Non-corridor"
    best_dist = float("inf")
    for name, (clat, clon) in CORRIDOR_CENTROIDS.items():
        d = haversine(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best = name
    return best, round(best_dist, 3)

def load_spatial_data():
    global _spatial_data_cache
    if _spatial_data_cache is not None:
        return _spatial_data_cache
    df = pd.read_csv(DATA_FILE)
    df = df.dropna(subset=["latitude", "longitude"])
    _spatial_data_cache = df
    return df

def estimate_spatial_impact(lat, lon):
    df = load_spatial_data()
    distances = df.apply(
        lambda r: haversine(lat, lon, r["latitude"], r["longitude"]),
        axis=1
    )
    nearby = df[distances <= 3.0].copy()
    if len(nearby) == 0:
        _, dist_to_nearest = nearest_corridor(lat, lon)
        return {
            "estimated_impact_radius_km": 0.8,
            "nearby_event_count": 0,
            "avg_nearby_duration_hours": None,
            "nearest_corridor": "Non-corridor",
            "distance_to_nearest_km": dist_to_nearest,
        }
    nearby["_dist"] = distances[distances <= 3.0]
    avg_dur = nearby["duration_hours"].median()
    impact_radius = min(3.0, max(0.5, nearby["_dist"].quantile(0.85)))
    top_corridor_rows = nearby.groupby("corridor").size().sort_values(ascending=False)
    nearest_name = top_corridor_rows.index[0] if not top_corridor_rows.empty else "Non-corridor"
    top_corridors = top_corridor_rows.index[:3].tolist() if not top_corridor_rows.empty else []
    top_junction_rows = nearby.groupby("junction").size().sort_values(ascending=False)
    top_junctions = top_junction_rows.index[:3].tolist() if not top_junction_rows.empty else []
    _, dist_to_nearest = nearest_corridor(lat, lon)
    return {
        "estimated_impact_radius_km": round(impact_radius, 2),
        "nearby_event_count": int(len(nearby)),
        "avg_nearby_duration_hours": round(float(avg_dur), 2) if pd.notna(avg_dur) else None,
        "nearest_corridor": nearest_name,
        "distance_to_nearest_km": dist_to_nearest,
        "top_corridors": top_corridors,
        "top_junctions": top_junctions,
    }

if __name__ == "__main__":
    result = estimate_spatial_impact(12.9611, 77.5937)
    print(result)
