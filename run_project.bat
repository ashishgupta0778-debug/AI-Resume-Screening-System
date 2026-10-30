@echo off
title AI-Based Resume Screening and Candidate Shortlisting System
echo ============================================================
echo   AI-Based Resume Screening and Candidate Shortlisting System
echo ============================================================
echo.
echo Starting FastAPI Backend server on http://127.0.0.1:8000...
echo.
echo Access URLs:
echo   - Web Application: http://127.0.0.1:8000/frontend/login.html
echo   - Interactive API Docs: http://127.0.0.1:8000/docs
echo   - Recruiter Credentials: admin@hcl.com / admin123
echo.
echo ============================================================
call .\venv\Scripts\activate.bat
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
pause
