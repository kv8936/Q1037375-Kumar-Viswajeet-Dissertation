use crate::{
    models::PdfReportRequest, services::pdf_service::render_pdf_from_report, state::AppState,
};
use axum::{
    body::Body,
    extract::{Multipart, State},
    http::{header, HeaderValue, StatusCode},
    response::Response,
};
use base64::{engine::general_purpose::STANDARD, Engine as _};
use chrono::Utc;

fn infer_image_mime_type(file_name: Option<&str>, content_type: Option<&str>) -> String {
    if let Some(value) = content_type
        .map(str::trim)
        .filter(|value| !value.is_empty())
    {
        return value.to_string();
    }

    let ext = file_name
        .and_then(|name| name.rsplit('.').next())
        .map(|value| value.to_lowercase())
        .unwrap_or_default();

    match ext.as_str() {
        "png" => "image/png",
        "gif" => "image/gif",
        "webp" => "image/webp",
        "bmp" => "image/bmp",
        "tif" | "tiff" => "image/tiff",
        "svg" => "image/svg+xml",
        _ => "image/jpeg",
    }
    .to_string()
}

fn risk_badge(level: &str) -> String {
    match level.trim().to_lowercase().as_str() {
        "high" => "HIGH RISK".to_string(),
        "medium" => "MEDIUM RISK".to_string(),
        "low" => "LOW RISK".to_string(),
        _ => "RISK UNAVAILABLE".to_string(),
    }
}

fn image_to_data_url(image_bytes: &[u8], mime_type: &str) -> String {
    format!("data:{};base64,{}", mime_type, STANDARD.encode(image_bytes))
}

