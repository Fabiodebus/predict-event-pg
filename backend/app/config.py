from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str  # postgresql+asyncpg://user:pass@host:5432/dbname

    # Redis — Celery requires broker and result backend as separate URLs
    celery_broker_url: str   # redis://host:6379/0
    celery_result_backend: str  # redis://host:6379/1

    # AWS
    aws_region: str = "us-east-1"
    aws_s3_bucket: str

    # Cognito
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str = "us-east-1"

    # CORS — comma-separated origins, e.g. "http://localhost:5173,https://app.predict-ability.com"
    allowed_origins: list[str] = ["http://localhost:5173"]

    # LLM providers
    anthropic_api_key: str
    openai_api_key: str

    # LLM role -> "<provider>:<model_id>" mapping. Provider must be one of
    # the names registered in app.llm.router. No model defaults; raise on
    # missing role at startup.
    llm_role_models: dict[str, str] = {
        "long_context_reasoning": "anthropic:claude-3-7-sonnet-20250219",
        "structured_extraction": "openai:gpt-4o-mini",
        "message_generation": "openai:gpt-4o-mini",
    }

    # Third-party integrations
    crustdata_api_key: str
    browser_use_api_key: str
    unipile_api_key: str
    unipile_base_url: str

    # LangGraph PostgresSaver — separate sync DSN (postgresql://...) from
    # the async asyncpg URL used by SQLAlchemy. PostgresSaver uses psycopg.
    langgraph_checkpoint_dsn: str  # postgresql://user:pass@host:5432/dbname


settings = Settings()
