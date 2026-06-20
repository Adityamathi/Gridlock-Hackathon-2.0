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
    # --- Outer Ring Road (ring) ---
    "ORR East 1":       [("ORR East 2", 1), ("ORR North 1", 2), ("ORR West 1", 3), ("Old Airport Road", 1), ("Old Madras Road", 1)],
    "ORR East 2":       [("ORR East 1", 1), ("ORR North 2", 2), ("ORR West 1", 3), ("Hosur Road", 1), ("Varthur Road", 1)],
    "ORR North 1":      [("ORR North 2", 1), ("ORR East 1", 2), ("Bellary Road 1", 1), ("Bellary Road 2", 1), ("Tumkur Road", 2)],
    "ORR North 2":      [("ORR North 1", 1), ("ORR East 2", 2), ("Bellary Road 2", 1)],
    "ORR West 1":       [("ORR East 1", 3), ("ORR East 2", 3), ("Mysore Road", 1), ("Bannerghata Road", 1), ("West of Chord Road", 1)],

    # --- Radial corridors (connecting core to ORR) ---
    "Mysore Road":      [("ORR West 1", 1), ("West of Chord Road", 1), ("CBD 1", 2), ("CBD 2", 2)],
    "Bellary Road 1":   [("ORR North 1", 1), ("Bellary Road 2", 1), ("CBD 1", 2)],
    "Bellary Road 2":   [("ORR North 1", 1), ("ORR North 2", 1), ("Bellary Road 1", 1)],
    "Tumkur Road":      [("ORR North 1", 2), ("CBD 1", 3), ("CBD 2", 3)],
    "Old Airport Road": [("ORR East 1", 1), ("CBD 1", 1), ("CBD 2", 1)],
    "Varthur Road":     [("ORR East 2", 1), ("Old Airport Road", 2)],
    "Hosur Road":       [("ORR East 2", 1), ("ORR West 1", 2), ("CBD 2", 2)],
    "Old Madras Road":  [("ORR East 1", 1), ("ORR East 2", 2)],
    "Bannerghata Road": [("ORR West 1", 1), ("CBD 2", 3)],
    "West of Chord Road": [("ORR West 1", 1), ("Mysore Road", 1), ("CBD 1", 2)],
    "CBD 1":            [("CBD 2", 1), ("Old Airport Road", 1), ("Bellary Road 1", 2), ("West of Chord Road", 2), ("Mysore Road", 2), ("Tumkur Road", 3)],
    "CBD 2":            [("CBD 1", 1), ("Hosur Road", 2), ("Mysore Road", 2), ("Tumkur Road", 3), ("Bannerghata Road", 3), ("Old Airport Road", 1)],
    "Non-corridor":     [("CBD 1", 1), ("CBD 2", 1), ("Mysore Road", 2)],
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
