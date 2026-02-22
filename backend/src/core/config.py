from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Required core DB config
    NEON_DB_URL: str

    # Required R2 config
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_TOKEN: str
    R2_BUCKET_NAME: str
    R2_ENDPOINT_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
