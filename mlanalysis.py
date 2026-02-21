"""
ml_analysis.py — Beside Her
ML layer for postpartum mood analysis.
Techniques: Confidence System → Severity Score → Rule-Based Flags
            → Linear Regression → Z-Score Anomaly → KMeans Clustering
            → Postpartum Phase Detection
"""

import numpy as np
from datetime import date, datetime
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans


# ─────────────────────────────────────────────
# DATA STRUCTURE (one entry per day)
# ─────────────────────────────────────────────
# entry = {
#     "user_id": "uuid",       # from Supabase auth
#     "date": "2026-02-21",    # ISO string
#     "mood": 3,               # 1-5
#     "anxiety": 4,            # 1-5
#     "energy": 2,             # 1-5
#     "sleep_quality": 3,      # 1-5  ← matches Supabase column name
#     "quick_only": 0,         # 0 or 1
#     "heart_rate": 88,        # optional (from VitalLens)
#     "hrv": 42,               # optional (from VitalLens)
#     "notes": ""              # optional free text
# }


# ─────────────────────────────────────────────
# STEP 1 — DATA CONFIDENCE SYSTEM
# Gatekeeper: decides how much ML to run
# ─────────────────────────────────────────────

def get_confidence_level(entries: list) -> dict:
    """
    Returns confidence level based on number of entries.
    Everything else in this file checks this first.
    """
    n = len(entries)

    if n < 3:
        return {
            "level": "getting_started",
            "label": "Getting Started",
            "run_ml": False,
            "run_regression": False,
            "run_clustering": False,
            "message": "Encourage daily check-ins to unlock personalised insights.",
            "entry_count": n
        }
    elif n < 7:
        return {
            "level": "early_patterns",
            "label": "Early Patterns",
            "run_ml": True,
            "run_regression": False,   # regression on <7 points is unreliable
            "run_clustering": False,   # KMeans needs 7+ points
            "message": "Early patterns emerging — more data will improve accuracy.",
            "entry_count": n
        }
    else:
        return {
            "level": "full_analysis",
            "label": "Full Analysis",
            "run_ml": True,
            "run_regression": True,
            "run_clustering": True,
            "message": "Full analysis active.",
            "entry_count": n
        }


# ─────────────────────────────────────────────
# STEP 2 — SEVERITY SCORE
# Composite 0-10 index of how much support she needs
# ─────────────────────────────────────────────

def calculate_severity_score(entries: list, trend_labels: dict = None, anomaly_days: int = 0) -> dict:
    """
    Weighted composite severity score.
    Mood and anxiety weighted highest (primary PPD indicators per EPDS).
    Trend penalties applied if regression has been run.
    """
    mood_avg    = np.mean([e["mood"]          for e in entries])
    anxiety_avg = np.mean([e["anxiety"]       for e in entries])
    energy_avg  = np.mean([e["energy"]        for e in entries])
    sleep_avg   = np.mean([e["sleep_quality"] for e in entries])

    # Base score — higher = worse
    base = (
        (5 - mood_avg)    * 1.2 +   # mood weighted highest
        anxiety_avg       * 0.8 +   # anxiety second
        (5 - energy_avg)  * 0.5 +   # energy third
        (5 - sleep_avg)   * 0.3     # sleep fourth
    )

    # Normalize to 0-10
    max_possible = (4 * 1.2) + (5 * 0.8) + (4 * 0.5) + (4 * 0.3)
    score = (base / max_possible) * 10

    # Trend penalties (only applied when regression has run)
    if trend_labels:
        if trend_labels.get("mood") == "worsening":
            score += 1.0
        if trend_labels.get("anxiety") == "worsening":
            score += 0.5

    # Anomaly day penalties
    score += anomaly_days * 0.3

    # Cap at 10
    score = min(round(score, 1), 10.0)

    # Build interpretability reasons
    reasons = []
    if mood_avg < 2.5:
        reasons.append(f"Her mood has averaged {mood_avg:.1f}/5 — significantly below normal")
    if anxiety_avg > 3.5:
        reasons.append(f"High anxiety on recent days (avg {anxiety_avg:.1f}/5)")
    if energy_avg < 2.5:
        reasons.append(f"Energy has been consistently low (avg {energy_avg:.1f}/5)")
    if sleep_avg < 2.5:
        reasons.append(f"Sleep quality has been poor (avg {sleep_avg:.1f}/5)")
    if trend_labels and trend_labels.get("mood") == "worsening":
        reasons.append("Mood has been declining steadily")
    if anomaly_days > 0:
        reasons.append(f"{anomaly_days} unusually difficult day(s) detected this week")

    return {
        "score": score,
        "mood_avg": round(mood_avg, 2),
        "anxiety_avg": round(anxiety_avg, 2),
        "energy_avg": round(energy_avg, 2),
        "sleep_avg": round(sleep_avg, 2),
        "reasons": reasons
    }


