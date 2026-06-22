"""Smoke tests for v1.3 multilingual accuracy candidate model.

Run with:
    cd inference
    python test_v1_3_model.py

Expected results:
    oil spill on floor              → Slip/Trip Hazard
    fluchtweg blockiert             → Obstruction Hazard
    schlechte Beleuchtung / blind spot → Visibility Hazard
    clean corridor no hazard        → no_hazard
    chemical containers near walkway → manual_review
"""

import sys
import os

# Allow running from inference/ or project root
sys.path.insert(0, os.path.dirname(__file__))

from services.v1_3_model_service import load_v1_3_model, predict_v1_3

SMOKE_TESTS = [
    {
        "input": "oil spill on floor",
        "expected_category": "Slip/Trip Hazard",
        "expected_manual_review": None,  # guardrail fires → manual_review=True is correct per policy
    },
    {
        "input": "fluchtweg blockiert",
        "expected_category": "Obstruction Hazard",
        "expected_manual_review": None,
    },
    {
        "input": "schlechte Beleuchtung / blind spot",
        "expected_category": "Visibility Hazard",
        "expected_manual_review": None,
    },
    {
        "input": "clean corridor no hazard",
        "expected_category": "no_hazard",
        "expected_manual_review": False,
    },
    {
        "input": "chemical containers near walkway",
        "expected_category": None,  # any category acceptable
        "expected_manual_review": True,
    },
]


def _run_smoke_tests() -> None:
    print("Loading v1.3 model...")
    bundle = load_v1_3_model()
    if not bundle.ready:
        print(f"FAIL — model not loaded: {bundle.load_error}")
        sys.exit(1)
    print(f"Model ready: {bundle.stage1_model is not None}, encoder: {bundle.encoder is not None}\n")

    passed = 0
    failed = 0

    for case in SMOKE_TESTS:
        scenario = case["input"]
        result = predict_v1_3(
            scenario=scenario,
            location=None,
            image_caption="",
            image_caption_status="Not available",
        )

        category = result["hazard_category"]
        manual_review = result["manual_review_flag"]
        stage1 = result["stage1_label"]
        stage2 = result.get("stage2_label", "")
        guardrail = result.get("guardrail_applied", False)
        triggers = result.get("manual_review_triggers", [])
        risk = result["risk_level"]
        score = result.get("severity_score", 0)

        expected_cat = case["expected_category"]
        expected_mr = case["expected_manual_review"]

        cat_ok = (expected_cat is None) or (category == expected_cat)
        mr_ok = (expected_mr is None) or (manual_review == expected_mr)

        status = "PASS" if (cat_ok and mr_ok) else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1

        print(f"[{status}] '{scenario}'")
        print(f"       stage1={stage1}  stage2={stage2 or '-'}  guardrail={guardrail}")
        print(f"       category={category}  risk={risk}  severity={score}")
        print(f"       manual_review={manual_review}  triggers={triggers}")
        if not cat_ok:
            print(f"       !! expected category: {expected_cat}")
        if not mr_ok:
            print(f"       !! expected manual_review: {expected_mr}")
        print()

    print(f"Results: {passed}/{len(SMOKE_TESTS)} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    _run_smoke_tests()
