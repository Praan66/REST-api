from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


on_current_file = Path(__file__).resolve()
ROOT_DIR = on_current_file.parent.parent.parent

class DBSettings(BaseSettings):
    user: str
    password: str
    host: str
    port: str
    dbname: str

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="postgres_",
        case_sensitive=False,
        extra="ignore"
    )

class SecretSettings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="s",
        case_sensitive=False,
        extra="ignore"
    )
class AppSettings:
    db = DBSettings()
    ssetting = SecretSettings()

settings = AppSettings()