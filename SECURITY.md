# Security Policy

Echo Journal is intended for use on a trusted local network. The app includes
optional HTTP Basic authentication that can be enabled by setting the
`BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` environment variables. Without
those variables, there is no built‑in authentication. **Do not expose the
application directly to the internet.** If you deploy publicly, enable Basic
Auth and place the app behind a secure reverse proxy with additional access
controls. Refer to [docs/deployment.md](docs/deployment.md) for guidance on
secure configuration and reverse proxy examples.

## Reporting a Vulnerability

If you discover a security issue, please create a new GitHub issue with the
details and include `[Security]` in the title. You may also email the
maintainers privately at `security@echojournal.org` if you prefer not to disclose
information publicly.

When reporting a potential vulnerability, please provide:

- A description of the issue and its impact
- Steps to reproduce the problem
- Any relevant logs or screenshots

We will acknowledge your report within five business days.
