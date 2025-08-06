# Known Bugs

The following issues are still unresolved. Fixed bugs have been moved to [BUGS_FIXED.md](BUGS_FIXED.md).

### Open Issues

- HTTP Basic authentication uses plaintext credentials stored in configuration
- Journal entries are written directly to the final file path without atomic replacement or symlink protection
- Full settings (including API keys and passwords) are logged during load and save operations
- CSRF token cookie is set without the `Secure` attribute
- Location data is inserted into YAML frontmatter without validation; latitude/longitude are cast to floats and the label is written verbatim
- No rate-limiting on authentication attempts
- Application defaults to `DEBUG` logging level
- Broad `except Exception` block during configuration reload hides underlying issues
- `load_settings` does not handle `yaml.YAMLError`, so malformed configuration files can crash the application
- `build_frontmatter` truncates Wordnik definitions to a single line, losing multi-line explanations【F:src/echo_journal/weather_utils.py†L75-L83】
