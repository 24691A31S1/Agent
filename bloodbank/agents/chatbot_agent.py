"""Chatbot Agent: natural-language front door to the pipeline. Extracts
blood group, city, units required, and emergency level from a free-text
message. Uses Google Gemini if an API key is configured (richer, more
forgiving parsing); otherwise falls back to a deterministic rule-based
parser so the app never breaks without an API key.
"""
import re

BLOOD_GROUP_PATTERN = re.compile(
    r"\b(AB|A|B|O)\s?(\+|\-|positive|negative|pos|neg)", re.IGNORECASE
)
UNITS_PATTERN = re.compile(r"(\d+)\s*(unit|units|bottle|bottles|bag|bags)?", re.IGNORECASE)
EMERGENCY_WORDS = {
    "critical": ["critical", "urgent", "immediately", "emergency", "asap", "dying", "surgery now"],
    "high": ["high", "soon", "today", "quick", "fast"],
    "moderate": ["moderate", "tomorrow", "planned", "scheduled"],
}


def _normalize_blood_group(letters, sign):
    letters = letters.upper()
    sign = sign.lower()
    if sign in ("+", "positive", "pos"):
        return f"{letters}+"
    return f"{letters}-"


def rule_based_parse(message, known_cities):
    text = message.strip()
    result = {"blood_group": None, "city": None, "units_required": 1, "emergency_level": "High"}

    bg_match = BLOOD_GROUP_PATTERN.search(text)
    if bg_match:
        result["blood_group"] = _normalize_blood_group(bg_match.group(1), bg_match.group(2))

    for city in known_cities:
        if city.lower() in text.lower():
            result["city"] = city
            break

    units_match = re.search(r"(\d+)\s*(unit|units|bottle|bottles|bag|bags)", text, re.IGNORECASE)
    if units_match:
        result["units_required"] = int(units_match.group(1))

    lowered = text.lower()
    for level, words in EMERGENCY_WORDS.items():
        if any(w in lowered for w in words):
            result["emergency_level"] = level.capitalize()
            break

    return result


def gemini_parse(st, message, known_cities):
    """Try parsing with Gemini for a more natural conversational experience.
    Returns None if no API key is configured or the call fails, so callers
    should fall back to rule_based_parse."""
    try:
        api_key = st.secrets.get("gemini", {}).get("api_key")
    except Exception:
        api_key = None

    if not api_key:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""Extract structured fields from this blood request message.
Known cities: {', '.join(known_cities)}
Message: "{message}"

Reply ONLY with compact JSON, no markdown fences, in this exact shape:
{{"blood_group": "A+/A-/B+/B-/AB+/AB-/O+/O- or null",
  "city": "one of the known cities or null",
  "units_required": integer (default 1),
  "emergency_level": "Critical/High/Moderate"}}"""

        response = model.generate_content(prompt)
        import json
        cleaned = response.text.strip().strip("`").replace("json\n", "").strip()
        data = json.loads(cleaned)
        return {
            "blood_group": data.get("blood_group"),
            "city": data.get("city"),
            "units_required": int(data.get("units_required") or 1),
            "emergency_level": data.get("emergency_level") or "High",
        }
    except Exception:
        return None


def parse_request(st, message, known_cities):
    """Main entry point: try Gemini, fall back to rules."""
    parsed = gemini_parse(st, message, known_cities)
    if parsed is None:
        parsed = rule_based_parse(message, known_cities)
    return parsed


def chatbot_reply_intro(parsed):
    bg = parsed.get("blood_group") or "your requested blood group"
    city = parsed.get("city") or "your area"
    units = parsed.get("units_required", 1)
    return (
        f"Got it — searching for **{units} unit(s) of {bg}** near **{city}**. "
        f"Emergency level: **{parsed.get('emergency_level', 'High')}**. One moment..."
    )
