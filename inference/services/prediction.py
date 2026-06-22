from dataclasses import replace
from typing import Optional, Sequence

from PIL import Image

from config import CAPTION_MODEL_NAME, SAFETY_NOTE
from services.captioner import FALLBACK_IMAGE_CAPTION, CaptionMetadata, generate_caption_metadata
from services.models import LoadedModels
from services.translation import TranslationCandidate, normalize_chat_input
from services.v1_2_model_service import build_v1_2_final_model_input, load_v1_2_model, predict_v1_2, score_v1_2_final_model_input

TRANSLATION_CONFIDENCE_UPLIFT_THRESHOLD = 0.02

REC_MAP = {
    "low": "Routine corrective action is recommended. The hazard should be documented and resolved through normal workplace safety procedures.",
    "medium": "Corrective action should be planned and completed within a reasonable timeframe. The situation should be monitored until the hazard is controlled.",
    "high": "Immediate action is required. Restrict access to the area, notify the responsible safety officer, and arrange corrective action.",
}


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _confidence_label(value: float) -> str:
    if value >= 0.80:
        return "High confidence"
    if value >= 0.60:
        return "Medium confidence"
    return "Low confidence — human review strongly recommended"


def _top_probabilities(labels: Sequence[str], probabilities: Sequence[float], limit: int = 3) -> list[dict]:
    ranked = sorted(zip(labels, probabilities), key=lambda item: item[1], reverse=True)[:limit]
    return [
        {
            "label": str(label),
            "probability": float(probability),
            "percent": _format_percent(float(probability)),
        }
        for label, probability in ranked
    ]


def _predict_with_confidence(model, final_model_input: str) -> tuple[str, float, list[dict]]:
    predicted_class = str(model.predict([final_model_input])[0])
    confidence = 0.0
    probability_rows: list[dict] = []

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba([final_model_input])[0]
        classes = [str(label) for label in getattr(model, "classes_", [])]

        if classes and len(classes) == len(probabilities):
            probability_rows = _top_probabilities(classes, probabilities)
            predicted_index = classes.index(predicted_class) if predicted_class in classes else None
            if predicted_index is not None:
                confidence = float(probabilities[predicted_index])
        else:
            probability_rows = _top_probabilities([str(index) for index in range(len(probabilities))], probabilities)

    return predicted_class, confidence, probability_rows


def _extract_image_captions(
    image: Optional[Image.Image],
    images: Optional[Sequence[Image.Image]],
) -> list[CaptionMetadata]:
    if images:
        return [generate_caption_metadata(img) for img in images if img is not None]

    if image is not None:
        return [generate_caption_metadata(image)]

    return []


def _combine_image_captions(captions: Sequence[CaptionMetadata]) -> dict:
    if not captions:
        return {
            "image_caption": "",
            "image_caption_status": "Not available",
            "image_caption_model": CAPTION_MODEL_NAME,
            "image_caption_warning": "No image provided",
        }

    completed = [
        (index, item.image_caption)
        for index, item in enumerate(captions, start=1)
        if item.image_caption_status == "Completed" and item.image_caption.strip()
    ]
    warnings = [item.image_caption_warning for item in captions if item.image_caption_warning.strip()]
    model_name = next((item.image_caption_model for item in captions if item.image_caption_model.strip()), CAPTION_MODEL_NAME)

    if completed:
        caption_text = completed[0][1] if len(completed) == 1 else " | ".join(
            f"Image {index}: {text}" for index, text in completed
        )
        if len(completed) != len(captions):
            warnings.append("One or more uploaded images did not produce a reliable caption")
        return {
            "image_caption": caption_text,
            "image_caption_status": "Completed",
            "image_caption_model": model_name,
            "image_caption_warning": " ; ".join(dict.fromkeys(warnings)),
        }

    return {
        "image_caption": FALLBACK_IMAGE_CAPTION,
        "image_caption_status": "Failed",
        "image_caption_model": model_name,
        "image_caption_warning": " ; ".join(dict.fromkeys(warnings)) or "Caption generation failed validation",
    }



def build_final_model_input(scenario: str, location: Optional[str], image_caption: str) -> str:
    parts = [f"Workplace scenario: {scenario}"]
    if location and location.strip():
        parts.append(f"Location: {location.strip()}")
    if image_caption.strip():
        parts.append(f"Visual context from image caption: {image_caption.strip()}")
    return " | ".join(parts)


def _select_best_translation_candidate(
    normalized,
    caption_bundle: dict,
    caption_for_model: str,
) -> tuple[TranslationCandidate, list[dict]]:
    candidates = list(normalized.translation_candidates)
    if len(candidates) <= 1:
        candidate = candidates[0] if candidates else TranslationCandidate(
            scenario_for_model=normalized.scenario_for_model,
            location_for_model=normalized.location_for_model,
            translated_model_input=normalized.translated_model_input,
            strategy=normalized.translation_strategy,
        )
        return candidate, []

    image_caption_status = caption_bundle["image_caption_status"]
    researcher_visual_context = caption_for_model if image_caption_status == "Completed" else ""
    blip2_visual_caption = caption_for_model if image_caption_status == "Completed" else ""

    scored_candidates: list[tuple[TranslationCandidate, dict]] = []
    for candidate in candidates:
        final_model_input = build_v1_2_final_model_input(
            candidate.scenario_for_model,
            candidate.location_for_model,
            researcher_visual_context,
            blip2_visual_caption,
            image_caption_status=image_caption_status,
        )
        score = score_v1_2_final_model_input(final_model_input)
        scored_candidates.append(
            (
                candidate,
                {
                    "strategy": candidate.strategy,
                    "predicted_hazard_category": score.predicted_hazard_category,
                    "hazard_confidence": score.hazard_confidence,
                    "hazard_confidence_percent": _format_percent(score.hazard_confidence),
                },
            )
        )

    primary_candidate, primary_score = scored_candidates[0]
    agreeing = [item for item in scored_candidates if item[1]["predicted_hazard_category"] == primary_score["predicted_hazard_category"]]
    best_candidate, best_score = max(agreeing, key=lambda item: item[1]["hazard_confidence"])

    if best_score["hazard_confidence"] >= primary_score["hazard_confidence"] + TRANSLATION_CONFIDENCE_UPLIFT_THRESHOLD:
        return best_candidate, [score for _, score in scored_candidates]

    return primary_candidate, [score for _, score in scored_candidates]



