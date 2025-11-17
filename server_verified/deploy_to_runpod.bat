@echo off
REM Deployment script for RunPod (Windows)
REM This script uploads the server directory to your RunPod instance

REM RunPod connection details
set RUNPOD_HOST=213.173.110.214
set RUNPOD_PORT=19492
set RUNPOD_USER=root
set SSH_KEY=%USERPROFILE%\.ssh\id_ed25519
set REMOTE_DIR=/workspace/pdf2markdown

echo =========================================
echo   PDF to Markdown - RunPod Deployment
echo =========================================
echo.

REM Check if SSH key exists
if not exist "%SSH_KEY%" (
    echo Error: SSH key not found at %SSH_KEY%
    echo Please update the SSH_KEY variable in this script
    pause
    exit /b 1
)

echo Step 1: Creating remote directory...
ssh -i "%SSH_KEY%" -p %RUNPOD_PORT% %RUNPOD_USER%@%RUNPOD_HOST% "mkdir -p %REMOTE_DIR%"

echo.
echo Step 2: Uploading server files...
echo This may take a few minutes...

REM Using scp to upload files
scp -i "%SSH_KEY%" -P %RUNPOD_PORT% -r server\* %RUNPOD_USER%@%RUNPOD_HOST%:%REMOTE_DIR%/

if errorlevel 1 (
    echo Error: Failed to upload files
    pause
    exit /b 1
)

echo.
echo Step 3: Installing dependencies...
ssh -i "%SSH_KEY%" -p %RUNPOD_PORT% %RUNPOD_USER%@%RUNPOD_HOST% "cd %REMOTE_DIR% && pip install -r requirements.txt"

echo.
echo =========================================
echo   Deployment Complete!
echo =========================================
echo.
echo Next steps:
echo 1. SSH into RunPod:
echo    ssh -i "%SSH_KEY%" -p %RUNPOD_PORT% %RUNPOD_USER%@%RUNPOD_HOST%
echo.
echo 2. Start the server:
echo    cd %REMOTE_DIR%
echo    screen -S pdf_server
echo    python server.py
echo.
echo 3. Get your HTTP Service URL from RunPod dashboard (Port 7777)
echo.
echo 4. Update client\config.json with the URL
echo.
echo 5. Test from local machine:
echo    cd client
echo    python client.py test.pdf
echo.
pause
