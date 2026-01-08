import os

# Load .env locally (safe in prod too; it will just do nothing if .env doesn't exist)
try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env in the current working directory
except Exception:
    pass

from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
from datetime import timedelta, datetime as _dt, date as _date
import pytz

from ai_ml import build_weekly_features, detect_anomalies

from ai_coach import build_coach_message

print("GOOGLE_APPLICATION_CREDENTIALS =", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

OMAHA_TZ = pytz.timezone("America/Chicago")


def _today_omaha():
    """Return today's date in Omaha (America/Chicago) time."""
    return _dt.now(OMAHA_TZ).date()

def _get_year_arg(default=2025) -> int:
    y = (request.args.get("year") or str(default)).strip()
    try:
        y = int(y)
    except Exception:
        y = default
    if y not in (2025, 2026):
        y = default
    return y

# Sheets helpers (expect: Date/Target/Exercise/Weight/Reps/Total -> mapped in sheets_client.py)
from sheets_client import get_rows, unique_exercises, unique_muscle_groups

app = Flask(__name__)

# Use absolute path for files written by the web worker (contact form CSV)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# Basic pages
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/more-about")
def more_about():
    return render_template("more-about.html")

@app.route("/resume")
def resume():
    return render_template("resume.html")

# -----------------------------
# Contact form (POST)
# -----------------------------
@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    subject = request.form.get("subject", "").strip()
    message = request.form.get("message", "").strip()

    csv_path = os.path.join(BASE_DIR, "submissions.csv")
    file_exists = os.path.isfile(csv_path)

    # Write a row; create header if the file didn't exist yet
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["Name", "Email", "Subject", "Message"])
        w.writerow([name, email, subject, message])

    # Back to contact section
    return redirect(url_for("home") + "#contact")

