import os, time
from datetime import date as _date, datetime as _dt, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "workout-dashboard-476518-f4b943386f4f.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SHEET_ID = "1hwTeWjYiuWh6yjjpomGZ5WaxOaAngfuQn8uMdZPyjOk"
RANGE = "'2025'!A:F"   # Date, Target, Exercise, Weight, Reps, Total

# cache to reduce API calls
_CACHE = {"rows": None, "expires": 0}
TTL_SECONDS = 600  # 10 min

# Map the headers -> normalized keys the app uses
_HEADER_MAP = {
    "Date": "date",             # stays as "MM/DD" string externally
    "Target": "muscle_group",
    "Exercise": "exercise",
    "Weight": "weight",
    "Reps": "reps",
    "Total": "total",
}

def _parse_mmdd(mmdd: str):
    """
    Take strings like '1/2' or '01/02' and return:
      - display string 'MM/DD' (zero-padded)
      - internal key as date(2000, MM, DD) for safe ordering/grouping
    """
    mmdd = (mmdd or "").strip()
    try:
        parts = mmdd.split("/")
        mm = int(parts[0]); dd = int(parts[1])
        disp = f"{mm:02d}/{dd:02d}"
        key = _date(2000, mm, dd)  # harmless fixed year for logic
        return disp, key
    except Exception:
        return "", None

def _fetch_rows():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    svc = build("sheets", "v4", credentials=creds)
    resp = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=RANGE).execute()
    vals = resp.get("values", [])
    if not vals:
        return []

    raw_headers = vals[0]
    data = vals[1:]

    # Build column index -> normalized key
    col_to_key = {}
    for i, h in enumerate(raw_headers):
        if h in _HEADER_MAP:
            col_to_key[i] = _HEADER_MAP[h]

    rows = []
    for row in data:
        rec = {"date": "", "muscle_group": "", "exercise": "", "weight": None, "reps": None, "total": None}
        for i, key in col_to_key.items():
            val = row[i] if i < len(row) else ""
            if key in ("weight", "reps", "total"):
                try:
                    rec[key] = float(val) if val != "" else None
                except Exception:
                    rec[key] = None
            elif key == "date":
                disp, keydate = _parse_mmdd(val)
                rec["date"] = disp              # public-facing 'MM/DD'
                rec["_date_key"] = keydate      # internal date(2000, mm, dd)
            else:
                rec[key] = (val or "").strip()

        # ensure internal key exists even if date missing
        if "_date_key" not in rec:
            disp, keydate = _parse_mmdd(rec.get("date", ""))
            rec["date"] = disp
            rec["_date_key"] = keydate

        rows.append(rec)
    return rows

def get_rows():
    now = time.time()
    if _CACHE["rows"] is None or now >= _CACHE["expires"]:
        _CACHE["rows"] = _fetch_rows()
        _CACHE["expires"] = now + TTL_SECONDS
    return _CACHE["rows"]

def unique_exercises():
    seen = set()
    for r in get_rows():
        ex = (r.get("exercise") or "").strip()
        if ex:
            seen.add(ex)
    return sorted(seen)

def unique_muscle_groups():
    seen = set()
    for r in get_rows():
        mg = (r.get("muscle_group") or "").strip()
        if mg:
            seen.add(mg)
    return sorted(seen)
