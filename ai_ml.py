# ai_ml.py
# Unsupervised ML anomaly detection + weekly feature builder for the workout dashboard.
# Year-aware: reads from Google Sheet tab "2025", "2026", etc via sheets_client.get_rows(year)
#
# Key design:
# - Weekly features include:
#   - total weekly volume
#   - weekly frequency (# distinct training days)
#   - per-target volume shares (balance signal)
#   - per-target absolute weekly volumes (so the coach can compare Back vs Back, etc.)
#
# NOTE: The sheet date is month/day only, so rows should already include "_date_key"
# (a date object with a dummy year, usually 2000) created in sheets_client.py.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest

from sheets_client import get_rows


# -------------------- config --------------------
DEFAULT_CONTAMINATION = 0.15
MIN_WEEKS_FOR_MODEL = 6

TARGETS_CANONICAL = [
    "Arms Shoulders",
    "Back",
    "Chest",
    "Legs",
]


# -------------------- helpers --------------------
def _norm(s: Any) -> str:
    return (s or "").strip()


def _canonical_target(raw: Any) -> str:
    """
    Normalize target labels to 4 canonical buckets.
    Adjust this mapping if the sheet labels differ.
    """
    t = _norm(raw)
    tl = t.lower()

    if tl in {"arms", "shoulders", "arm & shoulder", "arms & shoulder", "arms and shoulders",
              "arms shoulders", "arms/shoulders"}:
        return "Arms Shoulders"
    if tl == "back":
        return "Back"
    if tl == "chest":
        return "Chest"
    if tl in {"legs", "leg"}:
        return "Legs"

    if t in TARGETS_CANONICAL:
        return t

    return "Other"


def _week_start(d: date) -> date:
    # Monday as start of week
    return d - timedelta(days=d.weekday())


def _display_date(year: int, md_date: date) -> date:
    """
    Convert a month/day-only date (dummy year) into a real calendar date for display.
    Safe because each Google Sheet tab is a single year.
    """
    return date(int(year), md_date.month, md_date.day)


def _robust_z(x: np.ndarray) -> np.ndarray:
    """
    Robust z-score using median + MAD.
    Used only for labeling/explanations (not required for the model itself).
    """
    if x.size == 0:
        return x
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    if mad == 0:
        return np.zeros_like(x, dtype=float)
    return 0.6745 * (x - med) / mad


# -------------------- core types --------------------
@dataclass
class WeekFeature:
    week_start: date
    volume: float
    frequency: int
    shares: Dict[str, float]          # target -> share of weekly volume
    target_volumes: Dict[str, float]  # target -> absolute weekly volume

    def to_vector(self) -> List[float]:
        """
        Feature vector for the ML model.
        Use log1p(volume) to reduce scale dominance (e.g., legs-heavy totals).
        """
        vol = float(np.log1p(max(self.volume, 0.0)))
        return [
            vol,
            float(self.frequency),
            float(self.shares.get("Legs", 0.0)),
            float(self.shares.get("Back", 0.0)),
            float(self.shares.get("Chest", 0.0)),
            float(self.shares.get("Arms Shoulders", 0.0)),
        ]


# -------------------- feature builder --------------------
def build_weekly_features(year: int) -> List[WeekFeature]:
    """
    Build one WeekFeature per week from a single-year tab.
    Expects get_rows(year) rows to include:
      - "_date_key": datetime.date (dummy year, e.g. 2000)
      - "total": numeric
      - "muscle_group": str
    """
    rows = get_rows(int(year))

    weekly: Dict[date, Dict[str, Any]] = {}

    for r in rows:
        d = r.get("_date_key")
        if not isinstance(d, date):
            continue

        ws = _week_start(d)
        weekly.setdefault(ws, {
            "volume": 0.0,
            "days": set(),
            "targets": {k: 0.0 for k in TARGETS_CANONICAL},
            "other": 0.0,
        })

        total = float(r.get("total") or 0.0)
        weekly[ws]["volume"] += total
        weekly[ws]["days"].add(d)

        tgt = _canonical_target(r.get("muscle_group"))
        if tgt in TARGETS_CANONICAL:
            weekly[ws]["targets"][tgt] += total
        else:
            weekly[ws]["other"] += total

    out: List[WeekFeature] = []
    for ws, acc in weekly.items():
        vol = float(acc["volume"])
        freq = len(acc["days"])

        target_vols = {k: float(acc["targets"].get(k, 0.0)) for k in TARGETS_CANONICAL}

        shares: Dict[str, float] = {}
        if vol > 0:
            for k in TARGETS_CANONICAL:
                shares[k] = float(target_vols.get(k, 0.0)) / vol
        else:
            for k in TARGETS_CANONICAL:
                shares[k] = 0.0

        out.append(WeekFeature(
            week_start=ws,
            volume=vol,
            frequency=freq,
            shares=shares,
            target_volumes=target_vols,
        ))

    out.sort(key=lambda w: w.week_start)
    return out


