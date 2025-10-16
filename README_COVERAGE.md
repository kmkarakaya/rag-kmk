Run tests with coverage

Windows (PowerShell/cmd):

    call conda activate rag
    python -m pytest --cov=rag_kmk --cov-report=term-missing

Or use the convenience script:

    scripts\run_coverage.bat
