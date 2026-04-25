# backend/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):

    #  App 
    APP_ENV:     str = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False

    #  Anthropic
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL:   str = "claude-sonnet-4-6"
    

    #  Base de datos
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:port/db

    # Blockchain
    MONAD_RPC_URL:       str = "https://testnet-rpc.monad.xyz"
    MONAD_PRIVATE_KEY:   str = ""
    MONAD_CONTRACT_ADDR: str = ""
    BLOCKCHAIN_ENABLED:  bool = False  # False = simulate locally for demo

    #  CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
