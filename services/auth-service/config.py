from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://aruser:arpassword@postgres:5432/accounts_receivable"
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 480
    service_name: str = "auth-service"

    class Config:
        env_file = ".env"


settings = Settings()
