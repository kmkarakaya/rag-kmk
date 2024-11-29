@echo off

git add .
git commit -m "Package Structure Created"
bump-my-version bump patch --dry-run --verbose
bump-my-version bump patch
git push --tags
git push