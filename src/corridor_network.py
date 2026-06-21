"""
Corridor-level road network graph for Bangalore's major arterials.
Used by routing_engine to compute actual alternate routes instead of
returning hardcoded text strings.

Topology (simplified):
  ORR is a ring: North → East → South → West → North
  Radial corridors connect the CBD/core to ORR and beyond
"""

# Corridor adjacency graph: which corridors connect to which
# Format: {corridor: [(neighbor, weight), ...]}
# Weight = approximate travel time / distance (lower = closer)
CORRIDOR_GRAPH = {
    "ORR East 1": [("ORR East 2", 1), ("ORR North 1", 2), ("Old Airport Road", 2), ("Old Madras Road", 3), ("Jeevanbheemanagar Road", 3.1)],
    "ORR East 2": [("ORR East 1", 1), ("ORR North 2", 2), ("Hosur Road", 3), ("Varthur Road", 3), ("HAL Old Airport Road", 0.9), ("Bellandur Road", 3.1), ("Whitefield Road", 5.3), ("Electronic City Road", 10.4)],
    "ORR North 1": [("ORR North 2", 1), ("ORR East 1", 2), ("Bellary Road 1", 2), ("Bellary Road 2", 2), ("Hennur Main Road", 3), ("Hennuru Road", 2.2)],
    "ORR North 2": [("ORR North 1", 1), ("ORR East 2", 2), ("Bellary Road 2", 2), ("Hennuru Road", 2.6), ("K.R. Pura Road", 6.5)],
    "ORR West 1": [("ORR East 1", 3), ("ORR East 2", 3), ("Mysore Road", 3), ("Bannerghata Road", 3), ("West of Chord Road", 1), ("Banashankari Road", 1.2), ("Basavanagudi Road", 1.6), ("Jayanagara Road", 2.3), ("JP Nagar Road", 2.7), ("City Market Road", 3.0), ("VV Puram Road", 3.1), ("Wilson Garden Road", 3.2), ("KS Layout Road", 3.3), ("Thalagattapura Road", 6.8)],
    "Mysore Road": [("ORR West 1", 1), ("West of Chord Road", 1), ("Magadi Road", 2), ("Byatarayanapura Road", 1.8), ("Jnanabharathi Road", 2.7), ("Kengeri Road", 4.2), ("Kamakshipalya Road", 6.3)],
    "Bellary Road 1": [("ORR North 1", 1), ("Bellary Road 2", 1), ("Hennur Main Road", 3), ("IRR(Thanisandra road)", 3), ("KG Halli Road", 2.2), ("Kodigehalli Road", 3.0), ("RT Nagar Road", 3.1), ("Sadashivanagar Road", 4.0), ("Jalahalli Road", 6.7), ("Yelahanka Road", 8.1)],
    "Bellary Road 2": [("ORR North 1", 1), ("ORR North 2", 1), ("Bellary Road 1", 1), ("Kodigehalli Road", 4.2), ("Yelahanka Road", 5.6), ("Chikkajala Road", 15.7), ("Devanahalli Airport Road", 22.9)],
    "Tumkur Road": [("ORR North 1", 2), ("West of Chord Road", 3), ("Magadi Road", 4), ("Rajajinagar Road", 0.9), ("Yeshwanthpura Road", 2.1), ("Malleshwaram Road", 3.4), ("Sadashivanagar Road", 3.6), ("Jalahalli Road", 4.6), ("Peenya Road", 5.7), ("Chikkabanavara Road", 6.3)],
    "Old Airport Road": [("ORR East 1", 1), ("CBD 1", 1), ("CBD 2", 1), ("Varthur Road", 2), ("Jeevanbheemanagar Road", 1.2), ("Halasur Road", 2.5), ("Adugodi Road", 3.8), ("Banaswadi Road", 3.9)],
    "Varthur Road": [("ORR East 2", 1), ("Old Airport Road", 2), ("Whitefield Road", 3), ("HAL Old Airport Road", 0.6), ("Whitefield Road", 4.0), ("Mahadevapura Road", 7.0)],
    "Hosur Road": [("ORR East 2", 1), ("ORR West 1", 2), ("CBD 2", 2), ("Electronic City Road", 5), ("Madiwala Road", 0.5), ("Mico Layout Road", 2.9), ("Hulimavu Road", 3.0), ("Electronic City Road", 8.1)],
    "Old Madras Road": [("ORR East 1", 1), ("ORR East 2", 2), ("Banaswadi Road", 2), ("Banaswadi Road", 1.9), ("K.R. Pura Road", 4.0), ("Mahadevapura Road", 7.0)],
    "Bannerghata Road": [("ORR West 1", 1), ("CBD 2", 3), ("Jayanagara Road", 1), ("JP Nagar Road", 1), ("JP Nagar Road", 0.5), ("Jayanagara Road", 1.0), ("Mico Layout Road", 2.2), ("Banashankari Road", 2.4), ("Madiwala Road", 4.0), ("KS Layout Road", 4.3), ("Hulimavu Road", 4.7), ("Thalagattapura Road", 6.4)],
    "West of Chord Road": [("ORR West 1", 1), ("Mysore Road", 1), ("CBD 1", 2), ("Magadi Road", 2), ("Vijayanagara Road", 1.2), ("Magadi Road (Local)", 2.0), ("Chamarajpet Road", 2.3), ("Sheshadripuram Road", 2.9), ("Upparpet Road", 2.9), ("VV Puram Road", 2.9), ("City Market Road", 3.4), ("Basavanagudi Road", 3.9), ("Malleshwaram Road", 4.4), ("Yeshwanthpura Road", 6.5)],
    "CBD 1": [("CBD 2", 1), ("Old Airport Road", 1), ("West of Chord Road", 2), ("Shivajinagar Road", 1), ("Shivajinagar Road", 1.2), ("Ashok Nagar Road", 1.8), ("Cubbon Park Road", 1.9), ("Halasuru Gate Road", 2.0), ("High Ground Road", 2.4), ("Pulikeshinagar Road", 2.4), ("Upparpet Road", 3.1), ("RT Nagar Road", 3.6), ("Sheshadripuram Road", 3.7), ("Chamarajpet Road", 3.8)],
    "CBD 2": [("CBD 1", 1), ("Hosur Road", 2), ("Bannerghata Road", 3), ("Ashok Nagar Road", 1), ("Halasur Road", 1), ("Ashok Nagar Road", 0.3), ("Halasur Road", 1.3), ("Shivajinagar Road", 2.6), ("Wilson Garden Road", 3.0), ("Halasuru Gate Road", 3.1), ("Adugodi Road", 3.1), ("Cubbon Park Road", 3.2), ("Pulikeshinagar Road", 3.3), ("High Ground Road", 4.0)],
    "Airport New South Road": [("Bellandur Road", 3), ("Bellandur Road", 4.1)],
    "Hennur Main Road": [("ORR North 1", 3), ("Bellary Road 1", 3), ("KG Halli Road", 2), ("KG Halli Road", 1.5)],
    "IRR(Thanisandra road)": [("Bellary Road 1", 3), ("Bellary Road 2", 3)],
    "Magadi Road": [("Mysore Road", 2), ("West of Chord Road", 2), ("Tumkur Road", 4), ("Vijayanagara Road", 1), ("Vijayanagara Road", 1.4), ("Byatarayanapura Road", 1.8), ("Jnanabharathi Road", 2.5), ("Magadi Road (Local)", 3.9), ("Rajajinagar Road", 4.4), ("Kamakshipalya Road", 5.1), ("Kengeri Road", 7.0), ("Peenya Road", 8.9), ("Chikkabanavara Road", 9.5)],
    "Non-corridor": [("CBD 1", 1), ("CBD 2", 1), ("Mysore Road", 2)],
    "Adugodi Road": [("CBD 2", 3.1), ("Old Airport Road", 3.8)],
    "Ashok Nagar Road": [("CBD 2", 0.3), ("CBD 1", 1.8)],
    "Banashankari Road": [("ORR West 1", 1.2), ("Bannerghata Road", 2.4)],
    "Banaswadi Road": [("Old Madras Road", 1.9), ("Old Airport Road", 3.9)],
    "Basavanagudi Road": [("ORR West 1", 1.6), ("West of Chord Road", 3.9)],
    "Bellandur Road": [("ORR East 2", 3.1), ("Airport New South Road", 4.1)],
    "Byatarayanapura Road": [("Magadi Road", 1.8), ("Mysore Road", 1.8)],
    "Chamarajpet Road": [("West of Chord Road", 2.3), ("CBD 1", 3.8)],
    "Chikkabanavara Road": [("Tumkur Road", 6.3), ("Magadi Road", 9.5)],
    "Chikkajala Road": [("Bellary Road 2", 15.7)],
    "City Market Road": [("ORR West 1", 3.0), ("West of Chord Road", 3.4)],
    "Cubbon Park Road": [("CBD 1", 1.9), ("CBD 2", 3.2)],
    "Devanahalli Airport Road": [("Bellary Road 2", 22.9)],
    "Electronic City Road": [("Hosur Road", 8.1), ("ORR East 2", 10.4)],
    "HAL Old Airport Road": [("Varthur Road", 0.6), ("ORR East 2", 0.9)],
    "Halasur Road": [("CBD 2", 1.3), ("Old Airport Road", 2.5)],
    "Halasuru Gate Road": [("CBD 1", 2.0), ("CBD 2", 3.1)],
    "Hennuru Road": [("ORR North 1", 2.2), ("ORR North 2", 2.6)],
    "High Ground Road": [("CBD 1", 2.4), ("CBD 2", 4.0)],
    "Hulimavu Road": [("Hosur Road", 3.0), ("Bannerghata Road", 4.7)],
    "JP Nagar Road": [("Bannerghata Road", 0.5), ("ORR West 1", 2.7)],
    "Jalahalli Road": [("Tumkur Road", 4.6), ("Bellary Road 1", 6.7)],
    "Jayanagara Road": [("Bannerghata Road", 1.0), ("ORR West 1", 2.3)],
    "Jeevanbheemanagar Road": [("Old Airport Road", 1.2), ("ORR East 1", 3.1)],
    "Jnanabharathi Road": [("Magadi Road", 2.5), ("Mysore Road", 2.7)],
    "K.R. Pura Road": [("Old Madras Road", 4.0), ("ORR North 2", 6.5)],
    "KG Halli Road": [("Hennur Main Road", 1.5), ("Bellary Road 1", 2.2)],
    "KS Layout Road": [("ORR West 1", 3.3), ("Bannerghata Road", 4.3)],
    "Kamakshipalya Road": [("Magadi Road", 5.1), ("Mysore Road", 6.3)],
    "Kengeri Road": [("Mysore Road", 4.2), ("Magadi Road", 7.0)],
    "Kodigehalli Road": [("Bellary Road 1", 3.0), ("Bellary Road 2", 4.2)],
    "Madiwala Road": [("Hosur Road", 0.5), ("Bannerghata Road", 4.0)],
    "Magadi Road (Local)": [("West of Chord Road", 2.0), ("Magadi Road", 3.9)],
    "Mahadevapura Road": [("Varthur Road", 7.0), ("Old Madras Road", 7.0)],
    "Malleshwaram Road": [("Tumkur Road", 3.4), ("West of Chord Road", 4.4)],
    "Mico Layout Road": [("Bannerghata Road", 2.2), ("Hosur Road", 2.9)],
    "Peenya Road": [("Tumkur Road", 5.7), ("Magadi Road", 8.9)],
    "Pulikeshinagar Road": [("CBD 1", 2.4), ("CBD 2", 3.3)],
    "RT Nagar Road": [("Bellary Road 1", 3.1), ("CBD 1", 3.6)],
    "Rajajinagar Road": [("Tumkur Road", 0.9), ("Magadi Road", 4.4)],
    "Sadashivanagar Road": [("Tumkur Road", 3.6), ("Bellary Road 1", 4.0)],
    "Sheshadripuram Road": [("West of Chord Road", 2.9), ("CBD 1", 3.7)],
    "Shivajinagar Road": [("CBD 1", 1.2), ("CBD 2", 2.6)],
    "Thalagattapura Road": [("Bannerghata Road", 6.4), ("ORR West 1", 6.8)],
    "Upparpet Road": [("West of Chord Road", 2.9), ("CBD 1", 3.1)],
    "VV Puram Road": [("West of Chord Road", 2.9), ("ORR West 1", 3.1)],
    "Vijayanagara Road": [("West of Chord Road", 1.2), ("Magadi Road", 1.4)],
    "Whitefield Road": [("Varthur Road", 4.0), ("ORR East 2", 5.3)],
    "Wilson Garden Road": [("CBD 2", 3.0), ("ORR West 1", 3.2)],
    "Yelahanka Road": [("Bellary Road 2", 5.6), ("Bellary Road 1", 8.1)],
    "Yeshwanthpura Road": [("Tumkur Road", 2.1), ("West of Chord Road", 6.5)],
}


