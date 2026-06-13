# ai_coach.py
# Coach Dwayne (rule-based + light ML evidence)
#
# What this file does:
# - Generates a friendly coach message based on RECENT training patterns.
# - Supports cross-year “you started earlier than last year” messaging by checking
#   whether I had logged anything by today’s month/day in another year tab.
#
# Important behavior:
# - Main analysis uses `today_year` (defaults to system current year).
# - Cross-year comparison uses `compare_year` (defaults to the selected page year).
# - Within-target comparisons (Legs vs Legs, etc.) are allowed only when baseline is meaningful.
# - No markdown, no tips.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ai_ml import TARGETS_CANONICAL, build_weekly_features, detect_anomalies
from sheets_client import get_rows


# -----------------------------
# small helpers
# -----------------------------
def _md_index(d: date) -> int:
    """Month/day sortable index."""
    return d.month * 100 + d.day


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _trend_pct_last2_vs_prev2(series: List[float], min_baseline: float) -> Optional[float]:
    """
    % change of sum(last 2) vs sum(previous 2).
    Returns None if:
      - fewer than 4 points, OR
      - baseline too small (guardrail against silly +100%).
    """
    if len(series) < 4:
        return None
    last2 = series[-2] + series[-1]
    prev2 = series[-4] + series[-3]
    if prev2 < min_baseline:
        return None
    return ((last2 - prev2) / prev2) * 100.0


def _pick_most_changed_target(
    recent_weeks,
    min_target_baseline: float = 20000.0,   # higher guardrail to avoid misleading % early-year
) -> Tuple[Optional[str], Optional[float]]:
    """
    Choose target with largest |% change| comparing last2 vs prev2,
    but only if that target’s baseline is meaningful.
    """
    best_t: Optional[str] = None
    best_p: Optional[float] = None

    for t in TARGETS_CANONICAL:
        s = [float(w.target_volumes.get(t, 0.0)) for w in recent_weeks]
        p = _trend_pct_last2_vs_prev2(s, min_baseline=min_target_baseline)
        if p is None:
            continue
        if best_p is None or abs(p) > abs(best_p):
            best_t = t
            best_p = p

    return best_t, best_p


def _has_any_workout_upto_md(year: int, md: int) -> bool:
    """
    True if the given year tab has any row with month/day <= md.
    Uses month/day only (the sheet date has no year).
    """
    rows = get_rows(int(year))
    for r in rows:
        d = r.get("_date_key")
        if isinstance(d, date) and _md_index(d) <= md:
            return True
    return False


def _has_workout_on_md(year: int, md: int) -> bool:
    """True if the given year tab has any row exactly on that month/day."""
    rows = get_rows(int(year))
    for r in rows:
        d = r.get("_date_key")
        if isinstance(d, date) and _md_index(d) == md:
            return True
    return False


# -----------------------------
# public output type
# -----------------------------
@dataclass
class CoachMessage:
    name: str
    mood: str   # neutral | proud | watchful | warning | recovery | motivating
    title: str
    message: str
    focus: str  # Momentum | Consistency | Balance | Recovery


