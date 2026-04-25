def classify_score(score: float) -> str:
    if score >= 8:
        return "Strong"
    elif score >= 6:
        return "Adequate"
    elif score >= 3:
        return "Gap"
    else:
        return "Critical Gap"

def analyze_gaps(required_skills: list, skill_scores: dict, candidate_skills: list) -> dict:
    results = []
    for skill in required_skills:
        score_data = skill_scores.get(skill, {"score": 0.0, "notes": "Not assessed"})
        score = float(score_data.get("score", 0.0))
        label = classify_score(score)
        results.append({
            "skill": skill,
            "score": score,
            "status_label": label,
            "notes": score_data.get("notes", ""),
            "is_gap": score < 6,
        })

    total = sum(r["score"] for r in results)
    overall = (total / len(results)) if results else 0
    readiness = "Ready" if overall >= 7 else "Partially Ready" if overall >= 5 else "Not Ready"
    return {
        "skill_results": results,
        "overall_score": round(overall * 10),  # 0–100
        "readiness_label": readiness
    }
