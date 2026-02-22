from flask import Flask, render_template, request, jsonify, session
from supabase import create_client
from dotenv import load_dotenv
import os
import json
import secrets
from datetime import datetime, date

from google import genai
from mlanalysis import run_full_analysis as run_analysis

load_dotenv()

gemini = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={"api_version": "v1"}
)

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

@app.route("/mom/history")
def mom_history():
    return render_template("mom_history.html")

@app.route("/partner")
def partner():
    return render_template("partner_dashboard.html")

@app.route("/chat")
def chat():
    return render_template("partner_chat.html")

@app.route("/report")
def report():
    return render_template("mom_history.html")

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
    mom_id   = get_mom_id()
    baby_dob = session.get("baby_dob")

    if not mom_id:
        return jsonify({"ready": False, "message": "Not logged in"})

    rows = supabase.table("checkins")\
        .select("*")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(7)\
        .execute().data

    obs = supabase.table("observations")\
        .select("*")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(5)\
        .execute().data

    analysis = run_analysis(rows, baby_dob)

    # ── Normalize run_full_analysis() output ──────────────
    if analysis.get("ready_for_ml"):
        sv = analysis.get("severity", {})
        tr = analysis.get("trends") or {}
        fl = analysis.get("flags") or {}
        pt = analysis.get("patterns") or {}
        ph = analysis.get("phase") or {}

        analysis["ready"]    = True
        analysis["level"]    = analysis.get("escalation", "green")
        analysis["severity"] = sv.get("score", 0) if isinstance(sv, dict) else sv

        analysis["stats"] = {
            "mood":    {"avg": sv.get("mood_avg", 0)},
            "anxiety": {"avg": sv.get("anxiety_avg", 0)},
            "energy":  {"avg": sv.get("energy_avg", 0)},
            "sleep":   {"avg": sv.get("sleep_avg", 0)},
        }

        analysis["trends"] = {
            "mood_trend":    tr.get("mood", {}).get("trend", "stable") if isinstance(tr.get("mood"), dict) else "stable",
            "anxiety_trend": tr.get("anxiety", {}).get("trend", "stable") if isinstance(tr.get("anxiety"), dict) else "stable",
            "energy_trend":  tr.get("energy", {}).get("trend", "stable") if isinstance(tr.get("energy"), dict) else "stable",
        }

        analysis["flags"] = [
            {"message": f, "level": "warn"}
            for f in fl.get("flags", [])
        ]
        if fl.get("crisis_override"):
            analysis["flags"].append({"message": "Crisis language detected", "level": "urgent"})

        analysis["clusters"]  = {"dominant": pt.get("dominant_pattern", "mixed")}
        analysis["reasons"]   = sv.get("reasons", []) if isinstance(sv, dict) else []
        analysis["weeks"]     = ph.get("weeks", 0)
        analysis["phase"]     = ph.get("phase", "unknown")
    else:
        analysis["ready"] = False

    if not analysis["ready"]:
        return jsonify({
            "ready":      False,
            "confidence": analysis.get("confidence", {}),
            "message":    "Not enough data yet — encourage daily check-ins"
        })

    obs_text = ""
    if obs:
        lines = []
        for o in obs:
            signals = o.get("signals", "[]")
            try:
                signals = ", ".join(json.loads(signals))
            except:
                pass
            lines.append(
                f"- {o['date']}: {signals}"
                f"{' — ' + o['note'] if o.get('note') else ''}"
            )
        obs_text = "Partner also observed:\n" + "\n".join(lines)

    phase_context = {
        "baby_blues":    "Week 1-2. Baby blues are normal. Normalize feelings but stay close.",
        "watch_closely": "Past week 2. Symptoms persisting this long need attention. Gently flag professional support.",
        "ppd_risk":      "Week 9+. Persistent symptoms at this stage are serious. Professional support is urgent.",
        "unknown":       "Postpartum stage unknown."
    }.get(analysis["phase"], "")

    prompt = f"""
You are a postpartum support guide writing to a partner.
Be warm, specific, and actionable. Never generic.
Pronouns / audience rules (STRICT):
- Address the partner as "you".
- Refer to the mom as "she/her" or "your partner".
- NEVER address the mom directly as "you" (no "you're feeling...", no "you need...").
- The only place "you" can refer to the mom is inside the "ready_to_send" text message (because that message is from partner to mom).

Be warm, specific, and actionable. Never generic.
Never diagnose. Don't say "she has PPD". Say "she may be having a harder time".

ML ANALYSIS:
- Severity: {analysis['severity']}/10
- Escalation: {analysis['level'].upper()}
- Mood avg: {analysis['stats']['mood']['avg']}/5 — {analysis['trends']['mood_trend']}
- Anxiety avg: {analysis['stats']['anxiety']['avg']}/5 — {analysis['trends']['anxiety_trend']}
- Energy avg: {analysis['stats']['energy']['avg']}/5
- Sleep avg: {analysis['stats']['sleep']['avg']}/5
- Pattern: mostly {analysis['clusters']['dominant']} days
- Weeks postpartum: {analysis['weeks']}
- Phase: {phase_context}
- Flags: {', '.join([f['message'] for f in analysis['flags']]) or 'none'}
- Why score is high: {'; '.join(analysis['reasons']) or 'n/a'}

{obs_text}

Return ONLY a valid JSON object, no markdown, no explanation:
{{
  "action_2min": "One specific 2-minute action right now",
  "action_15min": "One specific 15-minute action today",
  "action_60min": "One specific 60-minute action today",
  "avoid": "One specific thing NOT to say or do and exactly why",
  "conversation_starter": "One gentle open question to ask her",
  "ready_to_send": "Exact text message they can copy and send to her",
  "summary": "Two sentences about how she is doing this week"
}}

Rules:
- If energy avg < 3, action_15min must involve food or preparing a meal
- If anxiety avg > 3, action_60min must involve calm or rest
- Never write generic advice like 'be supportive'
- Base everything on her actual ML data above
"""

    try:
        response = gemini.models.generate_content(model="gemini-2.5-flash-lite",contents=prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        playbook = json.loads(text.strip())

        return jsonify({
            "ready":    True,
            "playbook": playbook,
            "analysis": {
                "severity":   analysis["severity"],
                "level":      analysis["level"],
                "trends":     analysis["trends"],
                "clusters":   analysis["clusters"],
                "flags":      analysis["flags"],
                "reasons":    analysis["reasons"],
                "confidence": analysis["confidence"],
                "weeks":      analysis["weeks"],
                "phase":      analysis["phase"],
                "stats":      analysis["stats"],
            }
        })

    except Exception as e:
        return jsonify({"ready": False, "message": f"AI error: {str(e)}"})


@app.route("/api/chat", methods=["POST"])
def chat_api():
    mom_id   = get_mom_id()
    baby_dob = session.get("baby_dob")
    message  = request.json.get("message", "")

    if not mom_id or not message:
        return jsonify({"response": "Please log in first."})

    rows = supabase.table("checkins")\
        .select("*")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(45)\
        .execute().data

    analysis = run_analysis(rows, baby_dob)

    # ── Normalize output ──
    if analysis.get("ready_for_ml"):
        sv = analysis.get("severity", {})
        ph = analysis.get("phase") or {}
        analysis["ready"]    = True
        analysis["level"]    = analysis.get("escalation", "green")
        analysis["severity"] = sv.get("score", 0) if isinstance(sv, dict) else sv
        analysis["stats"]    = {
            "mood":    {"avg": sv.get("mood_avg", 0)},
            "anxiety": {"avg": sv.get("anxiety_avg", 0)},
        }
        analysis["weeks"] = ph.get("weeks", 0)
        analysis["phase"] = ph.get("phase", "unknown")
        analysis["trends"] = {
            "mood_trend": (analysis.get("trends") or {}).get("mood", {}).get("trend", "stable")
        }
    else:
        analysis["ready"] = False

    if analysis["ready"]:
        context = (
            f"Severity: {analysis['severity']}/10, Level: {analysis['level']}, "
            f"Mood: {analysis['stats']['mood']['avg']}/5 ({analysis['trends']['mood_trend']}), "
            f"Anxiety: {analysis['stats']['anxiety']['avg']}/5, "
            f"Weeks postpartum: {analysis['weeks']}, Phase: {analysis['phase']}"
        )
    else:
        context = "Less than 3 check-ins — limited data available."

    prompt = f"""
You are a warm postpartum support guide helping a partner.
Her current data: {context}
Partner asks: {message}
Answer warmly and specifically. Under 150 words.
If severity is high (7+), gently mention professional support.
Never give generic advice.
"""
    try:
        response = gemini.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        return jsonify({"response": response.text.strip()})
    except Exception as e:
        return jsonify({"response": f"AI error: {str(e)}"})


@app.route("/api/weekly")
def get_weekly():
    mom_id   = get_mom_id()
    baby_dob = session.get("baby_dob")

    if not mom_id:
        return jsonify({"ready": False})

    rows = supabase.table("checkins")\
        .select("*")\
        .eq("user_id", mom_id)\
        .order("date", desc=True)\
        .limit(7)\
        .execute().data

    
    analysis = run_analysis(rows, baby_dob)

    
    if analysis.get("ready_for_ml"):
        sv = analysis.get("severity", {})
        ph = analysis.get("phase") or {}
        pt = analysis.get("patterns") or {}
        analysis["ready"]    = True
        analysis["level"]    = analysis.get("escalation", "green")
        analysis["severity"] = sv.get("score", 0) if isinstance(sv, dict) else sv
        analysis["stats"]    = {
            "mood":    {"avg": sv.get("mood_avg", 0)},
            "anxiety": {"avg": sv.get("anxiety_avg", 0)},
            "energy":  {"avg": sv.get("energy_avg", 0)},
            "sleep":   {"avg": sv.get("sleep_avg", 0)},
        }
        analysis["clusters"] = {"dominant": pt.get("dominant_pattern", "mixed")}
        analysis["weeks"]    = ph.get("weeks", 0)
        analysis["phase"]    = ph.get("phase", "unknown")
        analysis["trends"]   = {"mood_trend": (analysis.get("trends") or {}).get("mood", {}).get("trend", "stable") if isinstance((analysis.get("trends") or {}).get("mood"), dict) else "stable"}
        analysis["flags"]    = [{"message": f, "level": "warn"} for f in (analysis.get("flags") or {}).get("flags", [])]
        analysis["trends"]   = {"mood_trend": (analysis.get("trends") or {}).get("mood", {}).get("trend", "stable")
}
    else:
        analysis["ready"] = False


    if not analysis["ready"]:
        return jsonify({"ready": False, "message": "Not enough data"})

    prompt = f"""
Write a weekly postpartum support report for a partner.
Severity: {analysis['severity']}/10, Level: {analysis['level']}
Mood: {analysis['stats']['mood']['avg']}/5 ({analysis['trends']['mood_trend']}),
Anxiety: {analysis['stats']['anxiety']['avg']}/5, Energy: {analysis['stats']['energy']['avg']}/5,
Sleep: {analysis['stats']['sleep']['avg']}/5, Pattern: {analysis['clusters']['dominant']} days,
Weeks postpartum: {analysis['weeks']},
Flags: {', '.join([f['message'] for f in analysis['flags']]) or 'none'}

Return ONLY valid JSON:
{{
  "week_summary": "3 sentences about her week",
  "biggest_challenge": "The main thing she struggled with",
  "what_worked": "Any positive signals",
  "next_week_focus": "One key focus for next week",
  "action_plan": ["action 1", "action 2", "action 3"],
  "professional_note": "Only if severity >= 6, else empty string"
}}
"""
    try:
        response = gemini.models.generate_content(model="gemini-2.5-flash-lite",contents=prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        report = json.loads(text.strip())
        return jsonify({"ready": True, "report": report,
                        "analysis": {"severity": analysis["severity"],
                                     "level": analysis["level"],
                                     "stats": analysis["stats"],
                                     "weeks": analysis["weeks"]}})
    except Exception as e:
        return jsonify({"ready": False, "message": str(e)})

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
            mom_prof = supabase.table("mom_profile")\
                .select("baby_dob")\
                .eq("id", partner.data[0]["linked_mom_id"])\
                .single().execute()
            session["baby_dob"] = mom_prof.data["baby_dob"] if mom_prof.data else None
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
    app.run(debug=True, host="0.0.0.0", port=5000)