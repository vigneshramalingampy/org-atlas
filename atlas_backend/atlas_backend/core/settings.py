import enum

from pydantic_settings import BaseSettings

class LogLevel(enum.Enum):
    """Possible log levels"""
    INFO = "INFO"
    DEBUG = "DEBUG"
    ERROR = "ERROR"
    FATAL = "FATAL"
    WARNING = "WARNING"

class Settings(BaseSettings):
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level : LogLevel = LogLevel.INFO


settings = Settings()
