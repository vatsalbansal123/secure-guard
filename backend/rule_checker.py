import json
import os

RULES_PATH = os.path.join(os.path.dirname(__file__), "rules", "owasp_rules.json")

with open(RULES_PATH) as f:
    RULES = json.load(f)

def scan_code(code):

    result = []
    for rule in RULES:

        for pattern in rule["code_patterns"]:

            if pattern.lower() in code.lower():

                result.append({
                    "rule_id": rule["rule_id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "remediation": rule["remediation_summary"]
                })

                break

    return result


# Points deducted from a perfect score (100) per finding, by severity.
SEVERITY_WEIGHTS = {
    "Critical": 40,
    "High": 25,
    "Medium": 10,
    "Low": 5,
}


def count_by_severity(findings):
    """Tally findings by severity level."""
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for finding in findings:
        severity = finding.get("severity", "Medium")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def grade_for_score(score):
    """Map a numeric score (0-100) to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def score_code(findings):
    """Rule-based security score (0-100) and letter grade from findings.

    Used as a deterministic fallback; the LLM agent assigns the primary score.
    """
    counts = count_by_severity(findings)
    deduction = sum(
        SEVERITY_WEIGHTS.get(sev, 10) * n for sev, n in counts.items()
    )
    score = max(0, 100 - deduction)

    return {
        "score": score,
        "grade": grade_for_score(score),
        "total_findings": len(findings),
        "counts": counts,
    }