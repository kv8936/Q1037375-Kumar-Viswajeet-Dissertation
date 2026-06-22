use crate::models::InferenceResponse;
use reqwest::header::CONTENT_TYPE;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, warn};

#[derive(Clone, Debug)]
pub struct UploadedImage {
    pub bytes: Vec<u8>,
    pub filename: Option<String>,
}

fn build_multipart_body(
    scenario: &str,
    location: Option<&str>,
    images: &[UploadedImage],
) -> (Vec<u8>, String) {
    let boundary = "----hazardbot-boundary";
    let mut body: Vec<u8> = Vec::new();

    macro_rules! push_str {
        ($s:expr) => {
            body.extend_from_slice($s.as_bytes())
        };
    }

    push_str!("--");
    push_str!(boundary);
    push_str!("\r\n");
    push_str!("Content-Disposition: form-data; name=\"scenario\"\r\n\r\n");
    push_str!(scenario);
    push_str!("\r\n");

    if let Some(location) = location.filter(|value| !value.trim().is_empty()) {
        push_str!("--");
        push_str!(boundary);
        push_str!("\r\n");
        push_str!("Content-Disposition: form-data; name=\"location\"\r\n\r\n");
        push_str!(location);
        push_str!("\r\n");
    }

    for (index, image) in images.iter().enumerate() {
        let filename = image
            .filename
            .as_deref()
            .filter(|value| !value.trim().is_empty())
            .map(|value| value.to_string())
            .unwrap_or_else(|| format!("upload-{}.jpg", index + 1));
        push_str!("--");
        push_str!(boundary);
        push_str!("\r\n");
        push_str!(&format!(
            "Content-Disposition: form-data; name=\"images\"; filename=\"{}\"\r\n",
            filename
        ));
        push_str!("Content-Type: application/octet-stream\r\n\r\n");
        body.extend_from_slice(&image.bytes);
        push_str!("\r\n");
    }

    push_str!("--");
    push_str!(boundary);
    push_str!("--\r\n");

    (body, format!("multipart/form-data; boundary={}", boundary))
}

pub async fn forward_prediction_request(
    inference_url: &str,
    timeout_secs: u64,
    scenario: &str,
    location: Option<&str>,
    images: Vec<UploadedImage>,
) -> Result<InferenceResponse, String> {
    let url = format!("{}/predict", inference_url.trim_end_matches('/'));
    let (body, content_type) = build_multipart_body(scenario, location, &images);

    info!(%url, "forwarding to inference service");

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(timeout_secs))
        .build();

    let client = client.map_err(|e| format!("failed to build inference client: {}", e))?;

    let max_attempts = 3;
    for attempt in 1..=max_attempts {
        let response = client
            .post(&url)
            .header(CONTENT_TYPE, &content_type)
            .header("User-Agent", "hazard-chatbot-backend/1.0")
            .body(body.clone())
            .send()
            .await;

        match response {
            Ok(resp) => {
                let status = resp.status();
                let text = resp
                    .text()
                    .await
                    .map_err(|e| format!("failed to read inference response: {}", e))?;

                if status.is_success() {
                    return serde_json::from_str::<InferenceResponse>(&text)
                        .map_err(|e| format!("invalid inference response: {}", e));
                }

                return Err(format!("inference service returned {}: {}", status, text));
            }
            Err(e) => {
                if attempt < max_attempts && (e.is_connect() || e.is_timeout() || e.is_request()) {
                    warn!(attempt, max_attempts, error = %e, "inference request failed, retrying");
                    sleep(Duration::from_millis(250 * attempt as u64)).await;
                    continue;
                }

                return Err(format!("inference request failed: {}", e));
            }
        }
    }

    Err("inference request failed after retries".to_string())
}
