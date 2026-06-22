use crate::{
    models::{ChatResponse, InferenceResponse},
    services::{database::log_chat_interaction, inference::forward_prediction_request},
    state::AppState,
};
use axum::{
    extract::{Multipart, State},
    http::StatusCode,
    Json,
};
use tracing::error;

fn scenario_has_enough_detail(value: &str, min_words: usize, min_chars: usize) -> bool {
    let trimmed = value.trim();
    let word_count = trimmed
        .split_whitespace()
        .filter(|part| !part.trim().is_empty())
        .count();
    let char_count = trimmed.chars().count();
    word_count >= min_words && char_count >= min_chars
}

#[axum::debug_handler]
pub async fn chat_handler(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<ChatResponse>, (StatusCode, String)> {
    let mut scenario: Option<String> = None;
    let mut location: Option<String> = None;
    let mut provider: Option<String> = None;
    let mut images: Vec<crate::services::inference::UploadedImage> = Vec::new();

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| (StatusCode::BAD_REQUEST, format!("multipart error: {}", e)))?
    {
        match field.name().as_deref() {
            Some("scenario") => {
                scenario = Some(
                    field
                        .text()
                        .await
                        .map_err(|e| (StatusCode::BAD_REQUEST, format!("read scenario: {}", e)))?,
                );
            }
            Some("location") => {
                location = Some(
                    field
                        .text()
                        .await
                        .map_err(|e| (StatusCode::BAD_REQUEST, format!("read location: {}", e)))?,
                );
            }
            Some("provider") => {
                provider = Some(
                    field
                        .text()
                        .await
                        .map_err(|e| (StatusCode::BAD_REQUEST, format!("read provider: {}", e)))?,
                );
            }
            Some("image") | Some("images") => {
                let filename = field.file_name().map(|value| value.to_string());
                let bytes = field
                    .bytes()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read image bytes: {}", e)))?;
                images.push(crate::services::inference::UploadedImage {
                    bytes: bytes.to_vec(),
                    filename,
                });
            }
            _ => {}
        }
    }

    let scenario_text = match scenario {
        Some(value) if !value.trim().is_empty() => value,
        _ => return Err((StatusCode::BAD_REQUEST, "scenario is required".to_string())),
    };

    if scenario_text.len() > state.config.max_scenario_chars {
        return Err((
            StatusCode::BAD_REQUEST,
            format!(
                "scenario must be at most {} characters",
                state.config.max_scenario_chars
            ),
        ));
    }

    if !scenario_has_enough_detail(
        &scenario_text,
        state.config.min_scenario_words,
        state.config.min_scenario_chars,
    ) {
        return Err((
            StatusCode::BAD_REQUEST,
            "Please enter a workplace hazard description with at least 3 meaningful words and 15 characters.".to_string(),
        ));
    }

    if let Some(location_text) = location.as_deref() {
        if location_text.len() > state.config.max_location_chars {
            return Err((
                StatusCode::BAD_REQUEST,
                format!(
                    "location must be at most {} characters",
                    state.config.max_location_chars
                ),
            ));
        }
    }

    if images.len() > state.config.max_images {
        return Err((
            StatusCode::BAD_REQUEST,
            format!("Up to {} images are allowed.", state.config.max_images),
        ));
    }

    let inference_url = state.config.inference_url.clone();
    let inference_timeout_secs = state.config.inference_timeout_secs;
    let scenario_for_forward = scenario_text.clone();
    let location_for_forward = location.clone();
    let images_for_forward = images.clone();

    let inference_result = forward_prediction_request(
        &inference_url,
        inference_timeout_secs,
        &scenario_for_forward,
        location_for_forward.as_deref(),
        images_for_forward,
    )
    .await;

    let inference: InferenceResponse = match inference_result {
        Ok(value) => value,
        Err(e) => return Err((StatusCode::BAD_GATEWAY, e)),
    };

    let mut logged = false;
    if state.config.enable_db_content_logging && !state.config.privacy_mode {
        if let Some(pool) = &state.pool {
            logged = log_chat_interaction(
                pool,
                &scenario_text,
                location.as_deref(),
                provider.as_deref(),
                !images.is_empty(),
                &inference,
            )
            .await;
        }
    }

    if inference.predicted_hazard_category.is_none() || inference.predicted_risk_level.is_none() {
        error!("inference service returned incomplete data");
    }

    let response = ChatResponse {
        model_version: inference.model_version,
        original_input: inference.original_input,
        detected_language: inference.detected_language,
        translated_model_input: inference.translated_model_input,
        final_model_input: inference
            .final_model_input
            .clone()
            .or(inference.final_model_input_v1_2.clone()),
        final_model_input_v1_2: inference.final_model_input_v1_2,
        predicted_hazard_category: inference
            .predicted_hazard_category
            .or(inference.hazard_category),
        predicted_risk_level: inference.predicted_risk_level.or(inference.risk_level),
        sub_hazard: inference.sub_hazard,
        manual_review_flag: inference.manual_review_flag,
        needs_more_information: inference.needs_more_information,
        clarification_question: inference.clarification_question,
        hazard_confidence: inference.hazard_confidence,
        hazard_confidence_percent: inference.hazard_confidence_percent,
        risk_confidence: inference.risk_confidence,
        risk_confidence_percent: inference.risk_confidence_percent,
        overall_confidence: inference.overall_confidence,
        overall_confidence_percent: inference.overall_confidence_percent,
        overall_confidence_label: inference.overall_confidence_label,
        hazard_probabilities: inference.hazard_probabilities,
        risk_probabilities: inference.risk_probabilities,
        confidence_note: inference.confidence_note,
        urgency: inference.urgency,
        risk_method: inference.risk_method,
        image_caption_status: inference.image_caption_status.clone(),
        image_caption_model: inference.image_caption_model,
        image_caption_warning: inference.image_caption_warning,
        decision_support_recommendation: inference.decision_support_recommendation,
        recommendation: inference.recommendation,
        suggested_follow_up_steps: inference.suggested_follow_up_steps,
        corrective_action_plan: inference.corrective_action_plan,
        safety_note: inference.safety_note,
        image_caption: inference.image_caption,
        logged,
    };

    Ok(Json(response))
}
