mod config;
mod handlers;
mod models;
mod services;
mod state;

use axum::extract::DefaultBodyLimit;
use axum::{routing::post, Router};
use config::AppConfig;
use handlers::chat::chat_handler;
use handlers::pdf::result_pdf_handler;
use services::database::ensure_schema;
use sqlx::PgPool;
use state::AppState;
use tracing::{error, info};
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let config = AppConfig::from_env();

    let pool = match config.database_url.as_deref() {
        Some(url) => {
            info!(%url, "connecting to database");
            match PgPool::connect(url).await {
                Ok(pool) => {
                    ensure_schema(&pool).await;
                    Some(pool)
                }
                Err(e) => {
                    error!(%e, "failed to connect to database; continuing without logging");
                    None
                }
            }
        }
        None => None,
    };

    let state = AppState {
        config: config.clone(),
        pool,
    };

    let app = Router::new()
        .route("/api/chat", post(chat_handler))
        .route("/api/result-pdf", post(result_pdf_handler))
        .layer(DefaultBodyLimit::max(100 * 1024 * 1024))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(config.bind_addr).await?;
    info!(addr = %config.bind_addr, "listening");
    axum::serve(listener, app).await?;

    Ok(())
}
