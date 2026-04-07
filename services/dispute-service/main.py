from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.disputes import router as disputes_router

app = FastAPI(
    title="AR Dispute Service",
    description="Dispute Management Service for Accounts Receivable",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(disputes_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "dispute-service"}