# ─────────────────────────────────────────────
# STEP 3 — RULE-BASED SAFETY FLAGS
# Deterministic clinical rules — no ML needed
# ─────────────────────────────────────────────

def detect_safety_flags(entries: list) -> dict:
    """
    Hardcoded clinical rules based on PPD diagnostic criteria.
    Returns active flags and a crisis override if detected.
    """
    flags = []

    moods    = [e["mood"]          for e in entries]
    anxietys = [e["anxiety"]       for e in entries]
    sleeps   = [e["sleep_quality"] for e in entries]

    mood_avg    = np.mean(moods)
    anxiety_avg = np.mean(anxietys)

    # persistent_low_mood — 3+ consecutive days mood <= 2
    for i in range(len(moods) - 2):
        if all(m <= 2 for m in moods[i:i+3]):
            flags.append("persistent_low_mood")
            break

    # high_anxiety — 3+ days anxiety >= 4
    high_anxiety_days = sum(1 for a in anxietys if a >= 4)
    if high_anxiety_days >= 3:
        flags.append("high_anxiety")

    # sleep_disruption — 3+ days sleep <= 2
    poor_sleep_days = sum(1 for s in sleeps if s <= 2)
    if poor_sleep_days >= 3:
        flags.append("sleep_disruption")

    # high_risk_combination — low mood AND high anxiety together
    if mood_avg <= 2.5 and anxiety_avg >= 3.5:
        flags.append("high_risk_combination")

    # silence_alert — last entry more than 2 days ago
    if entries:
        last_date = datetime.strptime(entries[-1]["date"], "%Y-%m-%d").date()
        days_since = (date.today() - last_date).days
        if days_since >= 2:
            flags.append("silence_alert")

    # crisis language detection in notes
    crisis_keywords = ["hopeless", "can't go on", "dont want to be here",
                       "don't want to be here", "end it", "no point"]
    crisis_detected = False
    for e in entries:
        notes = e.get("notes", "").lower()
        if any(kw in notes for kw in crisis_keywords):
            crisis_detected = True
            break

    return {
        "flags": list(set(flags)),   # deduplicate
        "crisis_override": crisis_detected,
        "flag_count": len(set(flags))
    }


# ─────────────────────────────────────────────
# STEP 4 — LINEAR REGRESSION (TREND DETECTION)
# Requires 7+ entries (checked by confidence system)
# ─────────────────────────────────────────────

def detect_trends(entries: list) -> dict:
    """
    Fits linear regression on mood, anxiety, energy over time.
    Uses actual date distances (not sequential index) so time gaps are respected.
    Returns slope and trend label for each feature.
    """
    first_date = datetime.strptime(entries[0]["date"], "%Y-%m-%d")
    days = np.array([
        (datetime.strptime(e["date"], "%Y-%m-%d") - first_date).days
        for e in entries
    ]).reshape(-1, 1)

    results = {}
    for feature in ["mood", "anxiety", "energy"]:
        values = np.array([e[feature] for e in entries])

        model = LinearRegression()
        model.fit(days, values)
        slope = round(model.coef_[0], 4)

        # Slope is now per day — thresholds adjusted accordingly
        if slope < -0.01:
            label = "worsening"
        elif slope > 0.01:
            label = "improving"
        else:
            label = "stable"

        results[feature] = {
            "slope": slope,
            "trend": label
        }

    if results["mood"]["trend"] == "worsening":
        results["declining_mood_flag"] = True

    return results