# -----------------------------
# Workout dashboard page
# -----------------------------
@app.route("/workout")
def workout():
    year = _get_year_arg(2025)

    try:
        exs = unique_exercises(year)
        groups = unique_muscle_groups(year)
    except Exception:
        exs, groups = [], []

    # ----- today's workout rows -----
    today_rows = []
    today = _today_omaha()
    today_date_label = today.strftime("%b %d, %Y")

    # selected year for charts
    year = _get_year_arg(2025)

    # year for "Today" panel (always current year if possible)
    today_year = today.year  # 2026 now, 2027 later

    try:
        # Prefer current year tab for today’s workout
        rows_today_year = [_ensure_row_normalized(dict(r)) for r in get_rows(today_year)]

        target_key = _date(2000, today.month, today.day)
        for r in rows_today_year:
            if r.get("_date_key") == target_key:
                today_rows.append(r)

    except Exception:
        today_rows = []

    # ----- reaction counts for today (for the fill effect) -----
    reaction_counts = {"great": 0, "push": 0, "lazy": 0, "rest": 0}
    reactions_csv = os.path.join(BASE_DIR, "workout_reactions.csv")

    if os.path.isfile(reactions_csv):
        with open(reactions_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("date") == today.isoformat():
                    t = (row.get("reaction_type") or "").strip()
                    if t in reaction_counts:
                        reaction_counts[t] += 1

    # convert counts to 0–100 "fill" percentages (no numbers shown to user)
    reaction_fill = {k: 0 for k in reaction_counts}
    max_count = max(reaction_counts.values()) if reaction_counts else 0
    if max_count > 0:
        for k, c in reaction_counts.items():
            if c > 0:
                # at least 25% bar for a non-zero vote
                reaction_fill[k] = 25 + int(75 * c / max_count)

    return render_template(
        "workout.html",
        year=year,
        year_options=[2025, 2026],
        exercises=exs,
        groups=groups,
        today_rows=today_rows,
        today_date_label=today_date_label,
        reaction_fill=reaction_fill,
    )

@app.route("/workout/react", methods=["POST"])
def workout_react():
    rtype = (request.form.get("reaction_type") or "").strip()
    if rtype not in ("great", "push", "lazy", "rest"):
        # Return a small error payload instead of redirect
        return jsonify({"ok": False, "error": "invalid_reaction"}), 400

    today = _today_omaha().isoformat()
    csv_path = os.path.join(BASE_DIR, "workout_reactions.csv")

    # --- 1) compute counts for today (before adding this vote) ---
    counts = {"great": 0, "push": 0, "lazy": 0, "rest": 0}
    if os.path.isfile(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("date") == today:
                    t = (row.get("reaction_type") or "").strip()
                    if t in counts:
                        counts[t] += 1

    # add this new vote
    counts[rtype] += 1

    # --- 2) append to CSV ---
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["date", "reaction_type"])
        w.writerow([today, rtype])

    # --- 3) compute new fill percentages 0–100 for each type ---
    reaction_fill = {k: 0 for k in counts}
    max_count = max(counts.values()) if counts else 0
    if max_count > 0:
        for k, c in counts.items():
            if c > 0:
                # at least 25% bar if chosen at all
                reaction_fill[k] = 25 + int(75 * c / max_count)

    return jsonify({"ok": True, "reaction_fill": reaction_fill})

@app.route("/workout/feedback", methods=["POST"])
def workout_feedback():
    msg = (request.form.get("message") or "").strip()
    if not msg:
        return redirect(url_for("workout"))

    today = _today_omaha().isoformat()
    csv_path = os.path.join(BASE_DIR, "workout_feedback.csv")
    file_exists = os.path.isfile(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["date", "message"])
        w.writerow([today, msg])

    return redirect(url_for("workout"))

# -----------------------------
# Helpers for workout APIs
# (Dates in sheet are MM/DD with no year.)
# I sort/group using an internal fake-year key created in sheets_client.py:
#   record["_date_key"] is a datetime.date(2000, mm, dd)
# Public labels remain "MM/DD".
# -----------------------------
def _norm(s):
    return (s or "").strip()

def _eq_ci(a, b):
    return _norm(a).lower() == _norm(b).lower()

def _coerce_float(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        s = _norm(x)
        return float(s) if s != "" else None
    except Exception:
        return None

def _parse_mmdd_label(mmdd):
    """
    Accepts '1/2' or '01/02' and returns:
      display 'MM/DD', internal _date_key as date(2000, MM, DD)
    """
    s = _norm(mmdd)
    if not s or "/" not in s:
        return "", None
    try:
        mm, dd = s.split("/", 1)
        mm_i = int(mm)
        dd_i = int(dd)
        disp = f"{mm_i:02d}/{dd_i:02d}"
        return disp, _date(2000, mm_i, dd_i)
    except Exception:
        return "", None

def _ensure_row_normalized(r):
    """
    Ensure each row has:
      - r['_date_key'] set (derive from r['date'] if needed)
      - r['date'] as zero-padded 'MM/DD'
      - numeric fields coerced to floats
    """
    # Date handling
    dk = r.get("_date_key")
    disp = _norm(r.get("date"))

    if not dk or not disp:
        disp2, dk2 = _parse_mmdd_label(disp)
        if dk2:
            r["_date_key"] = dk2
            r["date"] = disp2  # normalized MM/DD
        else:
            # leave missing; caller will skip
            r["_date_key"] = None
            r["date"] = disp or ""

    # Numerics
    for key in ("weight", "reps", "total"):
        r[key] = _coerce_float(r.get(key))

    # Texts
    for key in ("muscle_group", "exercise"):
        r[key] = _norm(r.get(key))

    return r

def _filter_rows(muscle=None, exercise=None, year: int = 2025):
    # Normalize incoming filters: treat "", "All" as no filter
    m = _norm(muscle)
    e = _norm(exercise)
    if m.lower() == "all": m = ""
    if e.lower() == "all": e = ""

    try:
        rows = [ _ensure_row_normalized(dict(r)) for r in get_rows(year) ]  # copy+normalize
    except Exception:
        rows = []

    if m:
        rows = [r for r in rows if _eq_ci(r.get("muscle_group"), m)]
    if e:
        rows = [r for r in rows if _eq_ci(r.get("exercise"), e)]
    # keep only rows with a valid internal date key
    rows = [r for r in rows if r.get("_date_key")]
    return rows

def _group_max_weight_by_date(rows):
    # Keep max weight per MM/DD; order by internal _date_key
    tmp = {}
    for r in rows:
        dk = r["_date_key"]
        # Prefer weight; if missing, try backfill from total/reps
        w = r.get("weight")
        if w is None:
            reps = r.get("reps")
            tot = r.get("total")
            if isinstance(tot, (int, float)) and isinstance(reps, (int, float)) and reps != 0:
                w = float(tot) / float(reps)
        if w is None:
            continue

        disp = r.get("date") or dk.strftime("%m/%d")
        if disp not in tmp or w > tmp[disp]["max"]:
            tmp[disp] = {"max": float(w), "_key": dk}
    items = sorted(tmp.items(), key=lambda kv: kv[1]["_key"])
    return [(disp, v["max"]) for disp, v in items]

def _sum_total_by_week(rows):
    # Monday-start week buckets using fake-year keys
    buckets = {}
    for r in rows:
        dk = r["_date_key"]
        tot = r.get("total")
        if not isinstance(tot, (int, float)):
            w = r.get("weight")
            reps = r.get("reps")
            if isinstance(w, (int, float)) and isinstance(reps, (int, float)):
                tot = float(w) * float(reps)
            else:
                tot = 0.0
        wk_start = dk - timedelta(days=dk.weekday())
        buckets[wk_start] = buckets.get(wk_start, 0.0) + float(tot)
    return [{"period": k.strftime("%m/%d"), "volume": float(v)}
            for k, v in sorted(buckets.items())]

def _sum_total_by_month(rows):
    buckets = {}
    for r in rows:
        dk = r["_date_key"]
        tot = r.get("total")
        if not isinstance(tot, (int, float)):
            w = r.get("weight")
            reps = r.get("reps")
            if isinstance(w, (int, float)) and isinstance(reps, (int, float)):
                tot = float(w) * float(reps)
            else:
                tot = 0.0
        buckets[dk.month] = buckets.get(dk.month, 0.0) + float(tot)
    return [{"period": f"{m:02d}", "volume": float(v)}
            for m, v in sorted(buckets.items())]

# -----------------------------
# Workout APIs (single, non-duplicated set)
# -----------------------------
@app.route("/api/workout/options")
def api_workout_options():
    """
    Returns mapping of muscle_group -> exercises, and exercise -> muscle_group.
    Used to populate per-chart exercise dropdowns.
    """
    try:
        year = _get_year_arg(2025)
        rows = [dict(r) for r in get_rows(year)]
    except Exception:
        rows = []

    def clean(s):
        return (s or "").strip()

    group_to_ex = {}
    ex_to_group = {}

    for r in rows:
        g = clean(r.get("muscle_group"))
        e = clean(r.get("exercise"))
        if not g or not e:
            continue
        group_to_ex.setdefault(g, set()).add(e)
        ex_to_group[e] = g

    # sets -> sorted lists
    group_to_ex = {g: sorted(list(exs)) for g, exs in group_to_ex.items()}

    return jsonify({
        "groups": sorted(group_to_ex.keys()),
        "group_to_ex": group_to_ex,
        "ex_to_group": ex_to_group,
    })

@app.route("/api/workout/group_series")
def api_workout_group_series():

    from flask import abort

    muscle = (request.args.get("muscle") or "").strip()
    exercise = (request.args.get("exercise") or "").strip()

    if not muscle:
        return abort(400, "muscle is required")

    try:
        year = _get_year_arg(2025)
        rows = [_ensure_row_normalized(dict(r)) for r in get_rows(year)]
    except Exception:
        rows = []

    # filter rows to this target
    target_rows = []
    for r in rows:
        if not r.get("_date_key"):
            continue
        if not _eq_ci(r.get("muscle_group"), muscle):
            continue
        # if exercise filter applied, keep only that exercise
        if exercise and exercise.lower() != "all":
            if not _eq_ci(r.get("exercise"), exercise):
                continue
        target_rows.append(r)

    # no rows -> empty series
    if not target_rows:
        return jsonify({
            "muscle_group": muscle,
            "exercise": exercise or "All",
            "mode": "volume" if (not exercise or exercise.lower() == "all") else "weight",
            "points": [],
        })

    # All exercises -> volume per date (sum total or weight*reps)
    if not exercise or exercise.lower() == "all":
        buckets = {}
        for r in target_rows:
            dk = r["_date_key"]
            label = r.get("date") or dk.strftime("%m/%d")
            tot = r.get("total")
            if not isinstance(tot, (int, float)):
                w = r.get("weight")
                reps = r.get("reps")
                if isinstance(w, (int, float)) and isinstance(reps, (int, float)):
                    tot = float(w) * float(reps)
                else:
                    tot = 0.0
            buckets.setdefault(label, 0.0)
            buckets[label] += float(tot)

        # sort by date as MM/DD using our fake-year key
        def parse_label(lbl):
            try:
                m, d = lbl.split("/")
                return _date(2000, int(m), int(d))
            except Exception:
                return _date(2000, 1, 1)

        pts = [{"date": lbl, "value": buckets[lbl]}
               for lbl in sorted(buckets.keys(), key=parse_label)]

        return jsonify({
            "muscle_group": muscle,
            "exercise": "All",
            "mode": "volume",
            "points": pts,
        })

    # Specific exercise -> training weight per date (use max weight per date)
    tmp = {}
    for r in target_rows:
        dk = r["_date_key"]
        label = r.get("date") or dk.strftime("%m/%d")
        w = r.get("weight")
        # if weight missing but total/reps present, approximate
        if w is None:
            tot = r.get("total")
            reps = r.get("reps")
            if isinstance(tot, (int, float)) and isinstance(reps, (int, float)) and reps != 0:
                w = float(tot) / float(reps)
        if w is None:
            continue
        if label not in tmp or w > tmp[label]:
            tmp[label] = float(w)

    def parse_label(lbl):
        try:
            m, d = lbl.split("/")
            return _date(2000, int(m), int(d))
        except Exception:
            return _date(2000, 1, 1)

    pts = [{"date": lbl, "value": tmp[lbl]}
           for lbl in sorted(tmp.keys(), key=parse_label)]

    return jsonify({
        "muscle_group": muscle,
        "exercise": exercise,
        "mode": "weight",
        "points": pts,
    })

@app.route("/api/workout/progress_by_group")
def api_workout_progress_by_group():

    exercise = request.args.get("exercise")  # may be None / "All"
    try:
        year = _get_year_arg(2025)
        rows = [_ensure_row_normalized(dict(r)) for r in get_rows(year)]
    except Exception:
        rows = []

    # build group -> rows
    grouped = {}
    for r in rows:
        dk = r.get("_date_key")
        g = r.get("muscle_group")
        if not dk or not g:
            continue

        # if exercise filter applied, keep only matching exercise
        if exercise and exercise.lower() != "all":
            if not _eq_ci(r.get("exercise"), exercise):
                continue

        grouped.setdefault(g, []).append(r)

    # build series per group using existing helper
    result = []
    for g, rlist in grouped.items():
        seq = _group_max_weight_by_date(rlist)  # [(MM/DD, weight), ...]
        points = [{"date": d, "weight": float(w)} for d, w in seq]
        result.append({"muscle_group": g, "points": points})

    # sort by muscle_group name for stable layout
    result.sort(key=lambda x: x["muscle_group"])
    return jsonify(result)

@app.route("/api/workout/volume")
def api_workout_volume():
    # I keep 'period' param for flexibility, but front-end will always send 'W' (weekly)
    period = (request.args.get("period") or "W").upper()  # 'W' or 'M'
    muscle = request.args.get("muscle")
    year = _get_year_arg(2025)
    rows = _filter_rows(muscle=muscle, exercise=None, year=year)

    if period == "M":
        return jsonify(_sum_total_by_month(rows))
    return jsonify(_sum_total_by_week(rows))

@app.route("/api/workout/frequency")
def api_workout_frequency():
    """
    period=W (weekly) or M (monthly)
    Returns how many DAYS had workouts in each period,
    counting unique dates, not sets/reps.
    """
    period = (request.args.get("period") or "W").upper()

    try:
        year = _get_year_arg(2025)
        rows = [_ensure_row_normalized(dict(r)) for r in get_rows(year)]
    except Exception:
        rows = []

    # collect unique workout days as _date_key values
    days = sorted({r["_date_key"] for r in rows if r.get("_date_key")})

    if period == "M":
        # (year, month) -> set(day)
        buckets = {}
        for d in days:
            key = (d.year, d.month)
            buckets.setdefault(key, set()).add(d.day)
        out = []
        for (yy, mm), dayset in sorted(buckets.items()):
            label = f"{mm:02d}"  # e.g. "01" for Jan
            out.append({"period": label, "count": len(dayset)})
        return jsonify(out)

    # default: weekly frequency
    buckets = {}
    for d in days:
        wk_start = d - timedelta(days=d.weekday())  # Monday-start week
        buckets.setdefault(wk_start, set()).add(d)
    out = []
    for wk_start, dayset in sorted(buckets.items()):
        label = wk_start.strftime("%m/%d")  # label the week by its Monday
        out.append({"period": label, "count": len(dayset)})
    return jsonify(out)

@app.route("/api/workout/anomalies")
def api_workout_anomalies():
    year = _get_year_arg(2025)

    # optional knobs (safe defaults)
    try:
        contamination = float(request.args.get("contamination", "0.15"))
        contamination = max(0.05, min(0.30, contamination))  # clamp
    except Exception:
        contamination = 0.15

    try:
        limit = int(request.args.get("limit", "8"))
        limit = max(1, min(50, limit))
    except Exception:
        limit = 8

    try:
        weeks = build_weekly_features(year)
        result = detect_anomalies(weeks, year=year, contamination=contamination)

        # Sort anomalies by "most anomalous" first (lowest score)
        anomalies = result.get("anomalies", [])
        anomalies.sort(key=lambda x: x.get("score", 0.0))

        # Keep only top N
        anomalies = anomalies[:limit]

        return jsonify({
            "year": year,
            "reason": result.get("reason", "ok"),
            "count": len(anomalies),
            "anomalies": anomalies,
        })
    except Exception as e:
        return jsonify({
            "year": year,
            "reason": "error",
            "error": str(e),
            "count": 0,
            "anomalies": [],
        }), 500

@app.get("/api/workout/coach")
def api_workout_coach():
    selected_year = int(request.args.get("year", 2025))
    return jsonify(build_coach_message(selected_year))
