@echo off
echo Starting AR Manager Microservices...

set BASE=C:\My Programs\claude\accounts-receivable\services

echo [1/9] Starting auth-service on port 8001...
start "auth-service" /min cmd /c "cd /d \"%BASE%\auth-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8001 > logs\auth.log 2>&1"

timeout /t 3 /nobreak >nul

echo [2/9] Starting invoice-service on port 8002...
start "invoice-service" /min cmd /c "cd /d \"%BASE%\invoice-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8002 > logs\invoice.log 2>&1"

echo [3/9] Starting payment-service on port 8003...
start "payment-service" /min cmd /c "cd /d \"%BASE%\payment-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8003 > logs\payment.log 2>&1"

echo [4/9] Starting collections-service on port 8004...
start "collections-service" /min cmd /c "cd /d \"%BASE%\collections-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8004 > logs\collections.log 2>&1"

echo [5/9] Starting credit-service on port 8005...
start "credit-service" /min cmd /c "cd /d \"%BASE%\credit-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8005 > logs\credit.log 2>&1"

echo [6/9] Starting dispute-service on port 8006...
start "dispute-service" /min cmd /c "cd /d \"%BASE%\dispute-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8006 > logs\dispute.log 2>&1"

echo [7/9] Starting reporting-service on port 8007...
start "reporting-service" /min cmd /c "cd /d \"%BASE%\reporting-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8007 > logs\reporting.log 2>&1"

echo [8/9] Starting customer-service on port 8008...
start "customer-service" /min cmd /c "cd /d \"%BASE%\customer-service\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8008 > logs\customer.log 2>&1"

timeout /t 5 /nobreak >nul

echo [9/9] Starting api-gateway on port 8000...
start "api-gateway" /min cmd /c "cd /d \"%BASE%\api-gateway\" && venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 > logs\gateway.log 2>&1"

echo.
echo All services started. Access:
echo   API Gateway:  http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo   Frontend:     http://localhost:4200