pub async fn result_pdf_handler(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Response, (StatusCode, String)> {
    let mut scenario = String::new();
    let mut location = String::new();
    let mut provider = String::new();
    let mut model_version = String::new();
    let mut original_input = String::new();
    let mut detected_language = String::new();
    let mut translated_model_input = String::new();
    let mut predicted_hazard_category = String::new();
    let mut predicted_risk_level = String::new();
    let mut sub_hazard = String::new();
    let mut hazard_confidence = String::new();
    let mut hazard_confidence_percent = String::new();
    let mut risk_confidence = String::new();
    let mut risk_confidence_percent = String::new();
    let mut overall_confidence = String::new();
    let mut overall_confidence_percent = String::new();
    let mut overall_confidence_label = String::new();
    let mut hazard_probabilities = String::new();
    let mut risk_probabilities = String::new();
    let mut confidence_note = String::new();
    let mut urgency = String::new();
    let mut risk_method = String::new();
    let mut image_caption_status = String::new();
    let mut image_caption_model = String::new();
    let mut image_caption_warning = String::new();
    let mut decision_support_recommendation = String::new();
    let mut recommendation = String::new();
    let mut suggested_follow_up_steps = String::new();
    let mut corrective_action_plan = String::new();
    let mut recommended_follow_up = String::new();
    let mut safety_note = String::new();
    let mut image_caption = String::new();
    let mut final_model_input = String::new();
    let mut image_bytes: Option<Vec<u8>> = None;
    let mut image_filename: Option<String> = None;
    let mut image_content_type: Option<String> = None;

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| (StatusCode::BAD_REQUEST, format!("multipart error: {}", e)))?
    {
        match field.name().as_deref() {
            Some("scenario") => {
                scenario = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read scenario: {}", e)))?;
            }
            Some("location") => {
                location = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read location: {}", e)))?;
            }
            Some("provider") => {
                provider = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read provider: {}", e)))?;
            }
            Some("model_version") => {
                model_version = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read model version: {}", e),
                    )
                })?;
            }
            Some("original_input") => {
                original_input = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read original input: {}", e),
                    )
                })?;
            }
            Some("detected_language") => {
                detected_language = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read detected language: {}", e),
                    )
                })?;
            }
            Some("translated_model_input") => {
                translated_model_input = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read translated model input: {}", e),
                    )
                })?;
            }
            Some("predicted_hazard_category") => {
                predicted_hazard_category = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read hazard category: {}", e),
                    )
                })?;
            }
            Some("predicted_risk_level") => {
                predicted_risk_level = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read risk level: {}", e)))?;
            }
            Some("sub_hazard") => {
                sub_hazard = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read sub hazard: {}", e)))?;
            }
            Some("hazard_confidence") => {
                hazard_confidence = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read hazard confidence: {}", e),
                    )
                })?;
            }
            Some("hazard_confidence_percent") => {
                hazard_confidence_percent = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read hazard confidence percent: {}", e),
                    )
                })?;
            }
            Some("risk_confidence") => {
                risk_confidence = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read risk confidence: {}", e),
                    )
                })?;
            }
            Some("risk_confidence_percent") => {
                risk_confidence_percent = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read risk confidence percent: {}", e),
                    )
                })?;
            }
            Some("overall_confidence") => {
                overall_confidence = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read overall confidence: {}", e),
                    )
                })?;
            }
            Some("overall_confidence_percent") => {
                overall_confidence_percent = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read overall confidence percent: {}", e),
                    )
                })?;
            }
            Some("overall_confidence_label") => {
                overall_confidence_label = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read overall confidence label: {}", e),
                    )
                })?;
            }
            Some("hazard_probabilities") => {
                hazard_probabilities = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read hazard probabilities: {}", e),
                    )
                })?;
            }
            Some("risk_probabilities") => {
                risk_probabilities = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read risk probabilities: {}", e),
                    )
                })?;
            }
            Some("confidence_note") => {
                confidence_note = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read confidence note: {}", e),
                    )
                })?;
            }
            Some("urgency") => {
                urgency = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read urgency: {}", e)))?;
            }
            Some("risk_method") => {
                risk_method = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read risk method: {}", e)))?;
            }
            Some("image_caption_status") => {
                image_caption_status = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read image caption status: {}", e),
                    )
                })?;
            }
            Some("image_caption_model") => {
                image_caption_model = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read image caption model: {}", e),
                    )
                })?;
            }
            Some("image_caption_warning") => {
                image_caption_warning = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read image caption warning: {}", e),
                    )
                })?;
            }
            Some("decision_support_recommendation") => {
                decision_support_recommendation = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read recommendation: {}", e),
                    )
                })?;
            }
            Some("recommendation") => {
                recommendation = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read alt recommendation: {}", e),
                    )
                })?;
            }
            Some("suggested_follow_up_steps") => {
                suggested_follow_up_steps = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read suggested follow-up steps: {}", e),
                    )
                })?;
            }
            Some("corrective_action_plan") => {
                corrective_action_plan = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read corrective action plan: {}", e),
                    )
                })?;
            }
            Some("recommended_follow_up") => {
                recommended_follow_up = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read recommended follow-up: {}", e),
                    )
                })?;
            }
            Some("safety_note") => {
                safety_note = field
                    .text()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read safety note: {}", e)))?;
            }
            Some("image_caption") => {
                image_caption = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read image caption: {}", e),
                    )
                })?;
            }
            Some("final_model_input") => {
                final_model_input = field.text().await.map_err(|e| {
                    (
                        StatusCode::BAD_REQUEST,
                        format!("read final model input: {}", e),
                    )
                })?;
            }
            Some("image") => {
                image_filename = field.file_name().map(|value| value.to_string());
                image_content_type = field.content_type().map(|value| value.to_string());
                let bytes = field
                    .bytes()
                    .await
                    .map_err(|e| (StatusCode::BAD_REQUEST, format!("read image bytes: {}", e)))?;
                image_bytes = Some(bytes.to_vec());
            }
            _ => {}
        }
    }

    if scenario.trim().is_empty() {
        return Err((StatusCode::BAD_REQUEST, "scenario is required".to_string()));
    }

    if model_version.trim().is_empty() {
        model_version = "v1_2_multimodal_sbert_svm_candidate".to_string();
    }

    let generated_at = Utc::now().to_rfc3339();
    let report_id = format!("HCR-{}", Utc::now().format("%Y%m%d%H%M%S"));
    let image_mime_type = if image_bytes.is_some() {
        Some(infer_image_mime_type(
            image_filename.as_deref(),
            image_content_type.as_deref(),
        ))
    } else {
        None
    };
    let image_data_url = match (&image_bytes, image_mime_type.as_deref()) {
        (Some(bytes), Some(mime)) => Some(image_to_data_url(bytes, mime)),
        _ => None,
    };

    let report = PdfReportRequest {
        report_id,
        generated_at,
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        model_version,
        provider,
        scenario,
        location,
        original_language: if detected_language.trim().is_empty() {
            "unknown".to_string()
        } else {
            detected_language
        },
        original_input,
        translated_model_input: if translated_model_input.trim().is_empty() {
            final_model_input.clone()
        } else {
            translated_model_input
        },
        final_model_input: if final_model_input.trim().is_empty() {
            None
        } else {
            Some(final_model_input)
        },
        image_included: image_data_url.is_some(),
        image_file_name: image_filename,
        image_mime_type,
        image_data_url,
        image_caption: if image_caption.trim().is_empty() {
            None
        } else {
            Some(image_caption)
        },
        image_caption_status: if image_caption_status.trim().is_empty() {
            None
        } else {
            Some(image_caption_status)
        },
        image_caption_model: if image_caption_model.trim().is_empty() {
            None
        } else {
            Some(image_caption_model)
        },
        image_caption_warning: if image_caption_warning.trim().is_empty() {
            None
        } else {
            Some(image_caption_warning)
        },
        predicted_hazard_category,
        predicted_risk_level: predicted_risk_level.clone(),
        sub_hazard: if sub_hazard.trim().is_empty() {
            None
        } else {
            Some(sub_hazard)
        },
        hazard_confidence: hazard_confidence.parse().ok(),
        hazard_confidence_percent: if hazard_confidence_percent.trim().is_empty() {
            None
        } else {
            Some(hazard_confidence_percent)
        },
        risk_confidence: risk_confidence.parse().ok(),
        risk_confidence_percent: if risk_confidence_percent.trim().is_empty() {
            None
        } else {
            Some(risk_confidence_percent)
        },
        overall_confidence: overall_confidence.parse().ok(),
        overall_confidence_percent: if overall_confidence_percent.trim().is_empty() {
            None
        } else {
            Some(overall_confidence_percent)
        },
        overall_confidence_label: if overall_confidence_label.trim().is_empty() {
            None
        } else {
            Some(overall_confidence_label)
        },
        hazard_probabilities: if hazard_probabilities.trim().is_empty() {
            None
        } else {
            serde_json::from_str(&hazard_probabilities).ok()
        },
        risk_probabilities: if risk_probabilities.trim().is_empty() {
            None
        } else {
            serde_json::from_str(&risk_probabilities).ok()
        },
        confidence_note: if confidence_note.trim().is_empty() {
            None
        } else {
            Some(confidence_note)
        },
        urgency: if urgency.trim().is_empty() {
            None
        } else {
            Some(urgency)
        },
        risk_method: if risk_method.trim().is_empty() {
            None
        } else {
            Some(risk_method)
        },
        risk_badge: risk_badge(&predicted_risk_level),
        recommendation: if recommendation.trim().is_empty() {
            None
        } else {
            Some(recommendation)
        },
        suggested_follow_up_steps: if suggested_follow_up_steps.trim().is_empty() {
            None
        } else {
            serde_json::from_str(&suggested_follow_up_steps).ok()
        },
        corrective_action_plan: if corrective_action_plan.trim().is_empty() {
            None
        } else {
            serde_json::from_str(&corrective_action_plan).ok()
        },
        decision_support_recommendation,
        recommended_follow_up,
        safety_note,
    };

    let pdf_bytes = render_pdf_from_report(&state.config.pdf_service_url, &report)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e))?;

    let mut response = Response::new(Body::from(pdf_bytes));
    response.headers_mut().insert(
        header::CONTENT_TYPE,
        HeaderValue::from_static("application/pdf"),
    );
    response.headers_mut().insert(
        header::CONTENT_DISPOSITION,
        HeaderValue::from_static("attachment; filename=hazard-chatbot-report.pdf"),
    );
    response.headers_mut().insert(
        header::CACHE_CONTROL,
        HeaderValue::from_static("no-store, max-age=0"),
    );

    Ok(response)
}
