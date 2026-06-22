"""V1.3 Multilingual Accuracy Candidate — Two-stage hazard inference service.

Pipeline:
  1. Build embedding input with "passage: " prefix + BLIP-2 caption if available.
  2. Encode with intfloat/multilingual-e5-large (1024-dim, normalized).
  3. Stage 1 hazard gate  →  hazard_present / no_hazard / unclear_insufficient_evidence.
  4. Stage 2 category (only when hazard_present)  →  6-class SVM.
  5. Enterprise guardrails  →  3 deterministic pattern overrides.
  6. Deterministic risk rule  →  severity_score → Low / Medium / High.
  7. Manual review policy  →  union of all trigger conditions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

from config import (
    SAFETY_NOTE,
    V1_3_GUARDRAIL_CONFIG_PATH,
    V1_3_POLICY_CONFIG_PATH,
    V1_3_RISK_RULE_PATH,
    V1_3_RUNTIME_CONFIG_PATH,
    V1_3_STAGE1_CONFIG_PATH,
    V1_3_STAGE1_ENCODER_PATH,
    V1_3_STAGE1_MODEL_PATH,
    V1_3_STAGE2_CONFIG_PATH,
    V1_3_STAGE2_ENCODER_PATH,
    V1_3_STAGE2_MODEL_PATH,
)
from services.recommendation_service import build_recommendations

# ── Constants ─────────────────────────────────────────────────────────────────

MODEL_VERSION = "v1_3_multilingual_accuracy_candidate"
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"
EMBEDDING_PREFIX = "passage: "

STAGE1_CONF_THRESHOLD = 0.75   # below → manual review
STAGE2_CONF_THRESHOLD = 0.65   # below → manual review

STAGE1_HAZARD_PRESENT = "hazard_present"
STAGE1_NO_HAZARD = "no_hazard"
STAGE1_UNCLEAR = "unclear_insufficient_evidence"

SEVERITY_DEFAULTS: dict[str, float] = {
    "Fire Hazard": 9.0,
    "Electrical Hazard": 8.0,
    "Obstruction Hazard": 6.0,
    "Slip/Trip Hazard": 5.0,
    "Visibility Hazard": 4.0,
    "Ergonomic Hazard": 3.0,
}

CLARIFICATION_QUESTION = (
    "Please confirm the exact hazard location, what object or substance is involved, "
    "whether staff are frequently exposed, whether any emergency route or exit is blocked, "
    "whether there is immediate danger, and whether the condition is temporary or persistent."
)

# Enterprise guardrail pattern sets (applied to raw lowercased input)
_OBSTRUCTION_PATTERNS = re.compile(
    r"\b(blocked?|obstruct\w*|fluchtweg|notausgang|emergency\s+exit|fire\s+exit|"
    r"escape\s+route|exit\s+route|walkway|stairwell|corridor\s+block\w*|"
    r"gangway\s+block\w*)\b",
    re.IGNORECASE,
)
_SLIP_PATTERNS = re.compile(
    r"\b(oil\s+spill|spill\w*|liquid\s+on|wet\s+floor|pfütze|ausgerutscht|"
    r"rutsch\w*|slip\w*|nass\w*\s+boden|contamination)\b",
    re.IGNORECASE,
)
_VISIBILITY_PATTERNS = re.compile(
    r"\b(blind\s+spot|poor\s+visib\w*|schlechte\s+beleuchtung|dunkel\w*|"
    r"unübersichtlich|unuebersichtlich|dark\s+area|no\s+light\w*)\b",
    re.IGNORECASE,
)
# Chemical container ambiguity trigger
_CHEMICAL_PATTERNS = re.compile(
    r"\b(chemical\s+container|gefahrstoff\w*|hazardous\s+material|chemical\s+drum|"
    r"chemical\s+bottle|chemical\s+near\w*|chemical\s+storage)\b",
    re.IGNORECASE,
)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class V13ModelBundle:
    stage1_model: Any | None = None
    stage1_encoder: Any | None = None
    stage2_model: Any | None = None
    stage2_encoder: Any | None = None
    encoder: SentenceTransformer | None = None
    runtime_config: dict = field(default_factory=dict)
    guardrail_config: dict = field(default_factory=dict)
    policy_config: dict = field(default_factory=dict)
    risk_rule: dict = field(default_factory=dict)
    stage1_config: dict = field(default_factory=dict)
    stage2_config: dict = field(default_factory=dict)
    load_error: str = ""

    @property
    def ready(self) -> bool:
        return (
            self.stage1_model is not None
            and self.stage2_model is not None
            and self.encoder is not None
        )


_INSTANCE: V13ModelBundle | None = None


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_json(path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_v1_3_model() -> V13ModelBundle:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = V13ModelBundle()
    return _INSTANCE


def load_v1_3_model() -> V13ModelBundle:
    bundle = get_v1_3_model()
    if bundle.ready:
        return bundle

    try:
        for path in (V1_3_STAGE1_MODEL_PATH, V1_3_STAGE2_MODEL_PATH):
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")

        bundle.stage1_model = joblib.load(V1_3_STAGE1_MODEL_PATH)
        bundle.stage1_encoder = joblib.load(V1_3_STAGE1_ENCODER_PATH) if V1_3_STAGE1_ENCODER_PATH.exists() else None
        bundle.stage2_model = joblib.load(V1_3_STAGE2_MODEL_PATH)
        bundle.stage2_encoder = joblib.load(V1_3_STAGE2_ENCODER_PATH) if V1_3_STAGE2_ENCODER_PATH.exists() else None

        bundle.runtime_config = _load_json(V1_3_RUNTIME_CONFIG_PATH) if V1_3_RUNTIME_CONFIG_PATH.exists() else {}
        bundle.guardrail_config = _load_json(V1_3_GUARDRAIL_CONFIG_PATH) if V1_3_GUARDRAIL_CONFIG_PATH.exists() else {}
        bundle.policy_config = _load_json(V1_3_POLICY_CONFIG_PATH) if V1_3_POLICY_CONFIG_PATH.exists() else {}
        bundle.risk_rule = _load_json(V1_3_RISK_RULE_PATH) if V1_3_RISK_RULE_PATH.exists() else {}
        bundle.stage1_config = _load_json(V1_3_STAGE1_CONFIG_PATH) if V1_3_STAGE1_CONFIG_PATH.exists() else {}
        bundle.stage2_config = _load_json(V1_3_STAGE2_CONFIG_PATH) if V1_3_STAGE2_CONFIG_PATH.exists() else {}

        bundle.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        bundle.load_error = ""

    except Exception as exc:
        bundle.stage1_model = None
        bundle.stage2_model = None
        bundle.encoder = None
        bundle.load_error = str(exc)

    return bundle


# ── Internal helpers ──────────────────────────────────────────────────────────

def _clean(text: Optional[str]) -> str:
    return (text or "").strip()


def _build_embedding_input(user_text: str, image_caption: str) -> str:
    text = _clean(user_text)
    caption = _clean(image_caption)
    if caption:
        core = f"User report: {text}. Image caption: {caption}."
    else:
        core = f"User report: {text}."
    return f"{EMBEDDING_PREFIX}{core}"


def _encode(bundle: V13ModelBundle, text: str) -> np.ndarray:
    return bundle.encoder.encode(
        [text],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def _top_probabilities(labels: Sequence[str], proba: Sequence[float], limit: int = 3) -> list[dict]:
    ranked = sorted(zip(labels, proba), key=lambda x: x[1], reverse=True)[:limit]
    return [
        {"label": str(lbl), "probability": float(p), "percent": f"{float(p) * 100:.2f}%"}
        for lbl, p in ranked
    ]


def _predict_with_proba(model, embedding: np.ndarray, encoder=None) -> tuple[str, float, list[dict]]:
    """Predict with probabilities; decode integer class index via LabelEncoder if provided."""
    predicted_raw = model.predict(embedding)[0]

    if encoder is not None:
        try:
            predicted = str(encoder.inverse_transform([predicted_raw])[0])
        except Exception:
            predicted = str(predicted_raw)
    else:
        predicted = str(predicted_raw)

    confidence = 0.0
    proba_rows: list[dict] = []

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(embedding)[0]
        if encoder is not None:
            try:
                raw_classes = list(getattr(model, "classes_", range(len(proba))))
                classes = [str(encoder.inverse_transform([c])[0]) for c in raw_classes]
            except Exception:
                classes = [str(c) for c in getattr(model, "classes_", [])]
        else:
            classes = [str(c) for c in getattr(model, "classes_", [])]

        if classes and len(classes) == len(proba):
            proba_rows = _top_probabilities(classes, proba)
            if predicted in classes:
                confidence = float(proba[classes.index(predicted)])
            else:
                confidence = float(max(proba))
        else:
            confidence = float(max(proba))
            proba_rows = _top_probabilities([str(i) for i in range(len(proba))], proba)

    return predicted, confidence, proba_rows


def _apply_guardrails(raw_input: str, category: str) -> tuple[str, bool]:
    """Return (final_category, guardrail_applied)."""
    low = raw_input.lower()

    if _OBSTRUCTION_PATTERNS.search(low):
        return "Obstruction Hazard", True

    if _SLIP_PATTERNS.search(low):
        return "Slip/Trip Hazard", True

    if _VISIBILITY_PATTERNS.search(low):
        return "Visibility Hazard", True

    return category, False


def _compute_risk_level(severity_score: float) -> str:
    if severity_score <= 0:
        return "none"
    if severity_score <= 3:
        return "Low"
    if severity_score <= 6:
        return "Medium"
    return "High"


def _confidence_label(confidence: float, language: str = "en") -> str:
    de = language.strip().lower().startswith("de")
    if confidence >= 0.80:
        return "Hohe Konfidenz" if de else "High confidence"
    if confidence >= 0.60:
        return "Mittlere Konfidenz" if de else "Medium confidence"
    return (
        "Niedrige Konfidenz – menschliche Prüfung dringend empfohlen"
        if de
        else "Low confidence — human review strongly recommended"
    )


# ── Main prediction function ──────────────────────────────────────────────────

def predict_v1_3(
    scenario: str,
    location: Optional[str],
    image_caption: str,
    image_caption_status: str = "Not available",
    image_caption_model: str = "",
    image_caption_warning: str = "",
    response_language: str = "en",
) -> dict:
    bundle = load_v1_3_model()
    if not bundle.ready:
        raise RuntimeError(f"v1.3 model not loaded: {bundle.load_error}")

    scenario_clean = _clean(scenario)
    location_clean = _clean(location)
    caption_status = _clean(image_caption_status) or (
        "Completed" if _clean(image_caption) else "Not available"
    )
    effective_caption = _clean(image_caption) if caption_status == "Completed" else ""

    # Build input string + embedding
    embedding_input = _build_embedding_input(scenario_clean, effective_caption)
    embedding = _encode(bundle, embedding_input)

    # ── Stage 1: Hazard gate ──────────────────────────────────────────────────
    stage1_label, stage1_conf, stage1_proba = _predict_with_proba(bundle.stage1_model, embedding, bundle.stage1_encoder)

    manual_review_triggers: list[str] = []

    if stage1_label == STAGE1_NO_HAZARD:
        severity_score = 0.0
        hazard_category = "no_hazard"
        risk_level = "none"
        manual_review_flag = False
        stage2_label = ""
        stage2_conf = 0.0
        stage2_proba: list[dict] = []
        guardrail_applied = False
    elif stage1_label == STAGE1_UNCLEAR:
        severity_score = 0.0
        hazard_category = "unclear_insufficient_evidence"
        risk_level = "manual_review"
        manual_review_flag = True
        manual_review_triggers.append("unclear_insufficient_evidence")
        stage2_label = ""
        stage2_conf = 0.0
        stage2_proba = []
        guardrail_applied = False
    else:
        # Stage 1 returned hazard_present
        if stage1_conf < STAGE1_CONF_THRESHOLD:
            manual_review_triggers.append(f"low_stage1_confidence ({stage1_conf:.4f} < {STAGE1_CONF_THRESHOLD})")

        # ── Stage 2: Category classifier ─────────────────────────────────────
        stage2_label, stage2_conf, stage2_proba = _predict_with_proba(bundle.stage2_model, embedding, bundle.stage2_encoder)

        if stage2_conf < STAGE2_CONF_THRESHOLD:
            manual_review_triggers.append(f"low_stage2_confidence ({stage2_conf:.4f} < {STAGE2_CONF_THRESHOLD})")

        # ── Enterprise guardrails ─────────────────────────────────────────────
        raw_input = f"{scenario_clean} {location_clean} {effective_caption}"
        stage2_label, guardrail_applied = _apply_guardrails(raw_input, stage2_label)
        if guardrail_applied:
            manual_review_triggers.append("rule_based_guardrail_applied")

        # Chemical container ambiguity
        if _CHEMICAL_PATTERNS.search(raw_input.lower()):
            manual_review_triggers.append("ambiguous_chemical_container_context")

        hazard_category = stage2_label
        severity_score = SEVERITY_DEFAULTS.get(hazard_category, 5.0)
        risk_level = _compute_risk_level(severity_score)
        manual_review_flag = len(manual_review_triggers) > 0

    # Weak/failed caption trigger
    if caption_status == "Failed" or (caption_status not in ("Completed", "Not available")):
        manual_review_triggers.append("weak_or_filtered_image_caption")
        manual_review_flag = True

    manual_review_reason = " | ".join(manual_review_triggers) if manual_review_triggers else ""
    needs_more_information = manual_review_flag
    clarification_question = CLARIFICATION_QUESTION if needs_more_information else None
    confidence_note = _confidence_label(stage2_conf if stage1_label == STAGE1_HAZARD_PRESENT else stage1_conf, response_language)
    if manual_review_flag:
        suffix = "Manuelle Prüfung erforderlich." if response_language.strip().lower().startswith("de") else "Manual review required."
        confidence_note = f"{confidence_note}. {suffix}"

    recommendations = build_recommendations(
        hazard_category=hazard_category,
        risk_level=risk_level if risk_level not in ("none", "manual_review") else "medium",
        severity_score=severity_score,
        scenario=scenario_clean,
        location=location_clean or None,
        needs_manual_review=manual_review_flag,
        needs_more_info=needs_more_information,
        hazard_confidence=stage2_conf if stage1_label == STAGE1_HAZARD_PRESENT else stage1_conf,
        image_caption=effective_caption,
        language=response_language,
        image_caption_status=caption_status,
    )

    image_support_mode = "image_supported_text_inference" if caption_status == "Completed" else "text_only"

    return {
        "model_version": MODEL_VERSION,
        "original_input": f"Workplace scenario: {scenario_clean} | Location: {location_clean}".strip(),
        "detected_language": response_language,
        "translated_model_input": embedding_input,
        "scenario": scenario_clean,
        "location": location_clean,
        "image_caption": _clean(image_caption),
        "image_caption_status": caption_status,
        "image_caption_model": _clean(image_caption_model),
        "image_caption_warning": _clean(image_caption_warning),
        "final_model_input": embedding_input,
        "final_model_input_v1_3": embedding_input,
        "image_support_mode": image_support_mode,
        # Stage outputs
        "stage1_label": stage1_label,
        "stage1_confidence": float(stage1_conf),
        "stage1_probabilities": stage1_proba,
        "stage2_label": stage2_label,
        "stage2_confidence": float(stage2_conf),
        "stage2_probabilities": stage2_proba,
        "guardrail_applied": guardrail_applied,
        # Unified fields (API-compatible with v1.2)
        "predicted_hazard_category": hazard_category,
        "predicted_risk_level": risk_level,
        "hazard_category": hazard_category,
        "sub_hazard": recommendations.get("sub_hazard", ""),
        "hazard_confidence": float(stage2_conf if stage1_label == STAGE1_HAZARD_PRESENT else stage1_conf),
        "hazard_confidence_percent": f"{(stage2_conf if stage1_label == STAGE1_HAZARD_PRESENT else stage1_conf) * 100:.2f}%",
        "risk_level": risk_level,
        "risk_confidence": None,
        "risk_confidence_percent": None,
        "overall_confidence": float(stage2_conf if stage1_label == STAGE1_HAZARD_PRESENT else stage1_conf),
        "overall_confidence_percent": f"{(stage2_conf if stage1_label == STAGE1_HAZARD_PRESENT else stage1_conf) * 100:.2f}%",
        "overall_confidence_label": confidence_note,
        "hazard_probabilities": stage2_proba if stage1_label == STAGE1_HAZARD_PRESENT else stage1_proba,
        "risk_probabilities": [],
        "confidence_note": confidence_note,
        "urgency": risk_level,
        "severity_score": float(severity_score),
        "risk_method": "deterministic_severity_score_rule",
        "decision_support_recommendation": recommendations["recommendation_summary"],
        "recommendation": recommendations["recommendation_summary"],
        "suggested_follow_up_steps": recommendations["follow_up_checks"],
        "safety_note": SAFETY_NOTE,
        "manual_review_flag": manual_review_flag,
        "manual_review_reason": manual_review_reason,
        "manual_review_triggers": manual_review_triggers,
        "needs_more_information": needs_more_information,
        "clarification_question": clarification_question,
        "needs_manual_review": manual_review_flag,
        "corrective_action_plan": recommendations.get("corrective_action_plan", {}),
        "recommendations": recommendations,
    }
