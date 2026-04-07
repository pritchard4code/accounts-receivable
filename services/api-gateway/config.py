from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    auth_service_url: str = "http://auth-service:8001"
    invoice_service_url: str = "http://invoice-service:8002"
    payment_service_url: str = "http://payment-service:8003"
    collections_service_url: str = "http://collections-service:8004"
    credit_service_url: str = "http://credit-service:8005"
    dispute_service_url: str = "http://dispute-service:8006"
    reporting_service_url: str = "http://reporting-service:8007"
    customer_service_url: str = "http://customer-service:8008"

    class Config:
        env_file = ".env"


settings = Settings()