# ─────────────────────────────────────────────
# STEP 5 — Z-SCORE ANOMALY DETECTION
# Compares each day to her personal baseline
# ─────────────────────────────────────────────

def detect_anomalies(entries: list) -> dict:
    """
    Z-score anomaly detection on mood scores.
    Flags days 2+ standard deviations below her personal mean.
    Also checks vitals for masking detection if available.
    """
    moods = np.array([e["mood"] for e in entries])
    mean  = np.mean(moods)
    std   = np.std(moods)

    anomaly_days = []

    for i, e in enumerate(entries):
        if std == 0:
            z = 0
        else:
            z = (e["mood"] - mean) / std

        if z <= -2.0:
            anomaly_days.append({
                "date": e["date"],
                "mood": e["mood"],
                "z_score": round(z, 2)
            })

    # Masking detection — mood looks okay but vitals show stress
    masking_flags = []
    for e in entries:
        mood_z = (e["mood"] - mean) / std if std > 0 else 0
        hr = e.get("heart_rate")
        hrv = e.get("hrv")

        # If mood seems normal but heart rate is elevated or HRV is low
        if mood_z > -1.0 and hr and hr > 100:
            masking_flags.append({
                "date": e["date"],
                "reason": "Normal mood score but elevated heart rate detected"
            })
        if mood_z > -1.0 and hrv and hrv < 30:
            masking_flags.append({
                "date": e["date"],
                "reason": "Normal mood score but low HRV (physiological stress) detected"
            })

    return {
        "anomaly_days": anomaly_days,
        "anomaly_count": len(anomaly_days),
        "personal_mean": round(mean, 2),
        "personal_std": round(std, 2),
        "masking_flags": masking_flags
    }


# ─────────────────────────────────────────────
# STEP 6 — KMEANS CLUSTERING (DAY PATTERN RECOGNITION)
# Requires 7+ entries (checked by confidence system)
# ─────────────────────────────────────────────

def classify_day_patterns(entries: list) -> dict:
    """
    KMeans clustering on (mood - anxiety) score per day.
    Positive = better day, negative = harder day.
    Finds 3 natural clusters: good / moderate / hard.
    """
    scores = np.array([e["mood"] - e["anxiety"] for e in entries]).reshape(-1, 1)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(scores)

    # Sort cluster centers so we can label them reliably
    centers = sorted(enumerate(kmeans.cluster_centers_.flatten()), key=lambda x: x[1])
    # centers[0] = lowest score = hard days
    # centers[1] = middle = moderate days
    # centers[2] = highest score = good days
    label_map = {
        centers[0][0]: "hard",
        centers[1][0]: "moderate",
        centers[2][0]: "good"
    }

    labels = [label_map[c] for c in kmeans.labels_]

    count = {"good": 0, "moderate": 0, "hard": 0}
    for l in labels:
        count[l] += 1

    # Determine dominant pattern for the week
    dominant = max(count, key=count.get)
    if dominant == "good":
        week_summary = "This was predominantly a Good week"
    elif dominant == "moderate":
        week_summary = "This was predominantly a Moderate week"
    else:
        week_summary = "This was predominantly a Hard week"

    return {
        "day_labels": labels,
        "counts": count,
        "dominant_pattern": dominant,
        "week_summary": week_summary
    }


# ─────────────────────────────────────────────
# STEP 7 — POSTPARTUM PHASE DETECTION
# Adjusts all interpretations based on weeks since birth
# ─────────────────────────────────────────────

