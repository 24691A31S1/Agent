"""Recommendation Agent: analyzes search results, compares options, and
recommends the nearest and best available blood bank."""
from utils.geo import estimate_travel_time_minutes


def recommend_best(results_df, emergency_level="High"):
    """
    Pick the best blood bank from search results.
    Priority: can fulfill request -> shortest distance -> higher rating.
    Returns a dict describing the recommendation, or None if nothing fulfills it.
    """
    fulfillable = results_df[results_df["can_fulfill"]]
    if fulfillable.empty:
        return None

    fulfillable = fulfillable.sort_values(
        by=["distance_km", "rating"], ascending=[True, False]
    )
    best = fulfillable.iloc[0]

    mode = "ambulance" if emergency_level == "Critical" else "hospital_vehicle"
    eta = estimate_travel_time_minutes(best["distance_km"], mode=mode)

    return {
        "bank_id": int(best["id"]),
        "name": best["name"],
        "address": best["address"],
        "phone": best["phone"],
        "distance_km": best["distance_km"],
        "units_available": int(best["units_available"]),
        "rating": best["rating"],
        "eta_minutes": eta,
        "transport_mode": mode,
        "latitude": float(best["latitude"]),
        "longitude": float(best["longitude"]),
    }


def top_alternatives(results_df, exclude_id=None, n=3):
    """Return the next-best fulfillable alternatives (for comparison display)."""
    fulfillable = results_df[results_df["can_fulfill"]]
    if exclude_id is not None:
        fulfillable = fulfillable[fulfillable["id"] != exclude_id]
    return fulfillable.sort_values("distance_km").head(n)