# -----------------------------
# main API
# -----------------------------
def build_coach_message(
    selected_year: int,
    today_year: Optional[int] = None,
    today_md: Optional[int] = None,
) -> Dict[str, Any]:
   
    selected_year = int(selected_year)
    today_year = int(today_year) if today_year is not None else date.today().year

    # Main analysis is based on today_year
    weeks = build_weekly_features(today_year)

    # ---- Cross-year (existence/timing only) ----
    if today_md is None:
        md_today = int(today_md) if today_md is not None else _md_index(date.today())
    else:
        md_today = int(today_md)

    cross_year_line = ""
    if selected_year != today_year:
        if _has_workout_on_md(today_year, md_today) and (not _has_any_workout_upto_md(selected_year, md_today)):
            cross_year_line = (
                f" At this point in {selected_year}, you hadn’t started training yet — that’s real momentum."
            )

    # ---- If not enough data in the current year, keep it friendly ----
    if len(weeks) < 2:
        msg = CoachMessage(
            name="Dwayne",
            mood="neutral",
            title="Warming up",
            message=(
                "I’m ready when you are. Log a few more sessions and I’ll coach from my real patterns."
                + cross_year_line
            ),
            focus="Momentum",
        )
        return {
            "year": selected_year,          # keep the existing contract
            "today_year": today_year,       # helpful for debugging
            "name": msg.name,
            "mood": msg.mood,
            "title": msg.title,
            "message": msg.message,
            "focus": msg.focus,
            "anomaly_count": 0,
        }

    # Recent window (up to 8 weeks)
    recent = weeks[-8:] if len(weeks) >= 8 else weeks[:]
    vols_total = [float(w.volume) for w in recent]
    freqs = [int(w.frequency) for w in recent]
    avg_freq = (sum(freqs) / len(freqs)) if freqs else 0.0

    # Overall trend with a stronger guardrail
    overall_trend = _trend_pct_last2_vs_prev2(vols_total, min_baseline=40000.0)

    # Within-target trend (optional). Only include if it’s truly meaningful.
    target_line = ""
    if len(recent) >= 4:
        t_best, p_best = _pick_most_changed_target(recent, min_target_baseline=25000.0)
        if t_best is not None and p_best is not None and abs(p_best) >= 45.0:
            target_line = f" Your {t_best} workload has shifted a lot compared to your own recent baseline."

    # Balance signal: dominant share over recent weeks
    dom_targets: List[str] = []
    dom_shares: List[float] = []
    for w in recent:
        if w.shares:
            dom_t = max(w.shares, key=w.shares.get)
            dom_targets.append(dom_t)
            dom_shares.append(float(w.shares.get(dom_t, 0.0)))
        else:
            dom_shares.append(0.0)

    avg_dom_share = (sum(dom_shares) / len(dom_shares)) if dom_shares else 0.0
    imbalanced = avg_dom_share >= 0.70

    # ML evidence (optional)
    det = detect_anomalies(weeks, year=today_year, contamination=0.15)
    anomalies = det.get("anomalies", []) if det.get("reason") == "ok" else []
    recent_anoms = anomalies[-4:] if anomalies else []
    anom_count = len(recent_anoms)

    # Recovery risk heuristic (gentle)
    if overall_trend is None:
        recovery_risk = (anom_count >= 2 and avg_freq <= 2.5)
    else:
        recovery_risk = (overall_trend >= 35.0 and avg_freq <= 2.5) or (anom_count >= 2 and overall_trend >= 25.0)

    # Compose message (plain text, one main idea)
    avg_freq_str = f"{avg_freq:.1f}"

    if recovery_risk:
        mood = "recovery"
        title = "Recovery check"
        focus = "Recovery"
        if overall_trend is None:
            core = (
                f"Big push detected while frequency stays around {avg_freq_str} days/week."
                f"{target_line} Let’s protect your progress."
            )
        else:
            core = (
                f"Big push detected. Workload is up lately while frequency stays around {avg_freq_str} days/week."
                f"{target_line} That combo can sneak fatigue in."
            )

    elif imbalanced:
        mood = "watchful"
        title = "Balance check"
        focus = "Balance"
        common_dom = max(set(dom_targets), key=dom_targets.count) if dom_targets else "one target"
        core = (
            f"Your consistency is solid — about {avg_freq_str} days/week."
            f" Lately {common_dom} has been leading. Balance keeps you durable."
        )

    elif anom_count >= 1:
        mood = "warning"
        title = "Pattern shift"
        focus = "Consistency"
        core = (
            "I’m seeing a noticeable change in your recent pattern."
            " Keep it steady and you’ll adapt faster."
        )

    else:
        mood = "proud"
        title = "Solid work"
        focus = "Consistency"
        core = (
            f"Nice work. Consistency looks solid — about {avg_freq_str} workout days/week lately."
            f" Keep that rhythm."
        )

    message = core + cross_year_line

    return {
        "year": selected_year,          # keep the existing contract (dropdown year)
        "today_year": today_year,       # the year the coaching is based on
        "name": "Dwayne",
        "mood": mood,
        "title": title,
        "message": message,
        "focus": focus,
        "anomaly_count": len(anomalies),
    }
