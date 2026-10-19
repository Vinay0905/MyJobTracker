"""
DevRadar Extraction & Filtering Evaluation Harness
Computes Precision, Recall, F1, and MAE across curated ground-truth job postings.

Usage:
    python -m backend.extraction.evaluate
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List

from backend.extraction.pipeline import process_job_description

FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "eval_descriptions.json"

def run_evaluation() -> Dict[str, Any]:
    if not FIXTURE_PATH.exists():
        print(f"Error: Fixture file not found at {FIXTURE_PATH}")
        sys.exit(1)

    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])
    print(f"\n=======================================================")
    print(f"🚀 Running DevRadar Extraction Benchmark ({len(test_cases)} Test Cases)")
    print(f"=======================================================\n")

    # 1. Role Classification Metrics
    tp_role = 0
    fp_role = 0
    tn_role = 0
    fn_role = 0

    # 2. Skill Extraction Metrics
    total_expected_skills = 0
    total_extracted_skills = 0
    total_correct_skills = 0
    unexpected_skill_violations = 0

    # 3. YOE Metrics
    yoe_errors = []

    case_results = []

    for case in test_cases:
        cid = case["id"]
        title = case["title"]
        dept = case.get("department", "")
        desc = case["description"]
        expected_is_eng = case.get("is_engineering", True)

        processed = process_job_description(title=title, department=dept, raw_html_or_text=desc)
        actual_is_eng = processed["is_engineering"]

        # Role classification scoring
        if expected_is_eng and actual_is_eng:
            tp_role += 1
            role_verdict = "✅ TP (Accepted Eng)"
        elif not expected_is_eng and not actual_is_eng:
            tn_role += 1
            role_verdict = "✅ TN (Rejected Non-Eng)"
        elif not expected_is_eng and actual_is_eng:
            fp_role += 1
            role_verdict = "❌ FP (Should Reject)"
        else:
            fn_role += 1
            role_verdict = "❌ FN (Should Accept)"

        extracted_skills = {s["skill_id"] for s in processed["skills"]}
        expected_skills = set(case.get("expected_skills", []))
        unexpected_skills = set(case.get("unexpected_skills", []))

        # Skill scoring
        correct_for_case = extracted_skills.intersection(expected_skills)
        violations_for_case = extracted_skills.intersection(unexpected_skills)

        if expected_is_eng:
            total_expected_skills += len(expected_skills)
            total_extracted_skills += len(extracted_skills)
            total_correct_skills += len(correct_for_case)
            unexpected_skill_violations += len(violations_for_case)

        # YOE scoring
        expected_min_yoe = case.get("expected_min_yoe")
        actual_min_yoe = None
        if processed["experience"]:
            yoe_vals = [e["min_years"] for e in processed["experience"] if e["min_years"] is not None]
            if yoe_vals:
                actual_min_yoe = min(yoe_vals)

        if expected_min_yoe is not None and actual_min_yoe is not None:
            yoe_errors.append(abs(expected_min_yoe - actual_min_yoe))
        elif expected_min_yoe is not None and actual_min_yoe is None:
            yoe_errors.append(float(expected_min_yoe))

        case_results.append({
            "id": cid,
            "title": title,
            "role_verdict": role_verdict,
            "extracted_skills": sorted(list(extracted_skills)),
            "expected_skills": sorted(list(expected_skills)),
            "unexpected_violations": sorted(list(violations_for_case)),
            "expected_yoe": expected_min_yoe,
            "actual_yoe": actual_min_yoe,
        })

    # Calculations
    role_precision = tp_role / (tp_role + fp_role) if (tp_role + fp_role) > 0 else 1.0
    role_recall = tp_role / (tp_role + fn_role) if (tp_role + fn_role) > 0 else 1.0
    role_f1 = (2 * role_precision * role_recall) / (role_precision + role_recall) if (role_precision + role_recall) > 0 else 0.0

    skill_precision = total_correct_skills / total_extracted_skills if total_extracted_skills > 0 else 1.0
    skill_recall = total_correct_skills / total_expected_skills if total_expected_skills > 0 else 1.0
    skill_f1 = (2 * skill_precision * skill_recall) / (skill_precision + skill_recall) if (skill_precision + skill_recall) > 0 else 0.0

    mae_yoe = sum(yoe_errors) / len(yoe_errors) if yoe_errors else 0.0

    # Print Report
    print(f"{'Case ID':<25} | {'Role Verdict':<24} | {'Skills Correct / Extracted':<26} | {'YOE (Act/Exp)'}")
    print("-" * 95)
    for r in case_results:
        correct_count = len(set(r['extracted_skills']).intersection(set(r['expected_skills'])))
        skills_summary = f"{correct_count}/{len(r['expected_skills'])} (total: {len(r['extracted_skills'])})"
        yoe_summary = f"{r['actual_yoe']} / {r['expected_yoe']}"
        print(f"{r['id']:<25} | {r['role_verdict']:<24} | {skills_summary:<26} | {yoe_summary}")

    print("\n-------------------------------------------------------")
    print(f"📊 BENCHMARK SUMMARY & METRICS")
    print(f"-------------------------------------------------------")
    print(f"1. Role Gate Classification:")
    print(f"   - Precision: {role_precision*100:.1f}% (TP={tp_role}, FP={fp_role})")
    print(f"   - Recall:    {role_recall*100:.1f}% (FN={fn_role}, TN={tn_role})")
    print(f"   - F1 Score:  {role_f1*100:.1f}%\n")
    print(f"2. Skill Extraction Accuracy:")
    print(f"   - Precision: {skill_precision*100:.1f}% (Correct: {total_correct_skills}, Total Extracted: {total_extracted_skills})")
    print(f"   - Recall:    {skill_recall*100:.1f}% (Expected: {total_expected_skills})")
    print(f"   - F1 Score:  {skill_f1*100:.1f}%")
    print(f"   - Unexpected Violations (Negation / False Positives): {unexpected_skill_violations}\n")
    print(f"3. Experience Requirement Parsing:")
    print(f"   - Mean Absolute Error (MAE): {mae_yoe:.2f} years across {len(yoe_errors)} evaluations")
    print(f"=======================================================\n")

    passed = (role_precision >= 0.90) and (role_recall >= 0.90) and (skill_precision >= 0.85) and (skill_recall >= 0.85)
    if passed:
        print("🎉 STATUS: PASSED - Meets rigorous production extraction thresholds.\n")
    else:
        print("⚠️ STATUS: FAILED - Fails to meet required accuracy thresholds.\n")

    return {
        "passed": passed,
        "role_precision": role_precision,
        "role_recall": role_recall,
        "role_f1": role_f1,
        "skill_precision": skill_precision,
        "skill_recall": skill_recall,
        "skill_f1": skill_f1,
        "unexpected_skill_violations": unexpected_skill_violations,
        "mae_yoe": mae_yoe,
    }

if __name__ == "__main__":
    results = run_evaluation()
    sys.exit(0 if results["passed"] else 1)
