from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    recommendation_interaction_view_weight: float = 1.0
    recommendation_interaction_click_weight: float = 2.0
    recommendation_interaction_like_weight: float = 4.0
    recommendation_interaction_save_weight: float = 6.0
    recommendation_interaction_register_weight: float = 8.0
    recommendation_time_decay_lambda: float = 0.05
    recommendation_semantic_weight: float = 0.5
    recommendation_interest_weight: float = 0.2
    recommendation_behavior_weight: float = 0.2
    recommendation_popularity_weight: float = 0.05
    recommendation_recency_weight: float = 0.05
    recommendation_candidate_limit: int = 100
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_cors(cls, value: str) -> str:
        if "*" in value:
            raise ValueError("Wildcard CORS origins are not allowed")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
