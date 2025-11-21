# Deployment

> **Warning:** Echo Journal is in an alpha state and should not be exposed directly to the public internet. If remote access is required, use a VPN, reverse proxy, or other access controls to restrict who can reach the service.

## Security

- Set `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` before exposing the app to the internet. Without these variables, anyone can access your journal.
- Provide a valid contact email in `NOMINATIM_USER_AGENT` to comply with the Nominatim usage policy; requests without contact info may be throttled or rejected.
- The `/api/settings` endpoint returns server configuration details for convenience during development. Restrict it to trusted networks or run the app behind a VPN or reverse proxy to avoid leaking secrets.
- Outbound requests include a 10-second timeout and prompt categories are sanitized before saving or rendering, limiting the impact of malicious or unexpected input.

## Reverse Proxy

Echo Journal binds to `127.0.0.1:8000` by default so it's only reachable from the local machine. To make it available elsewhere, run it behind your VPN (e.g. WireGuard) or a reverse proxy such as Nginx or Caddy. The proxy can handle TLS termination and restrict access to known networks. Set `ECHO_JOURNAL_HOST=0.0.0.0` if the proxy needs to reach the app over the network. Change the port with `ECHO_JOURNAL_PORT`.

Example Nginx configuration terminating TLS and proxying requests:

```nginx
server {
    listen 443 ssl;
    server_name journal.example.com;

    ssl_certificate     /etc/letsencrypt/live/journal.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/journal.example.com/privkey.pem;

    location / {
       proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Nginx Proxy Manager

If you prefer a UI to manage Nginx, [Nginx Proxy Manager](https://nginxproxymanager.com/) can front Echo Journal and handle
TLS termination.

1. In **Hosts → Proxy Hosts** click **Add Proxy Host**.
2. Enter your domain (e.g. `journal.example.com`) under **Domain Names**.
3. Set **Scheme** to `http` and forward traffic to `http://echo-journal:8000`.
4. Enable **Block Common Exploits** and **Websockets Support**.
5. In the **Advanced** tab add:

   ```nginx
   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
   ```

   These headers preserve the original host and client IP information.
6. On the **SSL** tab request a Let's Encrypt certificate, enable **Force SSL**, and save.

## Direct HTTPS

Echo Journal can serve HTTPS directly when provided with a TLS key and
certificate. Set `ECHO_JOURNAL_SSL_KEYFILE` and
`ECHO_JOURNAL_SSL_CERTFILE` to the paths of these files to enable the
built-in server to handle TLS:

```bash
ECHO_JOURNAL_SSL_KEYFILE=/etc/ssl/private/journal.key \
ECHO_JOURNAL_SSL_CERTFILE=/etc/ssl/certs/journal.pem \
echo-journal
```

Ensure the key and certificate are valid and readable by the process.

When exposing the app publicly, enable Basic Auth by setting `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` so unauthenticated requests are rejected with a `401` response.
