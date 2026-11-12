"""
Blood Bank Availability Agent
An AI-powered assistant that finds real-time blood availability across
connected blood banks, recommends the best option, matches eligible donors
when stock is short, and sends a REAL SMS alert to the phone number the
user logged in with.
"""
import re
import streamlit as st
import pandas as pd
from pathlib import Path

from agents.search_agent import search_blood_banks, get_alternative_groups, BLOOD_GROUPS
from agents.recommendation_agent import recommend_best, top_alternatives
from agents.donor_agent import find_eligible_donors
from agents.notification_agent import (
    send_sms, is_sms_configured, build_available_message,
    build_not_available_message, build_login_welcome_message,
)
from agents.chatbot_agent import parse_request, chatbot_reply_intro
from utils.geo import resolve_location, reverse_geocode, CITY_COORDS

DATA_DIR = Path(__file__).parent / "data"

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Blood Bank Availability Agent",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Global styling
# --------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    html, body, [class*="css"] { font-family: 'Segoe UI', 'Inter', sans-serif; }

    .stApp {
        background:
            radial-gradient(circle at 10% 0%, rgba(176,0,15,0.12), transparent 40%),
            radial-gradient(circle at 90% 10%, rgba(31,122,77,0.10), transparent 40%),
            #0b0d12;
    }

    /* ---------- Hero ---------- */
    .hero {
        background: linear-gradient(135deg, #b0000f 0%, #7a0010 55%, #2b0007 100%);
        padding: 2.4rem 2.2rem;
        border-radius: 22px;
        color: white;
        margin-bottom: 1.4rem;
        box-shadow: 0 14px 40px rgba(176,0,15,0.30);
        position: relative;
        overflow: hidden;
    }
    .hero::after {
        content: "";
        position: absolute; top: -60px; right: -60px;
        width: 220px; height: 220px; border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.10), transparent 70%);
    }
    .hero h1 { font-size: 2.2rem; margin-bottom: 0.3rem; font-weight: 800; }
    .hero p { opacity: 0.94; font-size: 1.05rem; margin: 0; max-width: 640px; }
    .pill {
        display: inline-block;
        background: rgba(255,255,255,0.16);
        backdrop-filter: blur(4px);
        padding: 5px 14px;
        border-radius: 999px;
        font-size: 0.8rem;
        margin-right: 8px;
        margin-top: 12px;
        border: 1px solid rgba(255,255,255,0.2);
    }

    /* ---------- Cards ---------- */
    .best-card {
        background: linear-gradient(135deg, #10321f, #0d4429);
        border: 1px solid #1f7a4d;
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        color: #eafff1;
        box-shadow: 0 10px 26px rgba(15,120,60,0.20);
    }
    .best-card h3 { margin-top: 0; color: #7CFFB2; }
    .alt-card {
        background: #16161c;
        border: 1px solid #2c2c35;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        transition: border-color 0.15s ease, transform 0.15s ease;
    }
    .alt-card:hover { border-color: #b0000f; transform: translateY(-1px); }
    .warn-card {
        background: linear-gradient(135deg, #4a1010, #2a0a0a);
        border: 1px solid #a33;
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        color: #ffe0e0;
    }
    .loc-card {
        background: #14151b;
        border: 1px solid #2b2c35;
        border-radius: 14px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.5rem;
        font-size: 0.92rem;
    }
    .loc-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; }

    .badge-critical { color: #ff5c5c; font-weight: 700; }
    .badge-high { color: #ffb84d; font-weight: 700; }
    .badge-moderate { color: #7CFFB2; font-weight: 700; }

    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
    }

    /* ---------- Login screen ---------- */
    .login-wrap {
        max-width: 460px;
        margin: 3.5rem auto 0 auto;
        background: linear-gradient(160deg, #15161d, #0e0f14);
        border: 1px solid #2b2c35;
        border-radius: 22px;
        padding: 2.2rem 2.2rem 1.6rem 2.2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.45);
    }
    .login-badge {
        font-size: 2.6rem; text-align:center; margin-bottom: 0.2rem;
    }
    .login-title { text-align:center; font-size:1.5rem; font-weight:800; color:#fff; margin-bottom:0.2rem;}
    .login-sub { text-align:center; color:#9a9aa5; font-size:0.92rem; margin-bottom:1.6rem; }

    /* ---------- Floating AI chatbot logo ---------- */
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 28px;
        right: 28px;
        z-index: 999999;
    }
    div[data-testid="stPopover"] > div > button,
    div[data-testid="stPopoverButton"] button {
        width: 68px !important;
        height: 68px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #ff2e4d, #b0000f) !important;
        border: 3px solid rgba(255,255,255,0.18) !important;
        box-shadow: 0 10px 28px rgba(176,0,15,0.55), 0 0 0 6px rgba(176,0,15,0.10) !important;
        font-size: 30px !important;
        color: white !important;
        padding: 0 !important;
        line-height: 1 !important;
        transition: transform 0.15s ease;
    }
    div[data-testid="stPopover"] > div > button:hover,
    div[data-testid="stPopoverButton"] button:hover {
        transform: scale(1.06);
    }
    div[data-testid="stPopoverBody"] {
        width: 360px !important;
        max-height: 480px;
        overflow-y: auto;
        border-radius: 16px !important;
    }
    .chat-fab-title {
        font-weight: 700; font-size: 1.02rem; margin-bottom: 2px;
    }
    .chat-fab-sub {
        color: #9a9aa5; font-size: 0.8rem; margin-bottom: 10px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
@st.cache_data
def load_data():
    banks = pd.read_csv(DATA_DIR / "blood_banks.csv")
    inventory = pd.read_csv(DATA_DIR / "blood_inventory.csv")
    donors = pd.read_csv(DATA_DIR / "donors.csv")
    donors["eligible_to_donate"] = donors["eligible_to_donate"].astype(bool)
    return banks, inventory, donors


banks_df, inventory_df, donors_df = load_data()
known_cities = sorted(CITY_COORDS.keys())

# --------------------------------------------------------------------------
# Session state defaults
# --------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None


PHONE_PATTERN = re.compile(r"^\+?[0-9]{10,15}$")


def normalize_phone(raw: str) -> str:
    cleaned = raw.strip().replace(" ", "").replace("-", "")
    if cleaned and not cleaned.startswith("+"):
        # assume India if a bare 10-digit number is given
        if len(cleaned) == 10:
            cleaned = "+91" + cleaned
    return cleaned


# --------------------------------------------------------------------------
# LOGIN GATE — nothing below runs until the user logs in with a real phone
# number. That phone number is what every SMS in this app is sent to.
# --------------------------------------------------------------------------
if st.session_state.user is None:
    st.markdown(
        """
        <div class="login-wrap">
            <div class="login-badge">🩸</div>
            <div class="login-title">Blood Bank Availability Agent</div>
            <div class="login-sub">Log in with your phone number — we'll send your
            SMS alerts straight to it, no separate step needed.</div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form", clear_on_submit=False):
        name_in = st.text_input("Your name", placeholder="e.g. Ramesh Kumar")
        phone_in = st.text_input("Phone number", placeholder="+91XXXXXXXXXX")
        submitted = st.form_submit_button("Log in & continue", use_container_width=True, type="primary")

    if submitted:
        phone_clean = normalize_phone(phone_in)
        if not name_in.strip():
            st.error("Please enter your name.")
        elif not PHONE_PATTERN.match(phone_clean):
            st.error("Please enter a valid phone number, e.g. +919876543210.")
        else:
            st.session_state.user = {"name": name_in.strip(), "phone": phone_clean}
            st.session_state.chat_history.append(
                ("assistant", f"Hi {name_in.strip().split()[0]}! I'm your Blood Bank AI Assistant. "
                              f"Tell me what you need, e.g. \"Need 2 units O+ urgently in Tirupati\".")
            )
            st.rerun()

    if not is_sms_configured(st):
        st.caption(
            "⚠️ Twilio isn't configured in this environment yet, so SMS sending will show "
            "as 'not configured' after you log in. Add your Twilio credentials to "
            ".streamlit/secrets.toml to enable real delivery."
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

user = st.session_state.user

# --------------------------------------------------------------------------
# Hero
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
        <h1>🩸 Blood Bank Availability Agent</h1>
        <p>Welcome back, <b>{user['name']}</b> — find the nearest available blood in
        seconds, powered by AI search, recommendation, donor-matching &amp; real SMS
        alert agents.</p>
        <span class="pill">🔎 {len(banks_df)} blood banks connected</span>
        <span class="pill">🧑‍🤝‍🧑 {len(donors_df)} registered donors</span>
        <span class="pill">📍 {len(known_cities)} cities covered</span>
        <span class="pill">📱 SMS to {user['phone']}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Sidebar — structured request form
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"**Logged in as** {user['name']}  \n📱 {user['phone']}")
    if st.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.last_result = None
        st.session_state.chat_history = []
        st.rerun()
    st.divider()

    st.header("🔍 Request Details")
    blood_group = st.selectbox("Blood Group Required", BLOOD_GROUPS, index=6)
    location_mode = st.radio("Your location", ["Select city", "Enter address"], horizontal=True)
    if location_mode == "Select city":
        city = st.selectbox("City", known_cities, index=known_cities.index("Tirupati") if "Tirupati" in known_cities else 0)
        address = None
    else:
        address = st.text_input("Full address", placeholder="e.g. Tilak Road, Tirupati, Andhra Pradesh")
        city = None
    units_required = st.number_input("Units Required", min_value=1, max_value=20, value=2)
    emergency_level = st.select_slider("Emergency Level", ["Moderate", "High", "Critical"], value="High")
    st.divider()
    st.subheader("📱 SMS Alerts")
    enable_sms = st.checkbox(f"Text results to {user['phone']}", value=True)
    if not is_sms_configured(st):
        st.caption("⚠️ Twilio not configured — SMS won't actually send until it is.")
    st.divider()
    run_search = st.button("🚑 Find Blood Now", use_container_width=True, type="primary")


def notify(message: str):
    """Send a real SMS via Twilio and surface a status message honestly."""
    if not enable_sms:
        return
    outcome = send_sms(st, user["phone"], message)
    if outcome["status"] == "sent":
        st.success(f"📤 Real SMS sent to {user['phone']} (Twilio SID {outcome['sid']}).")
    elif outcome["status"] == "not_configured":
        st.warning(f"📵 SMS not sent — {outcome['detail']}")
    else:
        st.warning(f"📵 SMS failed: {outcome['detail']}")


def run_pipeline(blood_group, city, address, units_required, emergency_level):
    lat, lon, source = resolve_location(city=city, address=address)
    if lat is None:
        st.error("Couldn't resolve that location. Try selecting a city instead.")
        return

    user_address = reverse_geocode(lat, lon) or (address or city or f"{lat:.4f}, {lon:.4f}")

    results = search_blood_banks(banks_df, inventory_df, blood_group, units_required, lat, lon)
    best = recommend_best(results, emergency_level=emergency_level)
    st.session_state.last_result = {
        "blood_group": blood_group, "city": city or address, "units_required": units_required,
        "emergency_level": emergency_level, "results": results, "best": best,
        "lat": lat, "lon": lon, "source": source, "user_address": user_address,
    }


if run_search:
    run_pipeline(blood_group, city, address, units_required, emergency_level)

# --------------------------------------------------------------------------
# Floating AI chatbot — a round logo button pinned to the corner, not an
# inline bar. Clicking it opens a small chat panel via st.popover.
# --------------------------------------------------------------------------
with st.popover("🩸🤖", use_container_width=False):
    st.markdown('<div class="chat-fab-title">AI Blood Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-fab-sub">Ask in plain English — I\'ll fill the form for you.</div>', unsafe_allow_html=True)

    for role, text in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(text)

    chat_input = st.chat_input("e.g. \"Need 2 units O+ urgently in Tirupati\"")
    if chat_input:
        st.session_state.chat_history.append(("user", chat_input))

        parsed = parse_request(st, chat_input, known_cities)
        intro = chatbot_reply_intro(parsed)
        st.session_state.chat_history.append(("assistant", intro))

        if not parsed.get("blood_group") or not parsed.get("city"):
            clarify = ("I couldn't catch the blood group and/or city clearly — could you "
                       "use the sidebar form, or rephrase like: 'Need 2 units B+ in Guntur, critical'?")
            st.session_state.chat_history.append(("assistant", clarify))
        else:
            run_pipeline(
                parsed["blood_group"], parsed["city"], None,
                parsed.get("units_required", 1), parsed.get("emergency_level", "High"),
            )
            confirm = f"Done — check the results panel below for {parsed['blood_group']} near {parsed['city']}."
            st.session_state.chat_history.append(("assistant", confirm))
        st.rerun()

# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
res = st.session_state.last_result
if res:
    st.divider()
    badge_class = f"badge-{res['emergency_level'].lower()}"
    st.markdown(
        f"### Results for **{res['blood_group']}** · {res['units_required']} unit(s) · "
        f"near **{res['city']}** · <span class='{badge_class}'>{res['emergency_level']}</span>",
        unsafe_allow_html=True,
    )

    best = res["best"]

    if best:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(
                f"""
                <div class="best-card">
                    <h3>✅ Best Match: {best['name']}</h3>
                    <p>📍 {best['address']}</p>
                    <p>📞 {best['phone']} &nbsp;|&nbsp; ⭐ {best['rating']}</p>
                    <p>🩸 <b>{best['units_available']} units</b> available &nbsp;|&nbsp;
                       📏 {best['distance_km']} km away &nbsp;|&nbsp;
                       ⏱️ ETA {best['eta_minutes']} min ({best['transport_mode'].replace('_',' ')})</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            alts = top_alternatives(res["results"], exclude_id=best["bank_id"], n=3)
            if not alts.empty:
                st.markdown("#### Other nearby options")
                for _, row in alts.iterrows():
                    st.markdown(
                        f"""<div class="alt-card">
                        <b>{row['name']}</b> — {row['units_available']} units, {row['distance_km']} km away
                        <br>📞 {row['phone']} &nbsp;|&nbsp; ⭐ {row['rating']}
                        </div>""",
                        unsafe_allow_html=True,
                    )

        with col2:
            st.markdown("**🗺️ Your location vs. the blood bank**")
            map_df = pd.DataFrame([
                {"lat": res["lat"], "lon": res["lon"], "color": "#3B82F6", "size": 160},
                {"lat": best["latitude"], "lon": best["longitude"], "color": "#22C55E", "size": 160},
            ])
            st.map(map_df, latitude="lat", longitude="lon", color="color", size="size", zoom=10)
            st.markdown(
                f"""<div class="loc-card"><span class="loc-dot" style="background:#3B82F6;"></span>
                <b>Your location</b> ({res['source']})<br>{res['user_address']}</div>
                <div class="loc-card"><span class="loc-dot" style="background:#22C55E;"></span>
                <b>{best['name']}</b><br>{best['address']}</div>""",
                unsafe_allow_html=True,
            )

        notify(build_available_message(res["blood_group"], best))

    else:
        st.markdown(
            f"""
            <div class="warn-card">
                <h3>⚠️ No blood bank nearby currently has {res['blood_group']}
                in stock for {res['units_required']} unit(s).</h3>
                <p>Checking eligible donors and compatible alternatives below.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([2, 1])
        with col2:
            st.markdown("**🗺️ Your location**")
            map_df = pd.DataFrame([{"lat": res["lat"], "lon": res["lon"], "color": "#3B82F6", "size": 160}])
            st.map(map_df, latitude="lat", longitude="lon", color="color", size="size", zoom=10)
            st.markdown(
                f"""<div class="loc-card"><span class="loc-dot" style="background:#3B82F6;"></span>
                <b>Your location</b> ({res['source']})<br>{res['user_address']}</div>""",
                unsafe_allow_html=True,
            )

        with col1:
            alt_groups = get_alternative_groups(res["blood_group"])
            st.caption(f"Medically compatible alternative donor groups: {', '.join(alt_groups)}")

            donors = find_eligible_donors(donors_df, res["blood_group"], city=res["city"], limit=10)
            if not donors.empty:
                st.markdown("#### 🧑‍🤝‍🧑 Eligible donors found")
                st.dataframe(
                    donors[["name", "blood_group", "city", "last_donated", "phone"]],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.warning("No eligible donors found for this blood group right now.")
                donors = donors_df.iloc[0:0]

        notify(build_not_available_message(res["blood_group"], res["city"], donor_count=len(donors)))

st.divider()
st.caption(
    "Demo data: blood bank locations are real coordinates in Andhra Pradesh; "
    "inventory levels and donor contact numbers are synthetically generated for this demo "
    "and are not live medical data. SMS delivery is real (via Twilio) once credentials are configured."
)
