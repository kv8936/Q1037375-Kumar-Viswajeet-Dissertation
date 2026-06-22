use crate::models::InferenceResponse;
use sqlx::types::Json;
use sqlx::PgPool;
use tracing::error;

pub async fn ensure_schema(pool: &PgPool) {
    if let Err(e) =
        sqlx::query("ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS original_input TEXT")
            .execute(pool)
            .await
    {
        error!(%e, "failed to ensure chatbot_logs original_input column exists");
    }

    if let Err(e) =
        sqlx::query("ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS detected_language TEXT")
            .execute(pool)
            .await
    {
        error!(%e, "failed to ensure chatbot_logs detected_language column exists");
    }

    if let Err(e) =
        sqlx::query("ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS translated_model_input TEXT")
            .execute(pool)
            .await
    {
        error!(%e, "failed to ensure chatbot_logs translated_model_input column exists");
    }

    if let Err(e) = sqlx::query("ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS provider TEXT")
        .execute(pool)
        .await
    {
        error!(%e, "failed to ensure chatbot_logs provider column exists");
    }

    for statement in [
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS model_version TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS final_model_input_v1_2 TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS sub_hazard TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS hazard_confidence DOUBLE PRECISION",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS hazard_confidence_percent TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS risk_method TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS image_caption_status TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS manual_review_flag BOOLEAN",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS needs_more_information BOOLEAN",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS clarification_question TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS risk_confidence DOUBLE PRECISION",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS risk_confidence_percent TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS overall_confidence DOUBLE PRECISION",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS overall_confidence_percent TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS overall_confidence_label TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS hazard_probabilities TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS risk_probabilities TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS confidence_note TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS urgency TEXT",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS corrective_action_plan JSONB",
        "ALTER TABLE chatbot_logs ADD COLUMN IF NOT EXISTS recommendation TEXT",
    ] {
        if let Err(e) = sqlx::query(statement).execute(pool).await {
            error!(%e, statement, "failed to ensure chatbot_logs confidence column exists");
        }
    }
}

pub async fn log_chat_interaction(
    pool: &PgPool,
    scenario: &str,
    location: Option<&str>,
    provider: Option<&str>,
    image_uploaded: bool,
    inference: &InferenceResponse,
) -> bool {
    let original_input_bind = inference
        .original_input
        .clone()
        .unwrap_or_else(|| format!("Workplace scenario: {}", scenario));
    let detected_language_bind = inference.detected_language.clone();
    let translated_model_input_bind = inference.translated_model_input.clone();
    let scenario_bind = inference
        .scenario
        .clone()
        .unwrap_or_else(|| scenario.to_string());
    let location_bind = inference
        .location
        .clone()
        .or_else(|| location.map(|value| value.to_string()));
    let image_caption_bind = inference.image_caption.clone();
    let final_input_bind = inference.final_model_input.clone();
    let final_input_v1_2_bind = inference.final_model_input_v1_2.clone();
    let model_version_bind = inference.model_version.clone();
    let pred_hazard_bind = inference.predicted_hazard_category.clone();
    let pred_risk_bind = inference.predicted_risk_level.clone();
    let manual_review_flag_bind = inference.manual_review_flag;
    let needs_more_information_bind = inference.needs_more_information;
    let clarification_question_bind = inference.clarification_question.clone();
    let hazard_confidence_bind = inference.hazard_confidence;
    let hazard_confidence_percent_bind = inference.hazard_confidence_percent.clone();
    let risk_confidence_bind = inference.risk_confidence;
    let risk_confidence_percent_bind = inference.risk_confidence_percent.clone();
    let overall_confidence_bind = inference.overall_confidence;
    let overall_confidence_percent_bind = inference.overall_confidence_percent.clone();
    let overall_confidence_label_bind = inference.overall_confidence_label.clone();
    let hazard_probabilities_bind = inference
        .hazard_probabilities
        .clone()
        .map(|value| value.to_string());
    let risk_probabilities_bind = inference
        .risk_probabilities
        .clone()
        .map(|value| value.to_string());
    let confidence_note_bind = inference.confidence_note.clone();
    let urgency_bind = inference.urgency.clone();
    let decision_bind = inference.decision_support_recommendation.clone();
    let corrective_action_plan_bind = inference.corrective_action_plan.clone().map(Json);
    let recommendation_bind = inference.recommendation.clone();
    let provider_bind = provider.map(|value| value.to_string());

    let insert = sqlx::query(
        "INSERT INTO chatbot_logs (scenario, location, provider, image_uploaded, image_caption, original_input, detected_language, translated_model_input, final_model_input, final_model_input_v1_2, model_version, predicted_hazard_category, predicted_risk_level, manual_review_flag, needs_more_information, clarification_question, hazard_confidence, hazard_confidence_percent, risk_confidence, risk_confidence_percent, overall_confidence, overall_confidence_percent, overall_confidence_label, hazard_probabilities, risk_probabilities, confidence_note, urgency, decision_support_recommendation, recommendation, sub_hazard, risk_method, image_caption_status, corrective_action_plan) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33)",
    )
    .bind(scenario_bind)
    .bind(location_bind)
    .bind(provider_bind)
    .bind(image_uploaded)
    .bind(image_caption_bind)
    .bind(original_input_bind)
    .bind(detected_language_bind)
    .bind(translated_model_input_bind)
    .bind(final_input_bind)
    .bind(final_input_v1_2_bind)
    .bind(model_version_bind)
    .bind(pred_hazard_bind)
    .bind(pred_risk_bind)
    .bind(manual_review_flag_bind)
    .bind(needs_more_information_bind)
    .bind(clarification_question_bind)
    .bind(hazard_confidence_bind)
    .bind(hazard_confidence_percent_bind)
    .bind(risk_confidence_bind)
    .bind(risk_confidence_percent_bind)
    .bind(overall_confidence_bind)
    .bind(overall_confidence_percent_bind)
    .bind(overall_confidence_label_bind)
    .bind(hazard_probabilities_bind)
    .bind(risk_probabilities_bind)
    .bind(confidence_note_bind)
    .bind(urgency_bind)
    .bind(decision_bind)
    .bind(recommendation_bind)
    .bind(inference.sub_hazard.clone())
    .bind(inference.risk_method.clone())
    .bind(inference.image_caption_status.clone())
    .bind(corrective_action_plan_bind);

    match insert.execute(pool).await {
        Ok(_) => true,
        Err(e) => {
            error!(%e, "failed to insert log into database");
            false
        }
    }
}
