"""
Routing engine that generates actual alternate routes using the corridor
network graph, instead of returning hardcoded text strings.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from event_cause_map import normalize_cause
from corridor_network import find_alternate_routes, format_route, get_neighbors
from spatial_engine import estimate_spatial_impact

CAUSE_STRATEGIES = {
    "public_event":       "Divert general traffic away from event core; reserve inner roads for emergency access",
    "procession":         "Rolling diversion: close procession corridor in short windows, reopen in phases",
    "vip_movement":       "Protected corridor: keep one movement lane open, divert general traffic early",
    "protest":            "Maximum diversion: route traffic well before protest location, protect emergency access",
    "construction":       "Long-duration work-zone diversion: shift traffic to nearest parallel arterial",
    "accident":           "Incident clearance: bypass the node using nearest feasible parallel road",
    "vehiclebreakdown":   "Local bypass: route around stopped vehicle, avoid heavy rerouting unless congestion grows",
    "waterlogging":       "Avoid low-lying stretches and underpasses near the flooded node",
    "congestion":         "Demand-spread: distribute traffic across nearby parallel roads and junctions",
    "potholes":           "Lane-level caution: shift vehicles to safest usable lane or short local detour",
    "tree_fall":          "Restrict affected lane, manage merging, route heavy vehicles away",
    "road_conditions":    "Mark affected lane, guide traffic to safer positions with short detours",
    "debris":             "Block affected lane, merge traffic into adjacent lanes with cones and flaggers",
    "fog_low_visibility": "Reduce speed limits, deploy fog warnings at corridor entry, keep all lanes open",
}


def suggest_diversion_routes(event_cause, severity_label, latitude, longitude, corridor="Non-corridor"):
    # Get spatial context (nearby corridors and junctions)
    spatial = estimate_spatial_impact(latitude, longitude)
    top_corridors = spatial.get("top_corridors", [corridor])
    top_junctions = spatial.get("top_junctions", [])
    radius = spatial.get("estimated_impact_radius_km", 1.0)

    cause = normalize_cause(event_cause)
    diversion_strategy = CAUSE_STRATEGIES.get(cause, "Standard monitoring")
    if severity_label == "High":
        diversion_strategy = f"HIGH-SEVERITY: {diversion_strategy}"
    elif severity_label == "Medium":
        diversion_strategy = f"ELEVATED: {diversion_strategy}"

    # Generate alternate routes from the corridor network graph
    alt_routes = []
    seen = set()
    for c in top_corridors[:3]:
        if c in seen or c == "Non-corridor":
            continue
        seen.add(c)
        neighbors = get_neighbors(c)
        for neighbor, _ in neighbors[:2]:
            alts = find_alternate_routes(c, neighbor)
            for route in alts:
                formatted = format_route(route)
                if formatted and formatted not in alt_routes:
                    alt_routes.append(formatted)

    # If graph returned nothing, use more general fallback
    if not alt_routes:
        for c in top_corridors[:3]:
            if c == "Non-corridor":
                alt_routes.append("Use nearby internal road network for local dispersal")
            elif c == "Mysore Road":
                alt_routes.append("Divert via Chord Road and inner connector roads")
            elif "Bellary" in c:
                alt_routes.append("Divert via Hebbal flyover service routes")
            elif "Tumkur" in c:
                alt_routes.append("Divert via NICE Road entry points")
            elif "ORR" in c:
                alt_routes.append("Prefer ORR service roads and adjacent parallel connectors")
            else:
                alt_routes.append(f"Use parallel arterial roads near {c}")
        alt_routes = list(dict.fromkeys(alt_routes))[:4]

    affected_nodes = top_junctions[:3] if top_junctions else ["Nearest major junction"]

    return {
        "diversion_strategy": diversion_strategy,
        "estimated_impact_radius_km": radius,
        "affected_nodes": affected_nodes,
        "alternate_routes": alt_routes,
    }
