use crate::models::PdfReportRequest;
use reqwest::Client;
use std::time::Duration;
use tracing::{error, info};

pub async fn render_pdf_from_report(
    report_service_url: &str,
    report: &PdfReportRequest,
) -> Result<Vec<u8>, String> {
    let url = format!("{}/render-report", report_service_url.trim_end_matches('/'));
    info!(%url, "requesting PDF render");

    let client = Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(|e| format!("failed to build PDF client: {}", e))?;

    let response = client
        .post(&url)
        .json(report)
        .send()
        .await
        .map_err(|e| format!("pdf service request failed: {}", e))?;

    let status = response.status();
    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("failed to read PDF response: {}", e))?;

    if status.is_success() {
        Ok(bytes.to_vec())
    } else {
        let body = String::from_utf8_lossy(&bytes);
        error!(%status, %body, "pdf service returned error");
        Err(format!("pdf service returned {}: {}", status, body))
    }
}
