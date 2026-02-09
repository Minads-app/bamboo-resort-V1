@echo off
REM Quick deployment helper script for Windows
echo ========================================
echo Bamboo Resort - Deployment Helper
echo ========================================
echo.

echo Step 1: Generating Streamlit Secrets...
python generate_secrets.py
echo.
echo ========================================
echo.

echo Step 2: Git Status
git status
echo.
echo ========================================
echo.

echo Ready to deploy? This will:
echo 1. Add all changes to git
echo 2. Commit with message "Deploy to Streamlit Cloud"
echo 3. Push to GitHub
echo.
set /p confirm="Continue? (y/n): "

if /i "%confirm%"=="y" (
    echo.
    echo Adding files...
    git add .
    
    echo Committing...
    git commit -m "Deploy to Streamlit Cloud"
    
    echo Pushing to GitHub...
    git push origin main
    
    echo.
    echo ========================================
    echo ✅ Done! Now go to https://share.streamlit.io
    echo    to complete the deployment.
    echo ========================================
) else (
    echo Deployment cancelled.
)

pause
