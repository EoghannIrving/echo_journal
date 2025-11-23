# Security Protocols

This repository now ships with a multi-layered security guardrail package that runs before code lands on `main`.

1. **Pre-commit enforcement**
   - `detect-secrets` inspects every staged change against `.secrets.baseline` to ensure no high-entropy secrets sneak in.
   - `scripts/pre_commit/check_sensitive_patterns.py` scans staged files for keyword patterns such as `API_KEY`, `SECRET`, `PASSWORD`, and private key headers.
   - `scripts/pre_commit/validate_structure.py` ensures the sanctioned `src`, `config`, `docs`, `tests`, `docker`, and build artifact folders remain present.

2. **Working with credentials**
   - Never commit `.env` or any file containing live credentials; the new `.gitignore` already blocks these.
   - When a legitimate secret must be introduced, update `.secrets.baseline` via `detect-secrets scan` and record the change. Reviewers should confirm the rationale.
   - Keep production credentials in vaults or environment stores and populate `.env` only on deployed hosts or developer machines.

3. **Configuration hygiene**
   - Defaults live in `config/config.sample.json` and should be copied/renamed for each environment.
   - Document all sensitive integrations (Immich, Jellyfin, Wordnik, Audiobookshelf) in `SETUP.md`, and rotate keys regularly.

4. **Deploy-time hardening**
   - The `docker-compose.sample.yml` references `.env` values to avoid secrets in templates.
   - `SETUP.md` explains how to render production files from samples, rebuild CSS, and rerun validations before shipping.

Running `pre-commit run --all-files` before a merge will exercise every gate above; failures should be addressed locally before pushing.
