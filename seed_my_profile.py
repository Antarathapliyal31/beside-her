from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ── PASTE YOUR USER ID HERE ──────────────────────────
# Find it in Supabase Dashboard → Auth → Users
# Or check mom_profile table after signing up
<<<<<<< HEAD
USER_ID = "2158f347-11c0-479d-beeb-b34d77b0240b"
=======
USER_ID = "ebeef525-335f-4b8a-bbe5-53e495128fe1"
>>>>>>> 117f75927b4fc1bc4131b583484f53ed6e01ded3

# ── Pick a story ─────────────────────────────────────
# Maya's data — 40 days, worsening pattern
today = datetime.today()
data = [
    (40, 3, 3, 3, 3), (38, 3, 3, 2, 3), (35, 3, 3, 2, 2),
    (32, 2, 3, 2, 2), (30, 2, 4, 2, 2), (27, 2, 4, 1, 2),
    (25, 2, 4, 1, 2), (22, 1, 4, 1, 1), (20, 2, 4, 1, 2),
    (18, 1, 5, 1, 1), (15, 2, 4, 1, 2), (12, 1, 5, 1, 1),
    (10, 2, 4, 1, 2), (5,  1, 5, 1, 1), (4,  2, 4, 1, 2),
    (3,  1, 5, 1, 1), (2,  2, 4, 2, 2), (1,  1, 4, 1, 1),
]

# ── Clear old checkins for this user ─────────────────
supabase.table("checkins").delete().eq("user_id", USER_ID).execute()
print("🗑️  Cleared old check-ins")

# ── Insert fake data ─────────────────────────────────
rows = []
for (days_ago, mood, anxiety, energy, sleep) in data:
    rows.append({
        "user_id":       USER_ID,
        "date":          (today - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
        "mood":          mood,
        "anxiety":       anxiety,
        "energy":        energy,
        "sleep_quality": sleep,
        "quick_only":    0,
        "notes":         ""
    })

supabase.table("checkins").insert(rows).execute()
print(f"✅ Seeded {len(rows)} check-ins for user {USER_ID[:8]}...")