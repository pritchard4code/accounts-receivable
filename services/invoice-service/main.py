from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.invoices import router as invoices_router

app = FastAPI(
    title="AR Invoice Service",
    description="Invoice Management Service for Accounts Receivable",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "invoice-service"}
