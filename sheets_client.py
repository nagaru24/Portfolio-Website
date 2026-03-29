import os
import time
from datetime import date as _date
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Load .env automatically for local dev
try:
    from dotenv import load_dotenv
    load_dotenv()  # looks for .env in current working directory
except Exception:
    pass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SHEET_ID = "1hwTeWjYiuWh6yjjpomGZ5WaxOaAngfuQn8uMdZPyjOk"
def _range_for_year(year: int) -> str:
    # Tabs are named "2025", "2026", etc.
    return f"'{int(year)}'!A:F"  # Date, Target, Exercise, Weight, Reps, Total

# cache to reduce API calls
_CACHE = {}
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

def _get_service_account_file() -> str:

    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if path and os.path.isfile(path):
        return path

    raise RuntimeError(
        "Google Sheets credentials not found. "
        "Set environment variable GOOGLE_APPLICATION_CREDENTIALS to your service account JSON path."
    )

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

def _fetch_rows(year: int):
    rng = _range_for_year(year)
    try:
        service_account_file = _get_service_account_file()

        creds = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=SCOPES
        )
        svc = build("sheets", "v4", credentials=creds)
        resp = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=rng).execute()
        vals = resp.get("values", [])
        if not vals:
            return []
    except Exception as e:
        print("SHEETS ERROR:", repr(e))
        raise

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

def get_rows(year: int = 2026):
    year = int(year)
    now = time.time()
    entry = _CACHE.get(year)

    if (entry is None) or (now >= entry["expires"]):
        rows = _fetch_rows(year)
        _CACHE[year] = {"rows": rows, "expires": now + TTL_SECONDS}

    return _CACHE[year]["rows"]

def unique_exercises(year: int = 2026):
    seen = set()
    for r in get_rows(year):
        ex = (r.get("exercise") or "").strip()
        if ex:
            seen.add(ex)
    return sorted(seen)

def unique_muscle_groups(year: int = 2026):
    seen = set()
    for r in get_rows(year):
        mg = (r.get("muscle_group") or "").strip()
        if mg:
            seen.add(mg)
    return sorted(seen)
