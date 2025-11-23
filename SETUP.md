# Production Setup Guide

## 1. Bootstrap the workspace
1. Install Python/runtime dependencies: `pip install .`
2. Install Node.js dependencies and compile UI assets: `npm install && npm run build:css`
3. Ensure the following folders exist (pre-commit hooks will enforce them): `src`, `config`, `docs`, `tests`, `docker`, and either `build` or `dist`.

## 2. Create configuration from the samples
1. Copy `.env.example` to `.env` and populate live values. Keep `.env` local only; it is ignored by Git.
2. Copy `config/config.sample.json` to `config/config.json` (or another path you control) and adjust logging, integration, and security blocks.
3. Copy `settings.example.yaml` to `settings.yaml` inside your data directory (typically under `${DATA_DIR}/.settings/`).
4. Use `docker-compose.sample.yml` as a reference. When you need a runnable compose stack, copy it to `docker-compose.yml`, point `env_file` to `.env`, and keep the relative bindings (`./static`, `./prompts.yaml`).

## 3. Environment considerations
- Place data directories outside the repo and point `DATA_DIR` and `MINDLOOM_DATA_DIR` at them. Volume mappings in `docker-compose.yml` already use the dotenv values.
- Set `PROMPTS_FILE`, `STATIC_DIR`, and other path-based variables to relative locations (`./prompts.yaml`, `./static`) so builds remain portable.
- Consume `config/config.json` values in runtime code by mapping them into your own deployment tooling or export them as environment variables if necessary.

## 4. Deployment checklist
1. Run `npm run build:css` whenever Tailwind or static assets change; the CSS artifacts live under `static/` and are copied into Docker builds.
2. Build the Docker image with `docker compose build`, ensuring `docker/Dockerfile` is referenced explicitly via the `dockerfile` key (see `docker-compose.sample.yml`).
3. Launch the stack with `docker compose up` (or your orchestrator of choice). Keep the `.env` file outside version control and supply secrets via environment variables or a secure store.
4. Optional: Populate `config/config.json` from the sample to drive runtime defaults for logging and integrations.

## 5. Security best practices
- This repository ships with pre-commit hooks that guard credentials and folder layout. Run `pre-commit install` and `pre-commit run --all-files` before pushing changes.
- Review `docs/security-protocols.md` for details about the detect-secrets baseline, pattern checks, and folder layout enforcement.
- Never commit private keys, `.env`, or other secrets: the hooks will block such attempts and the `.gitignore` hides them from Git.
- Rotate API keys (Immich, Jellyfin, Wordnik, etc.) regularly and keep them in a secrets manager or environment store.
