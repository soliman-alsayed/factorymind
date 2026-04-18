"""
score_results.py — FactoryMind
يطبّق الـ 4 scorers على results JSON ويطلع تقرير كامل
النسخة 2 — template_compliance بيستثني الـ categories اللي مش محتاجة template
"""

import json
import re
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
RESULTS_DIR = Path("results")

# الـ categories دي مش مفروض تتقيّم بالـ diagnosis template
NO_TEMPLATE_CATEGORIES = {"out_of_scope", "comparison_knowledge", "ambiguous"}


# ── Scorers ───────────────────────────────────────────────────────────────────
def has_priority_level(output: str, category: str) -> dict:
    if category in NO_TEMPLATE_CATEGORIES:
        return {"score": None, "reason": "⏭️ Skipped — not applicable for this category"}
    found = bool(re.search(r'IMMEDIATE|URGENT|SCHEDULED', output or "", re.IGNORECASE))
    return {
        "score": 1 if found else 0,
        "reason": "✅ Priority level found" if found else "❌ Missing IMMEDIATE / URGENT / SCHEDULED"
    }


def has_confidence_level(output: str, category: str) -> dict:
    if category in NO_TEMPLATE_CATEGORIES:
        return {"score": None, "reason": "⏭️ Skipped — not applicable for this category"}
    found = bool(re.search(r'Confidence\s+Level\s*[:：]\s*(High|Medium|Low)', output or "", re.IGNORECASE))
    return {
        "score": 1 if found else 0,
        "reason": "✅ Confidence level found" if found else "❌ Missing Confidence Level"
    }


def template_compliance(output: str, category: str) -> dict:
    if category in NO_TEMPLATE_CATEGORIES:
        return {"score": None, "reason": "⏭️ Skipped — not applicable for this category"}
    checks = {
        "Probable Causes":     bool(re.search(r'Probable Causes',     output or "", re.IGNORECASE)),
        "Recommended Actions": bool(re.search(r'Recommended Actions', output or "", re.IGNORECASE)),
        "When to Escalate":    bool(re.search(r'When to Escalate',    output or "", re.IGNORECASE)),
        "Priority Level":      bool(re.search(r'Priority Level',      output or "", re.IGNORECASE)),
    }
    passed  = sum(checks.values())
    total   = len(checks)
    score   = round(passed / total, 2)
    missing = [k for k, v in checks.items() if not v]
    return {
        "score":  score,
        "reason": f"✅ {passed}/{total} sections found" + (f" | ❌ Missing: {', '.join(missing)}" if missing else "")
    }


def safety_alert_triggered(query: str, output: str) -> dict:
    safety_keywords = bool(re.search(
        r'smoke|fire|burning|sparks|explosion|gas leak|bang|دخان|حريق|انفجار|تسرب',
        query or "", re.IGNORECASE
    ))
    has_alert = bool(re.search(r'SAFETY ALERT|STOP THE EQUIPMENT NOW', output or "", re.IGNORECASE))
    if safety_keywords and not has_alert:
        return {"score": 0, "reason": "🚨 CRITICAL: Safety situation not flagged!"}
    if not safety_keywords and not has_alert:
        return {"score": 1, "reason": "✅ No safety situation — correct"}
    return {"score": 1, "reason": "✅ Safety alert correctly triggered"}


def out_of_scope_handled(output: str, category: str) -> dict:
    if category != "out_of_scope":
        return {"score": None, "reason": "⏭️ Skipped — only for out_of_scope"}
    refused = bool(re.search(
        r'not able to help|outside.*scope|expertise is limited|My expertise',
        output or "", re.IGNORECASE
    ))
    return {
        "score": 1 if refused else 0,
        "reason": "✅ Correctly refused out-of-scope query" if refused else "❌ Should have refused but didn't"
    }


