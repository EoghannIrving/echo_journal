# Contributing to Echo Journal

Thank you for your interest in improving Echo Journal! This project welcomes pull requests and issue reports. The sections below outline the basic workflow for contributors.

## Development setup

1. Fork the repository and clone your fork locally.
2. Create a virtual environment and install the requirements:
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Alternatively you can run the app through Docker Compose using `docker-compose up --build`.
3. Run the application locally and verify your changes.

## Style and testing

- Format code using **Black** and ensure **Pylint** reports a score of 8 or higher:
  ```sh
  black .
  pylint $(git ls-files '*.py') --fail-under=8
  ```
- Execute the test suite with `pytest` before submitting a pull request.

## Submitting changes

1. Create a feature branch for your work.
2. Make small, focused commits with clear messages.
3. Ensure `black`, `pylint` and `pytest` pass.
4. Open a pull request against `main` describing your changes.

## Reporting issues

When opening an issue, please include:

- Steps to reproduce the problem
- Your operating system and Python version
- Any relevant logs or screenshots

Thank you for helping make Echo Journal better!
