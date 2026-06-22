"""Enterprise regression tests for the v1.1 candidate inference path."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from services.hazard_model_service import load_hazard_model_v1_1
from services.recommendation_service import build_recommendations


MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "v1_1_candidate"
MODEL_PATH = MODEL_DIR / "hazard_category_model_v1_1_candidate.joblib"
CONFIG_PATH = MODEL_DIR / "hybrid_model_config_v1_1_candidate.json"


def main() -> int:
    print("Test 1: model and config files exist...")
    assert MODEL_PATH.exists(), f"Missing model: {MODEL_PATH}"
    assert CONFIG_PATH.exists(), f"Missing config: {CONFIG_PATH}"
    print("  ✓ files present")

    print("\nTest 2: model loads...")
    model = load_hazard_model_v1_1()
    assert model.ready, model.load_error
    print("  ✓ model ready")

    print("\nTest 3: image-supported text inference builds final input...")
    sample_input = "Loose wiring is visible near an electrical panel during maintenance work."
    result = model.predict_v1_1_candidate(
        model_input=sample_input,
        severity_score=8.0,
        location="maintenance area",
        image_captions=["Loose wiring near the panel", "Wet surface close to the power unit"],
    )
    assert result["risk_level"] == "High", result
    assert result["image_support_mode"] == "image_supported_text_inference", result
    assert "Image-supported text inference captions" in result["final_model_input"], result["final_model_input"]
    print(f"  ✓ hazard={result['hazard_category']} risk={result['risk_level']}")

    print("\nTest 4: confidence policy tiers...")
    need_more = model.evaluate_confidence_policy(0.20, False)
    assert need_more["confidence_state"] == "need_more_info", need_more
    assert need_more["needs_more_info"] is True, need_more
    assert need_more["needs_manual_review"] is True, need_more

    review = model.evaluate_confidence_policy(0.33, False)
    assert review["confidence_state"] == "manual_review", review
    assert review["needs_manual_review"] is True, review

    normal_with_ambiguity = model.evaluate_confidence_policy(0.55, True)
    assert normal_with_ambiguity["confidence_state"] == "manual_review", normal_with_ambiguity
    assert "fire/exit-route obstruction ambiguity detected" in normal_with_ambiguity["manual_review_reason"], normal_with_ambiguity
    print("  ✓ confidence states pass")

    print("\nTest 5: recommendations are hazard-specific and risk-aware...")
    rec = build_recommendations(
        hazard_category="Electrical Hazard",
        risk_level="High",
        severity_score=8.0,
        scenario=sample_input,
        location="maintenance area",
        needs_manual_review=True,
        needs_more_info=False,
    )
    assert any("qualified electrician" in item.lower() for item in rec["escalation_steps"]), rec
    assert any("stop work" in item.lower() for item in rec["immediate_actions"]), rec
    assert "maintenance area" in rec["location_notes"], rec["location_notes"]
    print("  ✓ recommendations pass")

    print("\n✓ ALL ENTERPRISE TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
