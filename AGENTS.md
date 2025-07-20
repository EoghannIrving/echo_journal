# Codex Agent Guidelines

This file outlines how the Codex agent should interact with the Echo Journal repository.
The instructions apply to the entire project tree.

## Development setup
1. Create a virtual environment and install dependencies:
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   You may also run the app with Docker using `docker-compose up --build`.

## Style and testing
- Format all Python code with **Black**.
- Run **Pylint** with a minimum score of 8:
  ```sh
  pylint $(git ls-files '*.py') --fail-under=8
  ```
- Execute the test suite with **pytest**.
- Ensure `black`, `pylint` and `pytest` succeed before committing changes.

## Commit and PR guidelines
- Make small, focused commits with clear messages.
- Open pull requests against `main` after all checks pass.
- Summaries should briefly explain what changed and reference key files.

