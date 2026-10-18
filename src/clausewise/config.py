from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CLAUSEWISE_", extra="ignore")

    database_url: str = "postgresql://clausewise:clausewise@localhost:5433/clausewise"
    answer_model: str = "claude-sonnet-5-5"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Chunk size in characters. Legal sections vary a lot; long ones are split on paragraph
    # boundaries, short neighbours under the same heading are not merged (keeps citations exact).
    chunk_max_chars: int = 1800


settings = Settings()