def get_postpartum_phase(baby_dob: str) -> dict:
    """
    Calculates weeks postpartum and returns phase context.
    baby_dob: ISO date string e.g. "2026-01-01"
    """
    dob  = datetime.strptime(baby_dob, "%Y-%m-%d").date()
    weeks = (date.today() - dob).days // 7

    if weeks <= 2:
        return {
            "weeks": weeks,
            "phase": "baby_blues",
            "label": "Baby Blues Phase",
            "escalation_modifier": 0,   # no escalation boost
            "guidance_tone": "reassurance",
            "context": "Symptoms in weeks 1-2 are common. Baby blues affect 80% of moms. Stay close — this often resolves naturally."
        }
    elif weeks <= 8:
        return {
            "weeks": weeks,
            "phase": "watch_closely",
            "label": "Watch Closely Phase",
            "escalation_modifier": 1,   # bump escalation level up by 1
            "guidance_tone": "gentle_flag",
            "context": f"Symptoms persisting past 2 weeks (now week {weeks}) warrant closer attention. Gently encourage a professional support conversation."
        }
    else:
        return {
            "weeks": weeks,
            "phase": "ppd_risk",
            "label": "PPD Risk Phase",
            "escalation_modifier": 2,   # significant escalation boost
            "guidance_tone": "action_oriented",
            "context": f"Symptoms at week {weeks} are a serious concern. This is beyond baby blues. Professional support is strongly recommended."
        }


# ─────────────────────────────────────────────
# MASTER FUNCTION — run_full_analysis()
# Orchestrates all 7 techniques in correct order
# ─────────────────────────────────────────────

def run_full_analysis(entries: list, baby_dob: str) -> dict:
    """
    Main entry point. Pass in all entries and baby's DOB.
    Returns a complete analysis dict ready to inject into Gemini prompt.
    """

    # 1. Confidence check first — gates everything
    confidence = get_confidence_level(entries)

    if not confidence["run_ml"]:
        return {
            "confidence": confidence,
            "message": confidence["message"],
            "ready_for_ml": False
        }

    # 2. Severity score (basic stats — always run if run_ml is True)
    trend_labels = None
    anomaly_count = 0

    # 3. Trends (only if enough data)
    trends = None
    if confidence["run_regression"]:
        trends = detect_trends(entries)
        trend_labels = {k: v["trend"] for k, v in trends.items() if k != "declining_mood_flag"}

    # 4. Anomaly detection
    anomalies = detect_anomalies(entries)
    anomaly_count = anomalies["anomaly_count"]

    # 5. Severity score (now has trend + anomaly context)
    severity = calculate_severity_score(entries, trend_labels, anomaly_count)

    # 6. Safety flags
    flags = detect_safety_flags(entries)

    # 7. Clustering (only if enough data)
    patterns = None
    if confidence["run_clustering"]:
        patterns = classify_day_patterns(entries)

    # 8. Postpartum phase
    phase = get_postpartum_phase(baby_dob)

    # 9. Escalation level (crisis override takes priority)
    if flags["crisis_override"]:
        escalation = "red"
    else:
        base_score = severity["score"]
        base_score += phase["escalation_modifier"]  # phase adjustment

        if base_score >= 10 or flags["flag_count"] >= 4:
            escalation = "red"
        elif base_score >= 7 or flags["flag_count"] >= 2:
            escalation = "orange"
        elif base_score >= 5 or flags["flag_count"] >= 1:
            escalation = "yellow"
        else:
            escalation = "green"

    return {
        "confidence": confidence,
        "severity": severity,
        "trends": trends,
        "anomalies": anomalies,
        "flags": flags,
        "patterns": patterns,
        "phase": phase,
        "escalation": escalation,
        "ready_for_ml": True
    }


