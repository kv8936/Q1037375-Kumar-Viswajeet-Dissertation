"""Regression tests for the v1.2 multimodal hazard classifier."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from services.captioner import FALLBACK_IMAGE_CAPTION, validate_generated_caption
from services.prediction import predict_from_inputs
from services.models import load_models
from services.translation import TranslationError, build_translation_candidates, normalize_chat_input
from services.v1_2_model_service import load_v1_2_model, predict_v1_2


MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "v1_2_multimodal_sbert_svm_candidate" / "final_export_v1_2_multimodal_sbert_svm_candidate_20260610_180546"
MODEL_PATH = MODEL_DIR / "hazard_classifier_sbert_linear_svm.joblib"
LABELS_PATH = MODEL_DIR / "hazard_labels.json"
RULE_PATH = MODEL_DIR / "manual_review_rule.json"


def main() -> int:
    print("Test 1: v1.2 artifact files exist...")
    assert MODEL_PATH.exists(), f"Missing model: {MODEL_PATH}"
    assert LABELS_PATH.exists(), f"Missing labels: {LABELS_PATH}"
    assert RULE_PATH.exists(), f"Missing manual review rule: {RULE_PATH}"
    print("  ✓ files present")

    print("\nTest 2: v1.2 model loads...")
    model = load_v1_2_model()
    assert model.ready, model.load_error
    print(f"  ✓ model ready: {model.model_card.get('model_name', 'unknown') if model.model_card else 'unknown'}")

    print("\nTest 3: text-only scenario marks caption as not available...")
    sample = "A fire extinguisher access point is blocked by stored cardboard boxes near an emergency exit."
    text_only = predict_v1_2(
        scenario=sample,
        location="emergency exit corridor",
        image_caption="",
        image_caption_status="Not available",
        severity_score=6.0,
        researcher_visual_context="",
        blip2_visual_caption="",
    )
    assert text_only["image_caption_status"] == "Not available", text_only
    assert "Visual context:" not in text_only["final_model_input_v1_2"], text_only
    assert "Image evidence was uploaded" not in text_only["recommendation"], text_only
    print("  ✓ text-only caption status ok")

    print("\nTest 4: fire extinguisher access ambiguity triggers review...")
    sample = "A fire extinguisher access point is blocked by stored cardboard boxes near an emergency exit."
    result = predict_v1_2(
        scenario=sample,
        location="emergency exit corridor",
        image_caption="Cardboard boxes stacked in front of the extinguisher cabinet",
        image_caption_status="Completed",
        image_caption_model="Salesforce/blip2-opt-2.7b",
        severity_score=6.0,
        researcher_visual_context="Cardboard boxes near fire safety equipment",
        blip2_visual_caption="Cardboard boxes stacked in front of the extinguisher cabinet",
    )
    assert result["manual_review_flag"] is True, result
    assert result["hazard_confidence"] is not None, result
    assert result["risk_level"] in {"Medium", "High"}, result
    assert result["image_caption_status"] == "Completed", result
    print(f"  ✓ hazard={result['hazard_category']} confidence={result['hazard_confidence_percent']} review={result['manual_review_flag']}")

    print("\nTest 5: low-quality caption falls back safely...")
    failed = validate_generated_caption("s")
    assert failed.image_caption_status == "Failed", failed
    assert failed.image_caption == FALLBACK_IMAGE_CAPTION, failed
    print("  ✓ caption validation fallback ok")

    print("\nTest 6: deterministic risk rule works for severity 8...")
    high = predict_v1_2(
        scenario=sample,
        location="emergency exit corridor",
        image_caption="Cardboard boxes stacked in front of the extinguisher cabinet",
        image_caption_status="Completed",
        image_caption_model="Salesforce/blip2-opt-2.7b",
        severity_score=8.0,
        researcher_visual_context="Cardboard boxes near fire safety equipment",
        blip2_visual_caption="Cardboard boxes stacked in front of the extinguisher cabinet",
    )
    assert high["predicted_risk_level"] == "High", high
    print(f"  ✓ severity=8 -> {high['predicted_risk_level']}")

    print("\nTest 7: German input is translated to English before classification...")
    normalized = normalize_chat_input(
        "Nasser Boden in der Nähe des Büroeingangs",
        "Büroeingang",
        "",
    )
    assert normalized.detected_language == "de", normalized
    assert "wet floor" in normalized.scenario_for_model.lower(), normalized.scenario_for_model
    assert "office entrance" in normalized.location_for_model.lower(), normalized.location_for_model
    assert normalized.translation_candidate_count if hasattr(normalized, "translation_candidate_count") else True
    print(f"  ✓ translated scenario={normalized.scenario_for_model}")

    print("\nTest 8: fallback translation path remains resilient...")

    class FailingTranslator:
        def translate_to_english(self, text: str) -> str:
            raise TranslationError("forced failure")

    fallback = normalize_chat_input(
        "Nasser Boden in der Nähe des Büroeingangs",
        "Büroeingang",
        "",
        translator=FailingTranslator(),
    )
    assert fallback.scenario_for_model == "Nasser Boden in der Nähe des Büroeingangs", fallback
    assert fallback.location_for_model == "Büroeingang", fallback
    print("  ✓ fallback preserves service availability on translation failure")

    print("\nTest 9: German translation candidates are generated and deduplicated...")
    candidates = build_translation_candidates(
        "Nasser Boden in der Nähe des Büroeingangs",
        "Büroeingang",
        "",
    )
    assert len(candidates) >= 1, candidates
    assert all(candidate.strategy for candidate in candidates), candidates
    print(f"  ✓ candidate strategies={[candidate.strategy for candidate in candidates]}")

    print("\nTest 10: English and German variants produce the same v1.2 prediction...")
    models = load_models()
    english = predict_from_inputs(
        models,
        "wet floor near office entrance",
        "office entrance",
        None,
        images=None,
    )
    german = predict_from_inputs(
        models,
        "Nasser Boden in der Nähe des Büroeingangs",
        "Büroeingang",
        None,
        images=None,
    )
    assert english["predicted_hazard_category"] == german["predicted_hazard_category"], (english, german)
    assert english["predicted_risk_level"] == german["predicted_risk_level"], (english, german)
    assert german["detected_language"] == "de", german
    assert english["image_caption_status"] == "Not available", english
    assert german.get("translation_strategy") in {"hf", "fallback", "identity", "translated"}, german
    assert german.get("translation_candidate_count", 0) >= 1, german
    print(f"  ✓ english={english['predicted_hazard_category']}/{english['predicted_risk_level']}")
    print(f"  ✓ german={german['predicted_hazard_category']}/{german['predicted_risk_level']}")
    print(f"  ✓ german translation strategy={german.get('translation_strategy')} candidates={german.get('translation_candidate_count')}")

    print("\n✓ ALL v1.2 TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
