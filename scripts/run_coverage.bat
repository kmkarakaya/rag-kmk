@echo off
REM Run tests with coverage (Windows PowerShell / cmd friendly)
call conda activate rag
python -m pytest --cov=rag_kmk --cov-report=term-missing -q %*
