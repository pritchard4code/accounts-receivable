from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
from jose import JWTError, jwt
from config import settings
import json

app = FastAPI(
    title="AR API Gateway",
    description="API Gateway for Accounts Receivable Microservices",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://frontend:4200", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes that don't require auth
PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/health",
    "/docs",
    "/openapi.json",
}

SERVICE_ROUTES = {
    "/api/auth": settings.auth_service_url,
    "/api/users": settings.auth_service_url,
    "/api/invoices": settings.invoice_service_url,
    "/api/payments": settings.payment_service_url,
    "/api/collections": settings.collections_service_url,
    "/api/credit": settings.credit_service_url,
    "/api/disputes": settings.dispute_service_url,
    "/api/reports": settings.reporting_service_url,
    "/api/customers": settings.customer_service_url,
}


def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_target_service(path: str) -> str:
    # Rewrite /api/{service}/* to /api/v1/{service}/*
    for prefix, service_url in SERVICE_ROUTES.items():
        if path.startswith(prefix):
            return service_url, path.replace("/api/", "/api/v1/", 1)
    raise HTTPException(status_code=404, detail=f"No service found for path: {path}")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str):
    full_path = f"/api/{path}"

    # Check auth for non-public paths
    public_path = f"/api/v1/{path}"
    if public_path not in PUBLIC_PATHS and not path.startswith("auth/login") and not path.startswith("auth/register"):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth_header.split(" ")[1]
        verify_jwt_token(token)

    # Find target service
    try:
        target_url, rewritten_path = get_target_service(full_path)
    except HTTPException:
        raise

    # Build proxy URL
    proxy_url = f"{target_url}{rewritten_path}"
    if request.url.query:
        proxy_url += f"?{request.url.query}"

    # Get request body
    body = await request.body()

    # Forward headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.request(
                method=request.method,
                url=proxy_url,
                headers=headers,
                content=body,
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable: {target_url}"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Service timeout"
            )

    # Handle binary responses (like PDFs)
    content_type = response.headers.get("content-type", "")
    if "application/pdf" in content_type or "octet-stream" in content_type:
        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=content_type,
    )
