# AGENTS Instructions

These instructions apply to the entire repository.

## When pulling updates
- Work off the latest `main` branch.
- Sync with `git pull --rebase origin main` before starting new work.
- After pulling, reinstall dependencies if required:
  - `pip install .`
  - `npm install`

## Before pushing changes
- Format Python code: `black .`
- Lint: `pylint $(git ls-files '*.py') --fail-under=8`
- Run tests: `pytest`
- If frontend assets change, rebuild CSS: `npm run build:css`
- Ensure commit messages are clear and the worktree is clean (`git status`).

Follow any more specific instructions in nested `AGENTS.md` files.
