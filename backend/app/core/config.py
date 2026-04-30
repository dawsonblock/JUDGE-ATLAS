from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JudgeTracker Atlas"
    database_url: str = "sqlite:///./judgetracker.db"
    courtlistener_api_token: str | None = None
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"
    courtlistener_max_pages: int = 10
    courtlistener_max_dockets_per_run: int = 100
    courtlistener_timeout_seconds: int = 60
    app_env: str = "production"
    auto_seed: bool = True
    cors_origins: str = "https://localhost:3000"
    enable_admin_imports: bool = False
    enable_admin_review: bool = False
    enable_public_event_post: bool = False
    admin_token: str | None = None
    admin_review_token: str | None = None
    geonames_username: str | None = None
    statscan_enabled: bool = False
    fbi_crime_enabled: bool = False
    local_feeds_enabled: bool = False
    gdelt_enabled: bool = False
    courtlistener_bulk_data_dir: str = "data/courtlistener-bulk"
    courtlistener_bulk_snapshot_date: str | None = None
    courtlistener_bulk_enabled_files: str = (
        "courts,people-db-people,people-db-positions,"
        "dockets,opinion-clusters"
    )
    courtlistener_bulk_import_batch_size: int = 500
    courtlistener_bulk_normalize_batch_size: int = 200
    courtlistener_bulk_include_opinions: bool = False
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    ollama_timeout_seconds: int = 30

    # Rate limiting (requests per minute)
    rate_limit_public: int = 100  # Public API endpoints
    rate_limit_admin: int = 30  # Admin API endpoints
    rate_limit_map: int = 60  # Map endpoints
    rate_limit_ingestion: int = 10  # Ingestion endpoints
    rate_limit_enabled: bool = True

    # Request size limits (bytes)
    max_request_size: int = 10 * 1024 * 1024  # 10MB for regular API
    max_csv_upload_size: int = 50 * 1024 * 1024  # 50MB for CSV uploads

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JTA_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
