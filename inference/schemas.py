from typing import Optional

from pydantic import BaseModel


class ProbabilityItem(BaseModel):
    label: str
    probability: float
    percent: str


class PredictionResponse(BaseModel):
    model_version: Optional[str] = None
    original_input: str
    detected_language: str
    translated_model_input: str
    scenario: str
    location: str
    image_caption: str
    image_caption_status: Optional[str] = None
    image_caption_model: Optional[str] = None
    image_caption_warning: Optional[str] = None
    final_model_input: str
    final_model_input_v1_2: Optional[str] = None
    predicted_hazard_category: str
    predicted_risk_level: str
    hazard_category: str
    sub_hazard: Optional[str] = None
    hazard_confidence: float
    hazard_confidence_percent: str
    risk_level: str
    risk_confidence: Optional[float] = None
    risk_confidence_percent: Optional[str] = None
    overall_confidence: float
    overall_confidence_percent: str
    overall_confidence_label: str
    hazard_probabilities: list[ProbabilityItem]
    risk_probabilities: list[ProbabilityItem] | list[dict]
    confidence_note: str
    urgency: str
    decision_support_recommendation: str
    recommendation: str
    suggested_follow_up_steps: list[str]
    safety_note: str
    manual_review_flag: Optional[bool] = None
    needs_more_information: Optional[bool] = None
    clarification_question: Optional[str] = None
    risk_method: Optional[str] = None
    corrective_action_plan: Optional[dict] = None
    severity_score: Optional[float] = None
    translation_strategy: Optional[str] = None
    translation_candidate_count: Optional[int] = None
    translation_candidate_scores: Optional[list[dict]] = None


class RecommendationBundle(BaseModel):
    hazard_summary: str
    sub_hazard: Optional[str] = None
    hazard_confidence: Optional[float] = None
    risk_method: Optional[str] = None
    image_caption_status: Optional[str] = None
    immediate_actions: list[str]
    prevention_actions: list[str]
    escalation_steps: list[str]
    follow_up_checks: list[str]
    location_notes: str
    recommendation_priority: str
    recommendation_summary: str
    decision_support_recommendation: Optional[str] = None
    corrective_action_plan: Optional[dict] = None
    manual_review_flag: Optional[bool] = None
    needs_more_information: Optional[bool] = None
    clarification_question: Optional[str] = None


class EnterprisePredictionResponse(BaseModel):
    model_version: str
    final_model_input: str
    image_support_mode: str
    image_captions: list[str]
    hazard_category: str
    sub_hazard: Optional[str] = None
    hazard_confidence: float
    hazard_confidence_percent: str
    risk_level: str
    risk_method: str
    severity_score: float
    confidence_state: str
    needs_more_info: bool
    needs_manual_review: bool
    manual_review_reason: str
    recommendations: RecommendationBundle
    recommendation_summary: str
    corrective_action_plan: Optional[dict] = None
    image_caption_status: Optional[str] = None
    image_caption_model: Optional[str] = None
    image_caption_warning: Optional[str] = None
    safety_note: str = "This AI output is intended for decision support only and should be reviewed by a competent person before workplace safety decisions are made."


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    load_error: str
    caption_model_ready: bool
    model_version: str = "v1_2_multimodal_sbert_svm_candidate"
    v1_1_model_loaded: bool = False
    v1_2_model_loaded: bool = False
