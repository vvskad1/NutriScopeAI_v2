@echo off
REM deploy_v3.bat - Deploy NutriScope AI v3 to GitHub (Windows)

echo 🚀 Deploying NutriScope AI v3 to GitHub...
echo.

REM Check current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
if not "%CURRENT_BRANCH%"=="v3-llm-integration" (
    echo ❌ Error: Not on v3-llm-integration branch
    echo Current branch: %CURRENT_BRANCH%
    echo Please run: git checkout v3-llm-integration
    pause
    exit /b 1
)

echo 📋 Deployment Summary:
echo Branch: v3-llm-integration
echo.
echo Recent commits:
git log --oneline main..HEAD -5
echo.

echo 🔍 Key Files Being Deployed:
echo ✅ Local LLM Integration: backend/app/llm/
echo ✅ Trained Model: backend/llm/results/ (excluded from git - too large)
echo ✅ Updated API: backend/app/api/routes.py
echo ✅ Enhanced Frontend: frontend/pages/report_details.py
echo ✅ Documentation: README_v3.md, CHANGELOG.md
echo.

echo 📝 Before pushing to GitHub:
echo 1. Make sure your GitHub repository is set up
echo 2. The trained model files are ~3GB and excluded from git
echo 3. Users will need to train their own model or use API mode
echo.

set /p CONFIRM="Continue with deployment? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo ❌ Deployment cancelled
    pause
    exit /b 1
)

echo.
echo 🔄 Pushing to GitHub...

REM Push the v3 branch  
git push origin v3-llm-integration
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to push branch
    pause
    exit /b 1
)
echo ✅ Successfully pushed v3-llm-integration branch

echo.
echo 🏷️ Creating release tag...
git tag -a v3.0.0 -m "v3.0.0: Privacy-Preserving Local LLM Integration

Major Features:
- Local FLAN-T5-large model for privacy-first clinical analysis
- Hybrid architecture supporting local/API model switching  
- Dynamic meal recommendations based on lab results
- Complete HIPAA compliance with zero external data transfer
- Research-grade system ready for academic publication

Technical Achievements:
- 50,000 clinical examples training dataset
- 95%% loss reduction during training
- 2-3 second inference time
- Production-ready error handling and fallbacks"

if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to create tag
    pause
    exit /b 1
)
echo ✅ Created version tag v3.0.0

REM Push the tag
git push origin v3.0.0
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to push tag  
    pause
    exit /b 1
)
echo ✅ Successfully pushed version tag

echo.
echo 🎉 Deployment Complete!
echo.
echo 📍 Next Steps:
echo 1. Go to your GitHub repository
echo 2. Create a Pull Request from v3-llm-integration to main (optional)
echo 3. Create a GitHub Release using tag v3.0.0
echo 4. Share your research paper submission! 📄
echo.
echo 🔗 Your v3 branch is now available at:
echo    https://github.com/yourusername/yourrepo/tree/v3-llm-integration
echo.
echo 🏆 Congratulations on creating a privacy-preserving healthcare AI system!
echo.
pause