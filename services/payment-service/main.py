from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.payments import router as payments_router

app = FastAPI(
    title="AR Payment Service",
    description="Payment Management Service for Accounts Receivable",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "payment-service"}