def predict_from_inputs(
    models: LoadedModels,
    scenario: str,
    location: Optional[str],
    image: Optional[Image.Image],
    images: Optional[Sequence[Image.Image]] = None,
) -> dict:
    image_captions = _extract_image_captions(image, images)
    caption_bundle = _combine_image_captions(image_captions)
    caption_for_model = (
        caption_bundle["image_caption"]
        if caption_bundle["image_caption_status"] == "Completed"
        else (FALLBACK_IMAGE_CAPTION if caption_bundle["image_caption_status"] == "Failed" else "")
    )
    normalized = normalize_chat_input(scenario, location, caption_for_model)
    v12_model = load_v1_2_model()

    if v12_model.ready:
        selected_candidate, candidate_scores = _select_best_translation_candidate(
            normalized,
            caption_bundle,
            caption_for_model,
        )
        normalized = replace(
            normalized,
            scenario_for_model=selected_candidate.scenario_for_model,
            location_for_model=selected_candidate.location_for_model,
            translated_model_input=selected_candidate.translated_model_input,
            translation_strategy=selected_candidate.strategy,
        )

        result = predict_v1_2(
            scenario=normalized.scenario_for_model,
            location=normalized.location_for_model,
            image_caption=caption_bundle["image_caption"],
            image_caption_status=caption_bundle["image_caption_status"],
            image_caption_model=caption_bundle["image_caption_model"],
            image_caption_warning=caption_bundle["image_caption_warning"],
            researcher_visual_context=caption_for_model if caption_bundle["image_caption_status"] == "Completed" else "",
            blip2_visual_caption=caption_for_model if caption_bundle["image_caption_status"] == "Completed" else "",
            response_language=normalized.detected_language,
        )
        result.update(
            {
                "original_input": normalized.original_input,
                "detected_language": normalized.detected_language,
                "translated_model_input": result.get("final_model_input_v1_2", result.get("final_model_input", normalized.translated_model_input)),
                "scenario": scenario,
                "location": location or "",
                "image_caption": caption_bundle["image_caption"],
                "image_caption_status": caption_bundle["image_caption_status"],
                "image_caption_model": caption_bundle["image_caption_model"],
                "image_caption_warning": caption_bundle["image_caption_warning"],
                "final_model_input": result.get("final_model_input_v1_2", result.get("final_model_input", normalized.translated_model_input)),
                "predicted_hazard_category": result.get("predicted_hazard_category", result.get("hazard_category")),
                "predicted_risk_level": result.get("predicted_risk_level", result.get("risk_level")),
                "hazard_category": result.get("hazard_category", result.get("predicted_hazard_category")),
                "hazard_confidence": float(result.get("hazard_confidence") or 0.0),
                "hazard_confidence_percent": result.get("hazard_confidence_percent") or _format_percent(float(result.get("hazard_confidence") or 0.0)),
                "risk_level": result.get("risk_level", result.get("predicted_risk_level")),
                "risk_confidence": result.get("risk_confidence"),
                "risk_confidence_percent": result.get("risk_confidence_percent"),
                "overall_confidence": float(result.get("overall_confidence") or result.get("hazard_confidence") or 0.0),
                "overall_confidence_percent": result.get("overall_confidence_percent") or _format_percent(float(result.get("overall_confidence") or result.get("hazard_confidence") or 0.0)),
                "overall_confidence_label": result.get("overall_confidence_label") or _confidence_label(float(result.get("overall_confidence") or result.get("hazard_confidence") or 0.0)),
                "hazard_probabilities": result.get("hazard_probabilities", [])[:3] if isinstance(result.get("hazard_probabilities"), list) else result.get("hazard_probabilities"),
                "risk_probabilities": result.get("risk_probabilities", []),
                "confidence_note": result.get("confidence_note", ""),
                "urgency": result.get("urgency", ""),
                "decision_support_recommendation": result.get("decision_support_recommendation", result.get("recommendation", "")),
                "recommendation": result.get("recommendation", result.get("decision_support_recommendation", "")),
                "suggested_follow_up_steps": result.get("suggested_follow_up_steps", []),
                "safety_note": result.get("safety_note", SAFETY_NOTE),
                "manual_review_flag": result.get("manual_review_flag", False),
                "needs_more_information": result.get("needs_more_information", False),
                "clarification_question": result.get("clarification_question"),
                "model_version": result.get("model_version", "v1_2_multimodal_sbert_svm_candidate"),
                "severity_score": result.get("severity_score"),
                "final_model_input_v1_2": result.get("final_model_input_v1_2", result.get("final_model_input", "")),
                "translation_strategy": normalized.translation_strategy,
                "translation_candidate_count": len(normalized.translation_candidates),
                "translation_candidate_scores": candidate_scores,
            }
        )
        return result

    raise RuntimeError(f"v1.2 model not loaded: {v12_model.load_error}")
