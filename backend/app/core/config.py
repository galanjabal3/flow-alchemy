from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "FlowAlchemy API"
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Worker
    WORKER_POLL_INTERVAL: float = 1.0

    # Retry (workflow-level)
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE: int = 2
    RETRY_JITTER: float = 0.5  # 0-50% jitter

    # Node-level retry
    NODE_MAX_RETRIES: int = 2

    # Timeout
    WORKFLOW_TIMEOUT: int = 300  # 5 min
    NODE_TIMEOUT: int = 30  # 30 sec

    # Resource Limits
    MAX_CONCURRENT_PER_USER: int = 15
    MAX_CONCURRENT_TOTAL: int = 30
    MAX_NODES_PER_WORKFLOW: int = 50
    MAX_PAYLOAD_SIZE: int = 1048576  # 1MB
    MAX_RESPONSE_SIZE: int = 10485760  # 10MB

    @model_validator(mode="after")
    def validate_critical_settings(self) -> "Settings":
        errors = []
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY must not be empty")
        if len(self.SECRET_KEY) < 16:
            errors.append("SECRET_KEY must be at least 16 characters")
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL must not be empty")

        # Resource limit validation
        if self.MAX_CONCURRENT_PER_USER < 1:
            errors.append("MAX_CONCURRENT_PER_USER must be at least 1")
        if self.MAX_CONCURRENT_TOTAL < self.MAX_CONCURRENT_PER_USER:
            errors.append("MAX_CONCURRENT_TOTAL must be >= MAX_CONCURRENT_PER_USER")
        if self.MAX_NODES_PER_WORKFLOW < 1:
            errors.append("MAX_NODES_PER_WORKFLOW must be at least 1")
        if self.MAX_PAYLOAD_SIZE < 1024:
            errors.append("MAX_PAYLOAD_SIZE must be at least 1024 bytes")
        if self.MAX_RESPONSE_SIZE < 1024:
            errors.append("MAX_RESPONSE_SIZE must be at least 1024 bytes")
        if self.NODE_MAX_RETRIES < 0:
            errors.append("NODE_MAX_RETRIES must be >= 0")
        if self.NODE_TIMEOUT < 1:
            errors.append("NODE_TIMEOUT must be at least 1 second")

        if errors:
            raise ValueError("; ".join(errors))
        return self

    @property
    def origins_list(self) -> List[str]:
        return [i.strip() for i in self.ALLOWED_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
