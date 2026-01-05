# ai_ml.py
# Real AI (unsupervised ML) anomaly detection for your workout dashboard
# Uses weekly features: volume, frequency, and per-target volume shares.
# Year-aware: reads from Google Sheet tab "2025", "2026", etc via sheets_client.get_rows(year)

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest

from sheets_client import get_rows


# --------- configuration ----------
DEFAULT_CONTAMINATION = 0.15  # expected fraction of "unusual" weeks
MIN_WEEKS_FOR_MODEL = 6       # need enough history to learn baseline

# Your sheet "Target" values (normalize variations here)
TARGETS_CANONICAL = [
    "Arms Shoulders",
    "Back",
    "Chest",
    "Legs",
]


def _norm(s: Any) -> str:
    return (s or "").strip()


def _canonical_target(raw: str) -> str:
    """
    Normalize target labels to 4 canonical buckets.
    Adjust here if your sheet uses slightly different labels.
    """
    t = _norm(raw)

    # common variants
    if t.lower() in {"arms", "shoulders", "arm & shoulder", "arms & shoulder", "arms shoulders", "arms/shoulders"}:
        return "Arms Shoulders"
    if t.lower() in {"arms shoulders", "arms  shoulders"}:
        return "Arms Shoulders"
    if t.lower() in {"back"}:
        return "Back"
    if t.lower() in {"chest"}:
        return "Chest"
    if t.lower() in {"legs", "leg"}:
        return "Legs"

    # fallback: keep original if it matches exactly
    if t in TARGETS_CANONICAL:
        return t

    # unknown bucket
    return "Other"


def _week_start(d: date) -> date:
    # Monday start (matches your Flask aggregation approach)
    return d - timedelta(days=d.weekday())

def _display_date(year: int, md_date: date) -> date:
    """
    Convert a month/day-only date (year 2000) into a real calendar date for display.
    Safe because each sheet tab is a single year.
    """
    return date(int(year), md_date.month, md_date.day)

def _robust_z(x: np.ndarray) -> np.ndarray:
    """
    Robust z-score using median and MAD.
    Used only for labeling/explanations (not the ML model itself).
    """
    if x.size == 0:
        return x
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    if mad == 0:
        return np.zeros_like(x, dtype=float)
    return 0.6745 * (x - med) / mad


@dataclass
class WeekFeature:
    week_start: date
    volume: float
    frequency: int
    shares: Dict[str, float]  # canonical target -> share of weekly volume

    def to_vector(self) -> List[float]:
        return [
            float(self.volume),
            float(self.frequency),
            float(self.shares.get("Legs", 0.0)),
            float(self.shares.get("Back", 0.0)),
            float(self.shares.get("Chest", 0.0)),
            float(self.shares.get("Arms Shoulders", 0.0)),
        ]


def build_weekly_features(year: int) -> List[WeekFeature]:
    """
    Build one feature row per week from the sheet tab for `year`.
    Requires sheets_client.get_rows(year) to return rows with _date_key and total.
    """
    rows = get_rows(int(year))

    # bucket: week_start -> accumulators
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
        shares: Dict[str, float] = {}

        if vol > 0:
            for k, v in acc["targets"].items():
                shares[k] = float(v) / vol
        else:
            for k in TARGETS_CANONICAL:
                shares[k] = 0.0

        out.append(WeekFeature(
            week_start=ws,
            volume=vol,
            frequency=freq,
            shares=shares,
        ))

    out.sort(key=lambda w: w.week_start)
    return out


def detect_anomalies(
    weeks: List[WeekFeature],
    year: int,
    contamination: float = DEFAULT_CONTAMINATION,
    random_state: int = 42,
) -> Dict[str, Any]:

    """
    Runs IsolationForest over weekly vectors.
    Returns both the week list and anomaly flags + a lightweight explanation label.
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
    preds = model.fit_predict(X)               # -1 anomaly, +1 normal
    scores = model.decision_function(X)        # lower = more anomalous

    # robust z-scores for explanations
    vol_z = _robust_z(X[:, 0])
    freq_z = _robust_z(X[:, 1])

    # dominance = max share across the 4 targets (balance signal)
    max_share = np.max(X[:, 2:6], axis=1) if X.shape[1] >= 6 else np.zeros(len(weeks))
    dom_z = _robust_z(max_share)

    anomalies: List[Dict[str, Any]] = []
    all_weeks: List[Dict[str, Any]] = []

    for w, pred, sc, vz, fz, dz, mshare in zip(weeks, preds, scores, vol_z, freq_z, dom_z, max_share):
        # explanation labeling (simple but useful)
        label_parts = []
        if vz >= 2.5:
            label_parts.append("high_volume")
        elif vz <= -2.5:
            label_parts.append("low_volume")

        if fz >= 2.5:
            label_parts.append("high_frequency")
        elif fz <= -2.5:
            label_parts.append("low_frequency")

        if dz >= 2.5 or mshare >= 0.75:
            label_parts.append("imbalanced_targets")

        label = "mixed" if len(label_parts) >= 2 else (label_parts[0] if label_parts else "unusual_pattern")

        ws_display = _display_date(year, w.week_start)

        payload = {
            "week_start": ws_display.isoformat(),
            "volume": int(round(w.volume)),
            "frequency": int(w.frequency),
            "shares": {k: round(float(w.shares.get(k, 0.0)), 4) for k in TARGETS_CANONICAL},
            "dominant_target": max(w.shares, key=w.shares.get) if w.shares else None,
            "dominant_share": round(float(max(w.shares.values())) if w.shares else 0.0, 4),
            "anomaly": bool(pred == -1),
            "score": float(sc),      # lower = more anomalous
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


# --------- quick CLI test ----------
if __name__ == "__main__":
    year = 2025
    feats = build_weekly_features(year)
    result = detect_anomalies(feats, year=year)

    if result["reason"] == "not_enough_data":
        print(f"Not enough data for {year} (need at least {MIN_WEEKS_FOR_MODEL} weeks).")
    else:
        for a in result["anomalies"]:
            ws = a["week_start"]
            print(f"🚨 ANOMALY | {ws} | vol={a['volume']:,}, freq={a['frequency']} | "
                  f"dom={a['dominant_target']}({a['dominant_share']:.2f}) | {a['label']}")
