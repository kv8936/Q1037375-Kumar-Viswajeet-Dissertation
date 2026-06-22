"""
V1.1 Candidate Hazard Model Service

Handles model loading and prediction using the v1.1 candidate model.
Implements manual review rules based on confidence and fire/exit-route ambiguity.
"""

import json
from typing import Any, Optional, Sequence

import joblib

from config import HAZARD_V1_1_CONFIG_PATH, HAZARD_V1_1_MODEL_PATH
from services.recommendation_service import build_recommendations


# Fire/exit-route and obstruction keywords
FIRE_EXIT_TERMS = {
    "fire escape",
    "fire exit",
    "emergency exit",
    "emergency route",
    "exit route",
    "escape route",
}

OBSTRUCTION_TERMS = {
    "obstructed",
    "blocked",
    "blocking",
    "boxes",
    "clutter",
    "stored",
    "storage",
    "partially blocking",
}


class HazardModelV1_1:
    """V1.1 Candidate Hazard Model loader and predictor."""

    def __init__(self):
        self.model: Optional[Any] = None
        self.config: Optional[dict] = None
        self.ready: bool = False
        self.load_error: str = ""

    def load(self) -> bool:
        """Load model and config from disk.
        
        Returns:
            bool: True if both model and config loaded successfully.
        """
        try:
            if not HAZARD_V1_1_MODEL_PATH.exists():
                raise FileNotFoundError(f"Model file not found: {HAZARD_V1_1_MODEL_PATH}")
            if not HAZARD_V1_1_CONFIG_PATH.exists():
                raise FileNotFoundError(f"Config file not found: {HAZARD_V1_1_CONFIG_PATH}")

            self.model = joblib.load(HAZARD_V1_1_MODEL_PATH)
            with open(HAZARD_V1_1_CONFIG_PATH, "r") as f:
                self.config = json.load(f)

            self.ready = True
            self.load_error = ""
            return True
        except Exception as exc:
            self.ready = False
            self.load_error = str(exc)
            return False

    def _get_hazard_confidence(self, model_input: str) -> tuple[str, float]:
        """Predict hazard category and get confidence.
        
        Args:
            model_input: Combined input string from scenario, location, caption.
            
        Returns:
            tuple: (predicted_hazard_category, confidence_float)
        """
        if not self.ready:
            raise RuntimeError("Model not loaded. Call load() first.")

        predicted_class = str(self.model.predict([model_input])[0])
        confidence = 0.0

        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba([model_input])[0]
            classes = [str(label) for label in getattr(self.model, "classes_", [])]

            if classes and len(classes) == len(probabilities):
                try:
                    predicted_index = classes.index(predicted_class)
                    confidence = float(probabilities[predicted_index])
                except ValueError:
                    pass

        return predicted_class, confidence

    def _detect_fire_obstruction_ambiguity(self, model_input: str) -> bool:
        """Detect if model_input contains fire/exit-route + obstruction keywords.
        
        Args:
            model_input: Combined input string.
            
        Returns:
            bool: True if both fire_exit_terms and obstruction_terms detected.
        """
        model_input_lower = model_input.lower()

        has_fire_exit = any(term in model_input_lower for term in FIRE_EXIT_TERMS)
        has_obstruction = any(term in model_input_lower for term in OBSTRUCTION_TERMS)

        return has_fire_exit and has_obstruction

    def _compute_risk_level(self, severity_score: float) -> str:
        """Compute risk level based on severity_score.
        
        Args:
            severity_score: Numeric severity score.
            
        Returns:
            str: "Low", "Medium", or "High"
        """
        if severity_score <= 3:
            return "Low"
        elif severity_score <= 6:
            return "Medium"
        else:
            return "High"

    def _build_final_model_input(
        self,
        model_input: str,
        location: Optional[str] = None,
        image_captions: Optional[Sequence[str]] = None,
    ) -> str:
        parts = []

        cleaned_input = model_input.strip()
        if cleaned_input:
            if cleaned_input.lower().startswith("workplace scenario:"):
                parts.append(cleaned_input)
            else:
                parts.append(f"Workplace scenario: {cleaned_input}")

        if location and location.strip():
            parts.append(f"Location: {location.strip()}")

        if image_captions:
            captions = [caption.strip() for caption in image_captions if caption and caption.strip()]
            if captions:
                caption_text = " | ".join(
                    f"Image {index}: {caption}" for index, caption in enumerate(captions, start=1)
                )
                parts.append(f"Image-supported text inference captions: {caption_text}")

        return " | ".join(parts) if parts else cleaned_input

    def evaluate_confidence_policy(
        self,
        hazard_confidence: float,
        fire_obstruction_ambiguity: bool,
    ) -> dict:
        """Classify uncertainty and review state using enterprise policy."""
        reasons = []
        needs_more_info = False
        needs_manual_review = False

        if hazard_confidence < 0.25:
            confidence_state = "need_more_info"
            needs_more_info = True
            needs_manual_review = True
            reasons.append(f"hazard_confidence {hazard_confidence:.4f} < 0.25")
        elif hazard_confidence < 0.40:
            confidence_state = "manual_review"
            needs_manual_review = True
            reasons.append(f"hazard_confidence {hazard_confidence:.4f} < 0.40")
        else:
            confidence_state = "normal"

        if fire_obstruction_ambiguity:
            needs_manual_review = True
            if confidence_state == "normal":
                confidence_state = "manual_review"
            reasons.append("fire/exit-route obstruction ambiguity detected")

        if needs_more_info:
            reasons.append("Please provide more detail and clearer images.")

        manual_review_reason = " AND ".join(reasons)

        return {
            "confidence_state": confidence_state,
            "needs_more_info": needs_more_info,
            "needs_manual_review": needs_manual_review,
            "manual_review_reason": manual_review_reason,
        }

    def predict_v1_1_candidate(
        self,
        model_input: str,
        severity_score: float,
        location: Optional[str] = None,
        image_captions: Optional[Sequence[str]] = None,
    ) -> dict:
        """Predict hazard and generate full output with manual review flag.
        
        Args:
            model_input: Combined input from scenario, location, image caption.
            severity_score: Numeric severity score (0-10).
            
        Returns:
            dict: Prediction output including hazard category, risk level, confidence, and manual_review flag.
        """
        if not self.ready:
            raise RuntimeError("Model not loaded. Call load() first.")

        final_model_input = self._build_final_model_input(model_input, location=location, image_captions=image_captions)

        # Get hazard prediction and confidence
        hazard_category, hazard_confidence = self._get_hazard_confidence(final_model_input)

        # Compute risk level from severity_score
        risk_level = self._compute_risk_level(severity_score)

        # Detect fire/exit-route obstruction ambiguity
        fire_obstruction_ambiguity = self._detect_fire_obstruction_ambiguity(final_model_input)

        policy = self.evaluate_confidence_policy(hazard_confidence, fire_obstruction_ambiguity)
        image_support_mode = "image_supported_text_inference" if image_captions else "text_only"
        recommendations = build_recommendations(
            hazard_category=hazard_category,
            risk_level=risk_level,
            severity_score=float(severity_score),
            scenario=model_input,
            location=location,
            needs_manual_review=policy["needs_manual_review"],
            needs_more_info=policy["needs_more_info"],
        )

        return {
            "model_version": str((self.config or {}).get("version", "v1_1_candidate")),
            "final_model_input": final_model_input,
            "image_support_mode": image_support_mode,
            "image_captions": [caption for caption in (image_captions or []) if caption and caption.strip()],
            "hazard_category": hazard_category,
            "hazard_confidence": float(hazard_confidence),
            "hazard_confidence_percent": f"{float(hazard_confidence) * 100:.2f}%",
            "risk_level": risk_level,
            "risk_method": "deterministic severity_score rule",
            "severity_score": float(severity_score),
            **policy,
            "recommendations": recommendations,
            "recommendation_summary": recommendations.get("recommendation_summary", ""),
        }


# Singleton instance
_instance: Optional[HazardModelV1_1] = None


def get_hazard_model_v1_1() -> HazardModelV1_1:
    """Get or create the HazardModelV1_1 singleton instance."""
    global _instance
    if _instance is None:
        _instance = HazardModelV1_1()
    return _instance


def load_hazard_model_v1_1() -> HazardModelV1_1:
    """Load the v1.1 candidate model.
    
    Returns:
        HazardModelV1_1: Loaded and ready model instance, or with load_error set.
    """
    model = get_hazard_model_v1_1()
    model.load()
    return model
