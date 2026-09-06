from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bzzorio_api_key: str
    bzzorio_base_url: str
    db_url: str
    redis_url: str
    model_config = SettingsConfigDict(env_file=".env")
    postgres_user: str
    postgres_pass: str
    postgres_db: str

settings = Settings()