def get_neighbors(corridor):
    """Return list of (neighbor_name, weight) for a corridor."""
    return CORRIDOR_GRAPH.get(corridor, [])


def shortest_path(start, end, max_steps=6):
    """BFS shortest path between two corridors. Returns list of corridor names."""
    if start == end:
        return [start]

    visited = {start}
    queue = [[start]]

    for _ in range(max_steps):
        next_queue = []
        for path in queue:
            last = path[-1]
            for neighbor, _ in CORRIDOR_GRAPH.get(last, []):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_queue.append(path + [neighbor])
        queue = next_queue
        if not queue:
            break

    return None


def find_alternate_routes(from_corridor, to_corridor=None, max_suggestions=3):
    """
    Find alternate routes between corridors.
    If to_corridor is None, returns nearby corridors.
    """
    if to_corridor:
        path = shortest_path(from_corridor, to_corridor)
        if path and len(path) > 1:
            return [path]
        return []

    # No destination: return top neighbor routes (diversion starting points)
    neighbors = get_neighbors(from_corridor)
    routes = []
    for neighbor, _ in neighbors[:max_suggestions]:
        path = shortest_path(from_corridor, neighbor)
        if path:
            routes.append(path)
    return routes


def format_route(path):
    """Format a corridor path as a human-readable diversion route."""
    if not path or len(path) < 2:
        return ""
    return " -> ".join(path)
