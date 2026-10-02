import os
import socket
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Engine-wide configuration read from environment variables or the ``.env`` file.

    Attributes:
        deepseek_api_key: API key for the DeepSeek platform.
        deepseek_base_url: Base URL of the DeepSeek OpenAI-compatible API.
        deepseek_flash_model: Model used to propose exercises (generation).
        deepseek_pro_model: Model used as verification fallback (verification).
        mistral_api_key: API key for the Mistral platform.
        mistral_base_url: Base URL of the Mistral API.
        mistral_ocr_model: OCR model used for curricular extraction.
        provider_timeout_seconds: Read timeout for a single provider call.
        provider_max_retries: Attempts per provider call on transient failures.
        generation_max_attempts: Attempts per generation run before it is exhausted.
        llm_max_concurrency: Maximum generation runs processed concurrently per request.
        redis_enabled: Whether the Redis task worker runs (Docker Compose turns it on).
        redis_url: Redis connection URL.
        redis_tasks_stream: Stream where kalibra-api publishes tasks.
        redis_results_stream: Stream where the engine publishes results.
        redis_consumer_group: Consumer group shared by every engine instance.
        redis_consumer_name: Name of this consumer; unique per process.
        redis_worker_concurrency: Tasks processed at the same time by this process.
        redis_block_milliseconds: How long a read waits for new tasks.
        redis_claim_idle_milliseconds: Idle time after which a pending task is reclaimed.
        redis_max_deliveries: Deliveries after which a task is failed instead of retried.
        redis_results_max_length: Approximate cap of the results stream length.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_flash_model: str = "deepseek-v4-flash"
    deepseek_pro_model: str = "deepseek-v4-pro"

    mistral_api_key: SecretStr = SecretStr("")
    mistral_base_url: str = "https://api.mistral.ai"
    mistral_ocr_model: str = "mistral-ocr-latest"

    provider_timeout_seconds: float = Field(default=90.0, gt=0)
    provider_max_retries: int = Field(default=3, ge=1)

    generation_max_attempts: int = Field(default=3, ge=1)
    llm_max_concurrency: int = Field(default=4, ge=1)

    redis_enabled: bool = False
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    redis_tasks_stream: str = "kalibra:engine:tasks"
    redis_results_stream: str = "kalibra:engine:results"
    redis_consumer_group: str = "adaptive-engine"
    redis_consumer_name: str = Field(
        default_factory=lambda: f"{socket.gethostname()}-{os.getpid()}", min_length=1
    )
    redis_worker_concurrency: int = Field(default=4, ge=1)
    redis_block_milliseconds: int = Field(default=5_000, ge=1)
    redis_claim_idle_milliseconds: int = Field(default=900_000, ge=1)
    redis_max_deliveries: int = Field(default=3, ge=1)
    redis_results_max_length: int = Field(default=100_000, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once and cached.

    Returns:
        The cached ``Settings`` instance.
    """
    return Settings()
