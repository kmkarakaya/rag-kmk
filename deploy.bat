@echo off
REM https://www.youtube.com/watch?v=Z2d1Kw1xSVY
REM https://github.com/opengeos/cookiecutter-pypackage
REM https://github.com/kmkarakaya/rag-kmk

git add .
git commit -m "Package Structure Created"
bump-my-version bump patch --dry-run --verbose
bump-my-version bump patch
git push --tags
git push

