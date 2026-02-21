from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

today = datetime.today()

# ── 3 Mom Stories ──────────────────────────────────────────

STORIES = [
    {
        "email":    "mom1@besideher.demo",
        "password": "demo1234",
        "name":     "Sarah",
        "baby_dob": (today - timedelta(weeks=2)).strftime("%Y-%m-%d"),
        "description": "Week 2 — Baby Blues, Green/Yellow",
        "data": [
            # (days_ago, mood, anxiety, energy, sleep)
            # Mild adjustment, mostly okay
            (13, 4, 2, 3, 3),
            (12, 3, 3, 3, 3),
            (11, 4, 2, 3, 4),
            (10, 3, 3, 2, 3),
            (9,  3, 2, 3, 3),
            (8,  4, 2, 3, 3),
            (7,  3, 3, 2, 2),
            (6,  3, 2, 3, 3),
            (5,  4, 2, 3, 3),
            (4,  3, 3, 2, 3),
            (3,  3, 2, 3, 3),
            (2,  4, 2, 3, 3),
            (1,  3, 3, 2, 3),
        ]
    },
    {
        "email":    "mom2@besideher.demo",
        "password": "demo1234",
        "name":     "Maya",
        "baby_dob": (today - timedelta(weeks=6)).strftime("%Y-%m-%d"),
        "description": "Week 6 — Persisting symptoms, Orange",
        "data": [
            # Started okay, now worsening
            (40, 3, 3, 3, 3),
            (38, 3, 3, 2, 3),
            (35, 3, 3, 2, 2),
            (32, 2, 3, 2, 2),
            (30, 2, 4, 2, 2),
            (27, 2, 4, 1, 2),
            (25, 2, 4, 1, 2),
            (22, 1, 4, 1, 1),
            (20, 2, 4, 1, 2),
            (18, 1, 5, 1, 1),
            (15, 2, 4, 1, 2),
            (12, 1, 5, 1, 1),
            (10, 2, 4, 1, 2),
            # Silence gap days 6-9
            (5,  1, 5, 1, 1),
            (4,  2, 4, 1, 2),
            (3,  1, 5, 1, 1),
            (2,  2, 4, 2, 2),
            (1,  1, 4, 1, 1),
        ]
    },
    {
        "email":    "mom3@besideher.demo",
        "password": "demo1234",
        "name":     "Priya",
        "baby_dob": (today - timedelta(weeks=10)).strftime("%Y-%m-%d"),
        "description": "Week 10 — PPD Risk, Red",
        "data": [
            # Long persistent decline — serious
            (45, 3, 3, 3, 3),
            (43, 3, 3, 2, 3),
            (40, 2, 3, 2, 3),
            (38, 2, 4, 2, 2),
            (35, 2, 4, 1, 2),
            (32, 1, 4, 1, 1),
            (30, 2, 4, 1, 2),
            (27, 1, 5, 1, 1),
            (25, 1, 5, 1, 1),
            (22, 2, 4, 1, 2),
            (20, 1, 5, 1, 1),
            (18, 1, 4, 1, 1),
            (15, 1, 5, 1, 1),
            (12, 2, 4, 1, 2),
            (10, 1, 5, 1, 1),
            (8,  1, 4, 1, 1),
            # Silence gap days 4-7
            (3,  1, 5, 1, 1),
            (2,  2, 4, 1, 2),
            (1,  1, 5, 1, 1),
        ]
    }
]

# ── Seed function ───────────────────────────────────────────

def seed():
    print("🌱 Starting seed...\n")

    for story in STORIES:
        print(f"Creating: {story['name']} — {story['description']}")

        # Step 1: Create auth user
        try:
            result = supabase.auth.sign_up({
                "email":    story["email"],
                "password": story["password"]
            })
            user_id = result.user.id
            print(f"   ✅ Auth user created: {user_id[:8]}...")

        except Exception as e:
            # User might already exist — try to find them
            print(f"   ⚠️  Auth signup failed: {e}")
            print(f"   Trying to find existing user...")

            # Get existing user from mom_profile by email pattern
            existing = supabase.table("mom_profile")\
                .select("id, name")\
                .eq("name", story["name"])\
                .execute()

            if existing.data:
                user_id = existing.data[0]["id"]
                print(f"   ✅ Found existing user: {user_id[:8]}...")
            else:
                print(f"   ❌ Skipping {story['name']} — could not create or find user")
                continue

        # Step 2: Create or update mom_profile
        import secrets
        partner_code = secrets.token_hex(4).upper()

        try:
            supabase.table("mom_profile").upsert({
                "id":           user_id,
                "name":         story["name"],
                "baby_dob":     story["baby_dob"],
                "partner_code": partner_code
            }).execute()
            print(f"   ✅ Profile created — partner code: {partner_code}")
        except Exception as e:
            print(f"   ⚠️  Profile error: {e}")

        # Step 3: Clear existing checkins for this user
        supabase.table("checkins")\
            .delete()\
            .eq("user_id", user_id)\
            .execute()

        # Step 4: Insert story data
        rows = []
        for (days_ago, mood, anxiety, energy, sleep) in story["data"]:
            date = (today - timedelta(days=days_ago))\
                   .strftime("%Y-%m-%d")
            rows.append({
                "user_id":       user_id,
                "date":          date,
                "mood":          mood,
                "anxiety":       anxiety,
                "energy":        energy,
                "sleep_quality": sleep,
                "quick_only":    0
            })

        supabase.table("checkins").insert(rows).execute()

        print(f"   ✅ Seeded {len(story['data'])} check-ins")
        print(f"   📅 Baby DOB: {story['baby_dob']}")
        print()

    print("=" * 45)
    print("✅ All 3 moms seeded successfully!")
    print()
    print("Demo accounts:")
    for s in STORIES:
        print(f"  {s['name']}: {s['email']} / {s['password']}")
    print()
    print("Expected ML results:")
    print("  Sarah (Week 2)  → 🟢 Green/Yellow — Baby Blues")
    print("  Maya  (Week 6)  → 🟠 Orange       — Watch Closely")
    print("  Priya (Week 10) → 🔴 Red           — PPD Risk")

if __name__ == "__main__":
    seed()