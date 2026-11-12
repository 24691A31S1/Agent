"""Notification Agent: sends a REAL SMS alert to the phone number the user
provided at login (and, in a real deployment, to matched donors/hospitals)
whenever a search completes.

This uses Twilio's REST API directly. There is no "pretend it worked"
fallback — if credentials aren't configured, the app tells you exactly
that, instead of showing a message that looks like a real SMS went out.
"""
import os


def _get_twilio_credentials(st):
    """
    Look for Twilio credentials in, in order of priority:
      1. Streamlit secrets (.streamlit/secrets.toml or Community Cloud "Secrets")
      2. Environment variables (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER)
    """
    sid = token = from_number = None
    try:
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_number = st.secrets["twilio"]["from_number"]
    except Exception:
        pass

    sid = sid or os.environ.get("TWILIO_ACCOUNT_SID")
    token = token or os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = from_number or os.environ.get("TWILIO_FROM_NUMBER")

    if sid and token and from_number:
        return sid, token, from_number
    return None


def is_sms_configured(st) -> bool:
    return _get_twilio_credentials(st) is not None


def send_sms(st, to_number: str, message: str):
    """
    Send a REAL SMS to `to_number` via Twilio. Returns a dict:
        {status: "sent" | "not_configured" | "error", detail: str, sid: str|None}

    "not_configured" means Twilio credentials are missing — the caller
    should surface this clearly rather than implying a message was sent.
    """
    if not to_number:
        return {"status": "error", "detail": "No phone number on file for this user.", "sid": None}

    creds = _get_twilio_credentials(st)
    if not creds:
        return {
            "status": "not_configured",
            "detail": (
                "Twilio isn't configured yet, so no SMS can be sent. Add "
                "account_sid / auth_token / from_number under [twilio] in "
                ".streamlit/secrets.toml (or set TWILIO_ACCOUNT_SID / "
                "TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER as environment "
                "variables) to enable real SMS delivery."
            ),
            "sid": None,
        }

    sid, token, from_number = creds
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        msg = client.messages.create(body=message, from_=from_number, to=to_number)
        return {"status": "sent", "detail": f"SMS sent to {to_number}", "sid": msg.sid}
    except Exception as e:
        return {"status": "error", "detail": str(e), "sid": None}


def build_not_available_message(blood_group, city, alt_bank=None, donor_count=0):
    if alt_bank:
        return (
            f"Blood Bank Agent: {blood_group} blood not found in {city}. "
            f"Nearest option: {alt_bank['name']} ({alt_bank['distance_km']} km, "
            f"{alt_bank['units_available']} units). Call {alt_bank['phone']}."
        )
    return (
        f"Blood Bank Agent: {blood_group} blood is currently unavailable near "
        f"{city}. We found {donor_count} eligible donor(s) and have notified "
        f"the nearest hospital to help arrange it. We'll update you shortly."
    )


def build_available_message(blood_group, bank):
    return (
        f"Blood Bank Agent: {blood_group} blood available at {bank['name']} "
        f"({bank['distance_km']} km away, {bank['units_available']} units). "
        f"Contact: {bank['phone']}. ETA by {bank['transport_mode'].replace('_',' ')}: "
        f"{bank['eta_minutes']} min."
    )


def build_login_welcome_message(name):
    who = name or "there"
    return (
        f"Blood Bank Agent: Hi {who}, you're logged in. We'll text this "
        f"number the moment we find your requested blood."
    )