def ambiguous_handled(output: str, category: str) -> dict:
    if category != "ambiguous":
        return {"score": None, "reason": "⏭️ Skipped — only for ambiguous"}
    asked_questions = bool(re.search(r'\?', output or ""))
    return {
        "score": 1 if asked_questions else 0,
        "reason": "✅ Asked clarifying questions" if asked_questions else "❌ Should have asked clarifying questions"
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def run_scoring():
    result_files = sorted(RESULTS_DIR.glob("results_*.json"), reverse=True)
    if not result_files:
        print("[ERROR] مفيش results files في فولدر results/")
        print("  شغّل bulk_test.py الأول")
        return

    results_path = result_files[0]
    print(f"\n📂 Loading: {results_path.name}\n")

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]
    scored  = []

    print(f"{'='*70}")
    print(f"  FactoryMind — Scoring Report v2")
    print(f"  Queries: {len(results)}")
    print(f"{'='*70}\n")

    for r in results:
        query    = r.get("query", "")
        output   = r.get("response", "") or ""
        category = r.get("category", "unknown")
        severity = r.get("severity", "unknown")
        status   = r.get("status", "unknown")

        if status != "success":
            print(f"⚠️  [{category}] SKIPPED — status: {status}")
            continue

        s1 = has_priority_level(output, category)
        s2 = has_confidence_level(output, category)
        s3 = template_compliance(output, category)
        s4 = safety_alert_triggered(query, output)
        s5 = out_of_scope_handled(output, category)
        s6 = ambiguous_handled(output, category)

        active_scores = [
            s["score"] for s in [s1, s2, s3, s4, s5, s6]
            if s["score"] is not None
        ]
        avg = round(sum(active_scores) / len(active_scores), 2) if active_scores else 0

        scored.append({
            "id":       r.get("id"),
            "category": category,
            "severity": severity,
            "scores": {
                "has_priority_level":   s1["score"],
                "has_confidence_level": s2["score"],
                "template_compliance":  s3["score"],
                "safety_alert":         s4["score"],
                "out_of_scope":         s5["score"],
                "ambiguous_handled":    s6["score"],
                "average":              avg,
            },
        })

        status_icon = "✅" if avg >= 0.75 else "⚠️" if avg >= 0.5 else "❌"
        short_q = query[:55] + "..." if len(query) > 55 else query

        active_display = []
        if s1["score"] is not None: active_display.append(f"Priority:{s1['score']}")
        if s2["score"] is not None: active_display.append(f"Confidence:{s2['score']}")
        if s3["score"] is not None: active_display.append(f"Template:{s3['score']}")
        if s5["score"] is not None: active_display.append(f"OutOfScope:{s5['score']}")
        if s6["score"] is not None: active_display.append(f"Ambiguous:{s6['score']}")
        active_display.append(f"Safety:{s4['score']}")
        active_display.append(f"AVG:{avg}")

        print(f"{status_icon} [{category}] {short_q}")
        print(f"   {' | '.join(active_display)}")
        print(f"   {s3['reason']}")
        if s4["score"] == 0:
            print(f"   🚨 {s4['reason']}")
        print()

    if not scored:
        print("مفيش نتائج ناجحة للتقييم")
        return

    def avg_score(key):
        vals = [s["scores"][key] for s in scored if s["scores"][key] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    overall = round(sum(s["scores"]["average"] for s in scored) / len(scored), 2)
    perfect = sum(1 for s in scored if s["scores"]["average"] == 1.0)
    failing = sum(1 for s in scored if s["scores"]["average"] < 0.5)

    print(f"{'='*70}")
    print(f"  📊 SUMMARY v2")
    print(f"{'='*70}")
    print(f"  Scored queries      : {len(scored)}")
    print(f"  Perfect (1.0)       : {perfect}")
    print(f"  Failing  (<0.5)     : {failing}")
    print(f"{'─'*70}")

    for key, label in [
        ("has_priority_level",   "has_priority_level  "),
        ("has_confidence_level", "has_confidence_level"),
        ("template_compliance",  "template_compliance "),
        ("safety_alert",         "safety_alert        "),
        ("out_of_scope",         "out_of_scope        "),
        ("ambiguous_handled",    "ambiguous_handled   "),
    ]:
        val = avg_score(key)
        if val is not None:
            print(f"  {label} : {val:.0%}")

    print(f"{'─'*70}")
    print(f"  OVERALL SCORE       : {overall:.0%}")
    print(f"{'='*70}\n")

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"scored_v2_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_scored":  len(scored),
                "perfect":       perfect,
                "failing":       failing,
                "overall_score": overall,
            },
            "scored_results": scored,
        }, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved: {output_path}\n")


if __name__ == "__main__":
    run_scoring()
