from flask import Flask, render_template, request, jsonify, session
from supabase import create_client
from dotenv import load_dotenv
import os
import json
import secrets
from datetime import datetime, date

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "beside-her-secret-2026")

# ── Supabase client ────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Helper — gets the correct mom's ID ────────────────────
def get_mom_id():
    role = session.get("role")
    if role == "mom":
        return session.get("user_id")
    elif role == "partner":
        return session.get("mom_id")
    return None

# ── Pages ──────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/mom")
def mom():
    return render_template("mom_checkin.html")

@app.route("/partner")
def partner():
    return render_template("partner_dashboard.html")

@app.route("/chat")
def chat():
    return render_template("partner_chat.html")

@app.route("/report")
def report():
    return render_template("weekly_report.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

# ── Mom check-in APIs ──────────────────────────────────────

@app.route("/api/checkin", methods=["POST"])
def log_checkin():
    d = request.json
    mom_id = get_mom_id()

    if not mom_id:
        return jsonify({"error": "Not logged in"}), 401

    supabase.table("checkins").insert({
        "user_id":       mom_id,
        "date":          d.get("date"),
        "mood":          d.get("mood"),
        "anxiety":       d.get("anxiety"),
        "energy":        d.get("energy"),
        "sleep_quality": d.get("sleep_quality"),
        "notes":         d.get("notes", ""),
        "heart_rate":    d.get("heart_rate"),
        "hrv":           d.get("hrv"),
        "breathing_rate": d.get("breathing_rate"),
        "quick_only":    0
    }).execute()
    return jsonify({"success": True})

@app.route("/api/checkins")
def get_checkins():
    mom_id = get_mom_id()

    if not mom_id:
        return jsonify([])

    result = supabase.table("checkins")\
        .select("*")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(60)\
        .execute()
    return jsonify(result.data)

# ── Partner APIs ───────────────────────────────────────────

@app.route("/api/observation", methods=["POST"])
def log_observation():
    d = request.json
    mom_id = get_mom_id()

    if not mom_id:
        return jsonify({"error": "Not logged in"}), 401

    supabase.table("observations").insert({
        "user_id": mom_id,
        "date":    d.get("date"),
        "note":    d.get("note", ""),
        "signals": json.dumps(d.get("signals", []))
    }).execute()
    return jsonify({"success": True})

@app.route("/api/observations")
def get_observations():
    mom_id = get_mom_id()

    if not mom_id:
        return jsonify([])

    result = supabase.table("observations")\
        .select("*")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(14)\
        .execute()
    return jsonify(result.data)

# ── Privacy settings ───────────────────────────────────────

@app.route("/api/privacy", methods=["POST"])
def save_privacy():
    d = request.json
    mom_id = get_mom_id()

    supabase.table("privacy_settings").upsert({
        "id":            mom_id,
        "sharing_level": d.get("sharing_level", "full"),
        "share_weekly":  d.get("share_weekly", 1)
    }).execute()
    return jsonify({"success": True})

@app.route("/api/privacy")
def get_privacy():
    mom_id = get_mom_id()

    if not mom_id:
        return jsonify({"sharing_level": "full", "share_weekly": 1})

    result = supabase.table("privacy_settings")\
        .select("*")\
        .eq("id", mom_id)\
        .limit(1)\
        .execute()

    if result.data:
        return jsonify(result.data[0])
    return jsonify({"sharing_level": "full", "share_weekly": 1})

# ── Silence detection ──────────────────────────────────────

@app.route("/api/misseddays")
def missed_days():
    mom_id = get_mom_id()

    if not mom_id:
        return jsonify({"days_since_last": 0})

    result = supabase.table("checkins")\
        .select("date")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(1)\
        .execute()

    if not result.data:
        return jsonify({"days_since_last": 0, "last_date": None})

    last = datetime.strptime(
        result.data[0]["date"], "%Y-%m-%d"
    ).date()
    days_since = (date.today() - last).days

    return jsonify({
        "days_since_last": days_since,
        "last_date":       str(last)
    })

# ── Digest + Weekly + Chat (placeholders) ─────────────────

@app.route("/api/digest")
def get_digest():
    return jsonify({
        "ready":   False,
        "message": "ML layer coming soon"
    })

@app.route("/api/weekly")
def get_weekly():
    return jsonify({
        "ready":   False,
        "message": "Weekly report coming soon"
    })

@app.route("/api/chat", methods=["POST"])
def chat_api():
    return jsonify({
        "response": "AI chat coming soon"
    })

# ── Auth ───────────────────────────────────────────────────

@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    email    = d.get("email")
    password = d.get("password")
    role     = d.get("role")

    try:
        result = supabase.auth.sign_up({
            "email":    email,
            "password": password
        })

        user = result.user
        if not user:
            return jsonify({"error": "Signup failed — try again"})

        user_id = user.id

        if role == "mom":
            code = secrets.token_hex(4).upper()

            supabase.table("mom_profile").insert({
                "id":           user_id,
                "name":         d.get("name", ""),
                "baby_dob":     d.get("baby_dob"),
                "partner_code": code
            }).execute()

            session["user_id"]  = user_id
            session["role"]     = "mom"
            session["baby_dob"] = d.get("baby_dob")

            return jsonify({
                "success":      True,
                "redirect":     "/mom",
                "partner_code": code
            })

        else:
            partner_code = d.get("partner_code", "").upper()
            mom = supabase.table("mom_profile")\
                .select("*")\
                .eq("partner_code", partner_code)\
                .execute()

            if not mom.data:
                return jsonify({
                    "error": "Partner code not found. "
                             "Ask your partner to check their profile."
                })

            mom_id = mom.data[0]["id"]

            supabase.table("partner_profile").insert({
                "id":            user_id,
                "partner_code":  partner_code,
                "linked_mom_id": mom_id
            }).execute()

            session["user_id"] = user_id
            session["role"]    = "partner"
            session["mom_id"]  = mom_id

            return jsonify({
                "success":  True,
                "redirect": "/partner"
            })

    except Exception as ex:
        return jsonify({"error": str(ex)})


@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    try:
        result = supabase.auth.sign_in_with_password({
            "email":    d.get("email"),
            "password": d.get("password")
        })

        user = result.user
        if not user:
            return jsonify({"error": "Invalid email or password"})

        user_id = user.id

        mom = supabase.table("mom_profile")\
            .select("*").eq("id", user_id).execute()

        if mom.data:
            session["user_id"]  = user_id
            session["role"]     = "mom"
            session["baby_dob"] = mom.data[0]["baby_dob"]
            return jsonify({"success": True, "redirect": "/mom"})

        partner = supabase.table("partner_profile")\
            .select("*").eq("id", user_id).execute()

        if partner.data:
            session["user_id"] = user_id
            session["role"]    = "partner"
            session["mom_id"]  = partner.data[0]["linked_mom_id"]
            return jsonify({"success": True, "redirect": "/partner"})

        return jsonify({"error": "Profile not found"})

    except Exception as ex:
        return jsonify({"error": str(ex)})


@app.route("/api/logout")
def logout():
    session.clear()
    supabase.auth.sign_out()
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True)