# -------------------- anomaly detection --------------------
def detect_anomalies(
    weeks: List[WeekFeature],
    year: int,
    contamination: float = DEFAULT_CONTAMINATION,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Fit IsolationForest on weekly feature vectors.
    Returns:
      - "weeks": all weeks with metadata
      - "anomalies": subset flagged as anomalies
    """
    if len(weeks) < MIN_WEEKS_FOR_MODEL:
        return {
            "ok": True,
            "reason": "not_enough_data",
            "weeks": [],
            "anomalies": [],
        }

    X = np.array([w.to_vector() for w in weeks], dtype=float)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
    )
    preds = model.fit_predict(X)         # -1 anomaly, +1 normal
    scores = model.decision_function(X)  # lower = more anomalous

    # Explanation helpers
    vol_arr = np.array([w.volume for w in weeks], dtype=float)
    freq_arr = np.array([w.frequency for w in weeks], dtype=float)

    vol_z = _robust_z(vol_arr)
    freq_z = _robust_z(freq_arr)

    # per-target robust z (within-target comparisons)
    tgt_mat = np.array(
        [[w.target_volumes.get(t, 0.0) for t in TARGETS_CANONICAL] for w in weeks],
        dtype=float
    )
    tgt_z = np.zeros_like(tgt_mat, dtype=float)
    for j in range(tgt_mat.shape[1]):
        tgt_z[:, j] = _robust_z(tgt_mat[:, j])

    # balance signal: dominant share
    shares_mat = np.array([[w.shares.get(t, 0.0) for t in TARGETS_CANONICAL] for w in weeks], dtype=float)
    max_share = np.max(shares_mat, axis=1) if shares_mat.size else np.zeros(len(weeks))
    dom_z = _robust_z(max_share)

    all_weeks: List[Dict[str, Any]] = []
    anomalies: List[Dict[str, Any]] = []

    for idx, (w, pred, sc) in enumerate(zip(weeks, preds, scores)):
        label_parts: List[str] = []

        # workload labels (overall)
        if vol_z[idx] >= 2.5:
            label_parts.append("workload_high")
        elif vol_z[idx] <= -2.5:
            label_parts.append("workload_low")

        if freq_z[idx] >= 2.5:
            label_parts.append("high_frequency")
        elif freq_z[idx] <= -2.5:
            label_parts.append("low_frequency")

        # within-target unusual movement
        j_best = int(np.argmax(np.abs(tgt_z[idx, :])))
        focus_target = TARGETS_CANONICAL[j_best]
        focus_z = float(tgt_z[idx, j_best])

        if abs(focus_z) >= 2.5:
            label_parts.append(f"{focus_target}_high" if focus_z > 0 else f"{focus_target}_low")

        # balance: dominant share unusually high
        if dom_z[idx] >= 2.5 or float(max_share[idx]) >= 0.75:
            label_parts.append("imbalanced_targets")

        label = "unusual_pattern"
        if len(label_parts) >= 2:
            label = "mixed"
        elif len(label_parts) == 1:
            label = label_parts[0]

        ws_display = _display_date(year, w.week_start)

        dominant_target = max(w.shares, key=w.shares.get) if w.shares else None
        dominant_share = float(max(w.shares.values())) if w.shares else 0.0

        payload = {
            "week_start": ws_display.isoformat(),
            "volume": int(round(w.volume)),
            "frequency": int(w.frequency),
            "shares": {k: round(float(w.shares.get(k, 0.0)), 4) for k in TARGETS_CANONICAL},
            "target_volumes": {k: int(round(float(w.target_volumes.get(k, 0.0)))) for k in TARGETS_CANONICAL},
            "dominant_target": dominant_target,
            "dominant_share": round(dominant_share, 4),
            "focus_target": focus_target,
            "focus_target_z": round(focus_z, 3),
            "anomaly": bool(pred == -1),
            "score": float(sc),
            "label": label,
        }

        all_weeks.append(payload)
        if pred == -1:
            anomalies.append(payload)

    return {
        "ok": True,
        "reason": "ok",
        "weeks": all_weeks,
        "anomalies": anomalies,
    }


# -------------------- quick CLI test --------------------
if __name__ == "__main__":
    year = 2025
    feats = build_weekly_features(year)
    result = detect_anomalies(feats, year=year)

    if result["reason"] == "not_enough_data":
        print(f"Not enough data for {year} (need at least {MIN_WEEKS_FOR_MODEL} weeks).")
    else:
        for a in result["anomalies"]:
            ws = a["week_start"]
            print(
                f"🚨 ANOMALY | {ws} | vol={a['volume']:,}, freq={a['frequency']} | "
                f"focus={a['focus_target']} z={a['focus_target_z']} | {a['label']}"
            )
