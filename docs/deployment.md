# Deployment

## Security

- Set `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` before exposing the app to the internet. Without these variables, anyone can access your journal.
- Provide a valid contact email in `NOMINATIM_USER_AGENT` to comply with the Nominatim usage policy; requests without contact info may be throttled or rejected.
- The `/api/settings` endpoint returns server configuration details for convenience during development. Restrict it to trusted networks or run the app behind a VPN or reverse proxy to avoid leaking secrets.
- Outbound requests include a 10-second timeout and prompt categories are sanitized before saving or rendering, limiting the impact of malicious or unexpected input.

## Reverse Proxy

Echo Journal binds to `127.0.0.1` by default so it's only reachable from the local machine. To make it available elsewhere, run it behind your VPN (e.g. WireGuard) or a reverse proxy such as Nginx or Caddy. The proxy can handle TLS termination and restrict access to known networks. Set `ECHO_JOURNAL_HOST=0.0.0.0` if the proxy needs to reach the app over the network.

Example Nginx configuration terminating TLS and proxying requests:

```nginx
server {
    listen 443 ssl;
    server_name journal.example.com;

    ssl_certificate     /etc/letsencrypt/live/journal.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/journal.example.com/privkey.pem;

    location / {
       proxy_pass http://127.0.0.1:8510;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

When exposing the app publicly, enable Basic Auth by setting `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` so unauthenticated requests are rejected with a `401` response.