# ─────────────────────────────────────────────
# QUICK TEST — remove before production
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import date, timedelta

    today = date.today()

    STORIES = [
        {
            "name": "Sarah",
            "baby_dob": (today - timedelta(weeks=2)).strftime("%Y-%m-%d"),
            "description": "Week 2 — Baby Blues, Green/Yellow",
            "data": [
                (13, 4, 2, 3, 3), (12, 3, 3, 3, 3), (11, 4, 2, 3, 4),
                (10, 3, 3, 2, 3), (9,  3, 2, 3, 3), (8,  4, 2, 3, 3),
                (7,  3, 3, 2, 2), (6,  3, 2, 3, 3), (5,  4, 2, 3, 3),
                (4,  3, 3, 2, 3), (3,  3, 2, 3, 3), (2,  4, 2, 3, 3),
                (1,  3, 3, 2, 3),
            ]
        },
        {
            "name": "Maya",
            "baby_dob": (today - timedelta(weeks=6)).strftime("%Y-%m-%d"),
            "description": "Week 6 — Persisting symptoms, Orange",
            "data": [
                (40, 3, 3, 3, 3), (38, 3, 3, 2, 3), (35, 3, 3, 2, 2),
                (32, 2, 3, 2, 2), (30, 2, 4, 2, 2), (27, 2, 4, 1, 2),
                (25, 2, 4, 1, 2), (22, 1, 4, 1, 1), (20, 2, 4, 1, 2),
                (18, 1, 5, 1, 1), (15, 2, 4, 1, 2), (12, 1, 5, 1, 1),
                (10, 2, 4, 1, 2), (5,  1, 5, 1, 1), (4,  2, 4, 1, 2),
                (3,  1, 5, 1, 1), (2,  2, 4, 2, 2), (1,  1, 4, 1, 1),
            ]
        },
        {
            "name": "Priya",
            "baby_dob": (today - timedelta(weeks=10)).strftime("%Y-%m-%d"),
            "description": "Week 10 — PPD Risk, Red",
            "data": [
                (45, 3, 3, 3, 3), (43, 3, 3, 2, 3), (40, 2, 3, 2, 3),
                (38, 2, 4, 2, 2), (35, 2, 4, 1, 2), (32, 1, 4, 1, 1),
                (30, 2, 4, 1, 2), (27, 1, 5, 1, 1), (25, 1, 5, 1, 1),
                (22, 2, 4, 1, 2), (20, 1, 5, 1, 1), (18, 1, 4, 1, 1),
                (15, 1, 5, 1, 1), (12, 2, 4, 1, 2), (10, 1, 5, 1, 1),
                (8,  1, 4, 1, 1), (3,  1, 5, 1, 1), (2,  2, 4, 1, 2),
                (1,  1, 5, 1, 1),
            ]
        }
    ]

    for story in STORIES:
        # Convert seed tuples into entry dicts matching Supabase structure
        entries = []
        for (days_ago, mood, anxiety, energy, sleep_quality) in story["data"]:
            entries.append({
                "date":          (today - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "mood":          mood,
                "anxiety":       anxiety,
                "energy":        energy,
                "sleep_quality": sleep_quality,
                "notes":         ""
            })

        result = run_full_analysis(entries, baby_dob=story["baby_dob"])

        print(f"=== {story['name'].upper()} — {story['description']} ===")
        print(f"Confidence:  {result['confidence']['label']}")
        print(f"Escalation:  {result['escalation'].upper()}")
        print(f"Severity:    {result['severity']['score']}/10")
        print(f"Phase:       {result['phase']['label']} (Week {result['phase']['weeks']})")
        print(f"Flags:       {result['flags']['flags']}")
        print(f"Anomalies:   {result['anomalies']['anomaly_count']} days")
        if result["trends"]:
            print(f"Mood trend:  {result['trends']['mood']['trend']} (slope {result['trends']['mood']['slope']})")
        print(f"Reasons:")
        for r in result['severity']['reasons']:
            print(f"  - {r}")
        if result["patterns"]:
            print(f"Week pattern: {result['patterns']['week_summary']}")
        print()