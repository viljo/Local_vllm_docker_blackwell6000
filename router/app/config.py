"""
Configuration management for router service
"""
import os
from typing import Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Authentication
    api_key: str = os.getenv("API_KEY", "sk-local-dev-key")

    # Backend URLs
    coder_backend_url: str = os.getenv("CODER_BACKEND_URL", "http://vllm-coder:8000")
    general_backend_url: str = os.getenv("GENERAL_BACKEND_URL", "http://vllm-general:8000")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # CORS Origins
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

    # Request limits
    max_queue_size: int = 100
    request_timeout: float = 300.0  # 5 minutes

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Model routing configuration
def get_model_routing() -> Dict[str, str]:
    """Get model to backend URL mapping"""
    return {
        "deepseek-coder-33b-instruct": settings.coder_backend_url,
        "deepseek-coder-33B-instruct": settings.coder_backend_url,
        "mistral-7b-v0.1": settings.general_backend_url,
        "qwen-2.5-14b-instruct": settings.general_backend_url,
    }
