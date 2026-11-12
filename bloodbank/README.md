# 🩸 Blood Bank Availability Agent

An AI-powered assistant that helps people find the required blood quickly
during emergencies — searches connected blood banks in real time, recommends
the nearest/best option, matches eligible donors when stock is short, shows
your location against the blood bank's on a map, and sends a **real SMS**
to the phone number you log in with.

Built around four cooperating agents (see `agents/`), plus a login gate and
a floating AI chatbot widget:

| Agent | File | Role |
|---|---|---|
| Search Agent | `agents/search_agent.py` | Checks blood availability across connected blood banks |
| Recommendation Agent | `agents/recommendation_agent.py` | Picks the nearest/best fulfillable option |
| Donor Matching Agent | `agents/donor_agent.py` | Finds eligible donors when stock is short |
| Notification Agent | `agents/notification_agent.py` | Sends a **real SMS** via Twilio to the logged-in phone number |
| Chatbot Agent | `agents/chatbot_agent.py` | Parses free-text requests (Gemini, with a rule-based fallback) |

## What's new in this version

- **Login gate** — the app now opens on a login screen that captures the
  user's name and phone number. That phone number is used for every SMS
  sent during the session; there's no separate "enter your number" field
  later.
- **Real SMS, not simulated** — `agents/notification_agent.py` calls the
  Twilio REST API directly. If Twilio credentials aren't configured, the
  app tells you plainly that SMS is "not configured" instead of showing a
  message that looks like a text went out.
- **Dual-location map** — after a search, the results map plots **your
  location** (blue) and the **recommended blood bank's location** (green)
  together, each labeled with its address underneath.
- **Floating AI chatbot** — instead of an inline chat bar, there's a round
  🩸🤖 logo button pinned to the bottom-right corner of the screen. Clicking
  it opens a small chat panel where you can type a request in plain
  English (e.g. *"Need 2 units O+ urgently in Tirupati"*), same as before,
  just relocated out of the main flow.

## Project structure

```
bloodbank/
├── app.py                        # Streamlit entry point (login + main app)
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   ├── config.toml               # theme
│   └── secrets.toml.example      # copy -> secrets.toml, fill in keys
├── agents/                       # the four AI agents + chatbot
├── utils/
│   └── geo.py                    # distance, location resolution, reverse geocoding
└── data/
    ├── blood_banks.csv           # 100 blood banks (real AP coordinates)
    ├── blood_inventory.csv       # per-bank, per-group stock (demo data)
    └── donors.csv                # cleaned donor list (demo phone numbers)
```

> **Note on data:** `blood_banks.csv` uses real coordinates supplied in the
> source dataset. `blood_inventory.csv` (live stock levels) and the phone
> numbers in `donors.csv` are **synthetically generated for this demo** —
> the original files had no inventory or donor-contact columns.

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

- Without a **Gemini** key, the chatbot uses a rule-based parser instead of
  the LLM-based one — it still works, just less forgiving of phrasing.
- Without **Twilio** keys, no SMS is sent — the app will say so clearly
  after each search rather than faking a "sent" message.

### Enabling real SMS (required for actual delivery)

1. Create a free [Twilio](https://www.twilio.com/try-twilio) account and
   buy/verify a "from" number capable of sending SMS.
2. Fill in `.streamlit/secrets.toml`:

   ```toml
   [twilio]
   account_sid = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   auth_token  = "your_auth_token"
   from_number = "+1XXXXXXXXXX"
   ```

   (Environment variables `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` /
   `TWILIO_FROM_NUMBER` also work, e.g. for a hosted deployment.)
3. On a Twilio **trial** account, you can only text numbers you've
   verified in the Twilio console — upgrade the account to text arbitrary
   numbers.
4. Log in to the app with the phone number you want alerts sent to. Every
   search result — found or not found — will now trigger a real SMS to
   that number.

```toml
[gemini]
api_key = "YOUR_GEMINI_KEY"
```

## Push to GitHub

```bash
cd bloodbank
git init
git add .
git commit -m "Blood Bank Availability Agent"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`secrets.toml` is git-ignored on purpose — only `secrets.toml.example` is
committed, so no keys ever leak into the repo.

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repo (see above).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Pick your repo/branch, set **Main file path** to `app.py`.
4. In **Advanced settings → Secrets**, paste the contents of
   `secrets.toml.example` with your real Gemini/Twilio keys filled in.
5. Click **Deploy**. The app installs `requirements.txt` automatically.

## How it works

1. The user **logs in** with their name and phone number — this phone
   number is what all SMS alerts go to for the rest of the session.
2. They ask in the **floating AI chatbot** (bottom-right logo) or fill the
   sidebar form.
3. The **Search Agent** checks stock for that blood group across all
   connected blood banks and computes distance from the user's location.
4. The **Recommendation Agent** ranks fulfillable options by distance and
   rating, and estimates travel time by ambulance/hospital vehicle.
5. The results map plots the **user's location** and the **recommended
   blood bank's location** together, with addresses underneath.
6. If nothing nearby has stock, the **Donor Matching Agent** looks up
   eligible donors (≥6 months since their last donation) for that blood
   group and city.
7. The **Notification Agent** sends a real SMS via Twilio to the phone
   number captured at login.
