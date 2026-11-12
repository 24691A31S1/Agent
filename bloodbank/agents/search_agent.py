"""Search Agent: receives a request and searches connected blood bank
inventory for real-time availability."""
import pandas as pd
from utils.geo import haversine_km

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

COMPATIBLE_DONORS = {
    "A+": ["A+", "A-", "O+", "O-"],
    "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"],
    "O-": ["O-"],
}


def search_blood_banks(banks_df: pd.DataFrame, inventory_df: pd.DataFrame,
                        blood_group: str, units_required: int,
                        user_lat: float, user_lon: float):
    """
    Search all connected blood banks for the requested blood group.
    Returns a DataFrame sorted by distance, annotated with availability.
    """
    stock = inventory_df[inventory_df["blood_group"] == blood_group]
    merged = banks_df.merge(
        stock, left_on="id", right_on="blood_bank_id", how="left"
    )
    merged["units_available"] = merged["units_available"].fillna(0).astype(int)

    merged["distance_km"] = merged.apply(
        lambda r: round(haversine_km(user_lat, user_lon, r["latitude"], r["longitude"]), 1),
        axis=1,
    )
    merged["can_fulfill"] = merged["units_available"] >= units_required

    result = merged.sort_values(
        by=["can_fulfill", "distance_km"], ascending=[False, True]
    ).reset_index(drop=True)
    return result


def get_alternative_groups(blood_group: str):
    """Suggest compatible blood groups a patient could also receive."""
    return COMPATIBLE_DONORS.get(blood_group, [])
