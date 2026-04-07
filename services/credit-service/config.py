from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://aruser:arpassword@postgres:5432/accounts_receivable"
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    service_name: str = "credit-service"
    auth_service_url: str = "http://auth-service:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
