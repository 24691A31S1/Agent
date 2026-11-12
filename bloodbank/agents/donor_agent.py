"""Donor Matching Agent: when blood is not available nearby, finds eligible
registered donors who can help arrange the required blood."""
import pandas as pd


def find_eligible_donors(donors_df: pd.DataFrame, blood_group: str,
                          city: str = None, limit: int = 10):
    """
    Return eligible donors (>=6 months since last donation) with a matching
    blood group, optionally filtered by city, nearest matches first (same
    city prioritized).
    """
    matches = donors_df[
        (donors_df["blood_group"] == blood_group) & (donors_df["eligible_to_donate"])
    ].copy()

    if city:
        matches["same_city"] = matches["city"] == city
        matches = matches.sort_values(by=["same_city", "days_since_donation"],
                                       ascending=[False, False])
    else:
        matches = matches.sort_values(by="days_since_donation", ascending=False)

    return matches.head(limit)
