"""v1.2 multimodal hazard classifier service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

from config import (
    SAFETY_NOTE,
    V1_2_LABELS_PATH,
    V1_2_MANUAL_REVIEW_RULE_PATH,
    V1_2_MODEL_CARD_PATH,
    V1_2_MODEL_PATH,
    V1_2_RISK_RULE_PATH,
)
from services.recommendation_service import build_recommendations


DEFAULT_MODEL_VERSION = "v1_2_multimodal_sbert_svm_candidate"
SBERT_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

FIRE_EXIT_TERMS = {
    "fire escape",
    "fire exit",
    "emergency exit",
    "emergency route",
    "exit route",
    "escape route",
    "fire route",
    "fire extinguisher",
    "fire extinguisher access",
    "fire extinguisher access point",
    "evacuation route",
    "corridor",
    "doorway",
    "stairwell",
}

OBSTRUCTION_TERMS = {
    "obstructed",
    "blocked",
    "blocking",
    "boxes",
    "cardboard boxes",
    "clutter",
    "stored",
    "storage",
    "stored items",
    "partially blocking",
}

CLARIFICATION_QUESTION = (
    "Please confirm the exact hazard location, what object or substance is involved, whether staff are frequently exposed, "
    "whether any emergency route, exit, or fire equipment is blocked, whether there is immediate danger, and whether the condition is temporary or persistent."
)

SEVERITY_FALLBACKS = {
    "Electrical Hazard": 8.0,
    "Fire Hazard": 9.0,
    "Obstruction Hazard": 6.0,
    "Slip/Trip Hazard": 5.0,
    "Visibility Hazard": 4.0,
    "Ergonomic Hazard": 3.0,
}


@dataclass
class V12ModelBundle:
    model: Any | None = None
    encoder: SentenceTransformer | None = None
    labels: list[str] | None = None
    risk_rule: dict | None = None
    manual_review_rule: dict | None = None
    model_card: dict | None = None
    load_error: str = ""

    @property
    def ready(self) -> bool:
        return self.model is not None and self.encoder is not None


_INSTANCE: V12ModelBundle | None = None


@dataclass(frozen=True)
class HazardCandidateScore:
    final_model_input: str
    predicted_hazard_category: str
    hazard_confidence: float
    hazard_probabilities: list[dict]


def _clean(text: Optional[str]) -> str:
    return (text or "").strip()


def _load_json(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_v1_2_model() -> V12ModelBundle:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = V12ModelBundle()
    return _INSTANCE


def load_v1_2_model() -> V12ModelBundle:
    model = get_v1_2_model()
    if model.ready:
        return model

    try:
        if not V1_2_MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found: {V1_2_MODEL_PATH}")

        model.model = joblib.load(V1_2_MODEL_PATH)
        model.labels = _load_json(V1_2_LABELS_PATH) if V1_2_LABELS_PATH.exists() else []
        model.risk_rule = _load_json(V1_2_RISK_RULE_PATH) if V1_2_RISK_RULE_PATH.exists() else {}
        model.manual_review_rule = _load_json(V1_2_MANUAL_REVIEW_RULE_PATH) if V1_2_MANUAL_REVIEW_RULE_PATH.exists() else {}
        model.model_card = _load_json(V1_2_MODEL_CARD_PATH) if V1_2_MODEL_CARD_PATH.exists() else {}
        model.encoder = SentenceTransformer(SBERT_MODEL_NAME)
        model.load_error = ""
        return model
    except Exception as exc:  # pragma: no cover - startup failure path
        model.model = None
        model.encoder = None
        model.load_error = str(exc)
        return model


def _build_final_model_input(
    scenario: str,
    location: Optional[str],
    researcher_visual_context: str,
    blip2_visual_caption: str,
    image_caption_status: str = "Not available",
) -> str:
    scenario_text = _clean(scenario)
    location_text = _clean(location)
    researcher_text = _clean(researcher_visual_context)
    blip2_text = _clean(blip2_visual_caption)
    caption_status = _clean(image_caption_status) or "Not available"

    parts = [
        f"Workplace scenario: {scenario_text}",
        f"Location: {location_text}" if location_text else "Location: ",
    ]

    if caption_status == "Completed" and blip2_text:
        parts.append(f"Researcher visual context: {researcher_text or blip2_text}")
        parts.append(f"BLIP-2 visual caption: {blip2_text}")
        parts.append(f"Visual context: {blip2_text}")
    elif caption_status == "Failed":
        parts.append("Visual context: No reliable image caption generated")

    return " | ".join(parts)


def _compute_risk_level(severity_score: Optional[float], hazard_category: str) -> tuple[str, float, str]:
    score = severity_score if severity_score is not None else SEVERITY_FALLBACKS.get(hazard_category, 5.0)
    if score <= 3:
        return "Low", float(score), "deterministic severity_score rule"
    if score <= 6:
        return "Medium", float(score), "deterministic severity_score rule"
    return "High", float(score), "deterministic severity_score rule"


def _manual_review_threshold(bundle: V12ModelBundle) -> float:
    try:
        value = float((bundle.manual_review_rule or {}).get("confidence_threshold", 0.40))
        return value
    except Exception:
        return 0.40


def _detect_fire_exit_obstruction_ambiguity(text: str) -> bool:
    lowered = text.lower()
    has_fire = any(term in lowered for term in FIRE_EXIT_TERMS)
    has_obstruction = any(term in lowered for term in OBSTRUCTION_TERMS)
    return has_fire and has_obstruction


def _looks_unclear(image_caption: str, blip2_caption: str) -> bool:
    combined = f"{_clean(image_caption)} | {_clean(blip2_caption)}".lower()
    if not combined.strip():
        return True
    return any(term in combined for term in {"caption unavailable", "unclear", "unknown", "not available", "no reliable image caption generated"})


def _top_probabilities(labels: Sequence[str], probabilities: Sequence[float], limit: int = 3) -> list[dict]:
    ranked = sorted(zip(labels, probabilities), key=lambda item: item[1], reverse=True)[:limit]
    return [
        {
            "label": str(label),
            "probability": float(probability),
            "percent": f"{float(probability) * 100:.2f}%",
        }
        for label, probability in ranked
    ]


def _confidence_label(confidence: float, language: str = "en") -> str:
    de = language.strip().lower().startswith("de")
    if confidence >= 0.8:
        return "Hohe Konfidenz" if de else "High confidence"
    if confidence >= 0.6:
        return "Mittlere Konfidenz" if de else "Medium confidence"
    return "Niedrige Konfidenz – menschliche Prüfung dringend empfohlen" if de else "Low confidence — human review strongly recommended"


def build_v1_2_final_model_input(
    scenario: str,
    location: Optional[str],
    researcher_visual_context: str,
    blip2_visual_caption: str,
    image_caption_status: str = "Not available",
) -> str:
    return _build_final_model_input(
        scenario,
        location,
        researcher_visual_context,
        blip2_visual_caption,
        image_caption_status=image_caption_status,
    )


def score_v1_2_final_model_input(final_model_input: str) -> HazardCandidateScore:
    bundle = load_v1_2_model()
    if not bundle.ready:
        raise RuntimeError(f"v1.2 model not loaded: {bundle.load_error}")

    encoded = bundle.encoder.encode([final_model_input], normalize_embeddings=True, convert_to_numpy=True)
    embeddings = np.asarray(encoded)

    predicted_hazard_category = str(bundle.model.predict(embeddings)[0])
    hazard_confidence = 0.0
    hazard_probabilities: list[dict] = []

    if hasattr(bundle.model, "predict_proba"):
        proba = bundle.model.predict_proba(embeddings)[0]
        classes = [str(label) for label in getattr(bundle.model, "classes_", [])] or [str(label) for label in (bundle.labels or [])]
        if classes and len(classes) == len(proba):
            hazard_probabilities = _top_probabilities(classes, proba)
            if predicted_hazard_category in classes:
                hazard_confidence = float(proba[classes.index(predicted_hazard_category)])
            else:
                hazard_confidence = float(max(proba))
        else:
            hazard_confidence = float(max(proba))
            hazard_probabilities = _top_probabilities([str(i) for i in range(len(proba))], proba)

    return HazardCandidateScore(
        final_model_input=final_model_input,
        predicted_hazard_category=predicted_hazard_category,
        hazard_confidence=hazard_confidence,
        hazard_probabilities=hazard_probabilities,
    )


def predict_v1_2(
    scenario: str,
    location: Optional[str],
    image_caption: str,
    severity_score: Optional[float] = None,
    researcher_visual_context: Optional[str] = None,
    blip2_visual_caption: str = "",
    response_language: str = "en",
    image_caption_status: str = "Not available",
    image_caption_model: str = "",
    image_caption_warning: str = "",
) -> dict:
    bundle = load_v1_2_model()
    if not bundle.ready:
        raise RuntimeError(f"v1.2 model not loaded: {bundle.load_error}")

    normalized_caption_status = _clean(image_caption_status) or ("Completed" if _clean(image_caption) else "Not available")
    effective_image_caption = _clean(image_caption) if normalized_caption_status == "Completed" else ""
    researcher_context = researcher_visual_context if researcher_visual_context is not None else effective_image_caption
    effective_blip2_caption = _clean(blip2_visual_caption) if normalized_caption_status == "Completed" else ""
    final_model_input = _build_final_model_input(
        scenario,
        location,
        researcher_context or "",
        effective_blip2_caption,
        image_caption_status=normalized_caption_status,
    )
    candidate_score = score_v1_2_final_model_input(final_model_input)
    predicted_hazard_category = candidate_score.predicted_hazard_category
    hazard_confidence = candidate_score.hazard_confidence
    hazard_probabilities = candidate_score.hazard_probabilities

    fire_obstruction_ambiguity = _detect_fire_exit_obstruction_ambiguity(final_model_input)
    unclear_image_context = normalized_caption_status == "Failed" or _looks_unclear(researcher_context or effective_image_caption, effective_blip2_caption)
    review_threshold = _manual_review_threshold(bundle)
    manual_review_flag = hazard_confidence < review_threshold or fire_obstruction_ambiguity or unclear_image_context
    manual_review_reason_parts = []
    if hazard_confidence < review_threshold:
        manual_review_reason_parts.append(f"hazard_confidence {hazard_confidence:.4f} < {review_threshold:.2f}")
    if fire_obstruction_ambiguity:
        manual_review_reason_parts.append("fire/exit-route obstruction ambiguity detected")
    if unclear_image_context:
        manual_review_reason_parts.append("image captions are unclear or unavailable")
    manual_review_reason = " AND ".join(manual_review_reason_parts)

    needs_more_information = hazard_confidence < review_threshold or unclear_image_context
    clarification_question = CLARIFICATION_QUESTION if needs_more_information else None

    risk_level, resolved_severity_score, risk_method = _compute_risk_level(severity_score, predicted_hazard_category)
    recommendations = build_recommendations(
        hazard_category=predicted_hazard_category,
        risk_level=risk_level,
        severity_score=resolved_severity_score,
        scenario=scenario,
        location=location,
        needs_manual_review=manual_review_flag,
        needs_more_info=hazard_confidence < 0.25,
        hazard_confidence=hazard_confidence,
        image_caption=effective_image_caption,
        language=response_language,
        image_caption_status=normalized_caption_status,
    )

    image_support_mode = "image_supported_text_inference" if normalized_caption_status == "Completed" else "text_only"
    confidence_note = _confidence_label(hazard_confidence, response_language)
    if manual_review_flag:
        confidence_note = f"{confidence_note}. {'Manuelle Prüfung erforderlich.' if response_language.strip().lower().startswith('de') else 'Manual review required.'}"

    return {
        "model_version": DEFAULT_MODEL_VERSION,
        "original_input": f"Workplace scenario: {_clean(scenario)} | Location: {_clean(location)}".strip(),
        "detected_language": response_language,
        "translated_model_input": final_model_input,
        "scenario": _clean(scenario),
        "location": _clean(location),
        "image_caption": _clean(image_caption),
        "image_caption_status": normalized_caption_status,
        "image_caption_model": _clean(image_caption_model),
        "image_caption_warning": _clean(image_caption_warning),
        "final_model_input": final_model_input,
        "image_support_mode": image_support_mode,
        "predicted_hazard_category": predicted_hazard_category,
        "predicted_risk_level": risk_level,
        "hazard_category": predicted_hazard_category,
        "sub_hazard": recommendations.get("sub_hazard", ""),
        "hazard_confidence": float(hazard_confidence),
        "hazard_confidence_percent": f"{hazard_confidence * 100:.2f}%",
        "risk_level": risk_level,
        "risk_confidence": None,
        "risk_confidence_percent": None,
        "overall_confidence": float(hazard_confidence),
        "overall_confidence_percent": f"{hazard_confidence * 100:.2f}%",
        "overall_confidence_label": confidence_note,
        "hazard_probabilities": hazard_probabilities,
        "risk_probabilities": [],
        "confidence_note": confidence_note,
        "urgency": risk_level,
        "decision_support_recommendation": recommendations["recommendation_summary"],
        "recommendation": recommendations["recommendation_summary"],
        "suggested_follow_up_steps": recommendations["follow_up_checks"],
        "safety_note": SAFETY_NOTE,
        "manual_review_flag": manual_review_flag,
        "needs_more_information": needs_more_information,
        "clarification_question": clarification_question,
        "needs_manual_review": manual_review_flag,
        "manual_review_reason": manual_review_reason,
        "severity_score": resolved_severity_score,
        "risk_method": risk_method,
        "image_caption_status": recommendations.get("image_caption_status", normalized_caption_status),
        "corrective_action_plan": recommendations.get("corrective_action_plan", {}),
        "recommendations": recommendations,
        "final_model_input_v1_2": final_model_input,
    }
