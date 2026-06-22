use std::{env, net::SocketAddr};

#[derive(Clone)]
pub struct AppConfig {
    pub inference_url: String,
    pub database_url: Option<String>,
    pub bind_addr: SocketAddr,
    pub pdf_service_url: String,
    pub privacy_mode: bool,
    pub enable_db_content_logging: bool,
    pub max_images: usize,
    pub min_scenario_words: usize,
    pub min_scenario_chars: usize,
    pub max_scenario_chars: usize,
    pub max_location_chars: usize,
    pub inference_timeout_secs: u64,
}

fn env_bool(name: &str, default: bool) -> bool {
    env::var(name)
        .ok()
        .map(|value| {
            matches!(
                value.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "yes" | "on"
            )
        })
        .unwrap_or(default)
}

fn env_usize(name: &str, default: usize) -> usize {
    env::var(name)
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(default)
}

fn env_u64(name: &str, default: u64) -> u64 {
    env::var(name)
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(default)
}

impl AppConfig {
    pub fn from_env() -> Self {
        let inference_url =
            env::var("INFERENCE_URL").unwrap_or_else(|_| "http://127.0.0.1:8001".to_string());
        let pdf_service_url =
            env::var("PDF_SERVICE_URL").unwrap_or_else(|_| "http://127.0.0.1:3001".to_string());
        let database_url = env::var("DATABASE_URL").ok();
        let bind_addr = env::var("BIND_ADDR")
            .ok()
            .and_then(|value| value.parse().ok())
            .unwrap_or_else(|| SocketAddr::from(([0, 0, 0, 0], 8000)));
        let privacy_mode = env_bool("PRIVACY_MODE", true);
        let enable_db_content_logging = env_bool("ENABLE_DB_CONTENT_LOGGING", false);
        let max_images = env_usize("MAX_IMAGES", 4);
        let min_scenario_words = env_usize("MIN_SCENARIO_WORDS", 3);
        let min_scenario_chars = env_usize("MIN_SCENARIO_CHARS", 15);
        let max_scenario_chars = env_usize("MAX_SCENARIO_CHARS", 4000);
        let max_location_chars = env_usize("MAX_LOCATION_CHARS", 256);
        let inference_timeout_secs = env_u64("INFERENCE_TIMEOUT_SECS", 20);

        Self {
            inference_url,
            pdf_service_url,
            database_url,
            bind_addr,
            privacy_mode,
            enable_db_content_logging,
            max_images,
            min_scenario_words,
            min_scenario_chars,
            max_scenario_chars,
            max_location_chars,
            inference_timeout_secs,
        }
    }
}
