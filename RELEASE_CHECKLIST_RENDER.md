Render Release Checklist
- Set env vars in Render:
  - `SECRET_KEY` (new random, never checked in)
  - `DATABASE_URL` (Render Postgres connection string)
  - `ORS_API_KEY` (OpenRouteService key)
  - `API_CORS_ORIGINS` (comma-separated allowed origins or `*` during dev)
  - `SESSION_COOKIE_SECURE=1`
  - `REMEMBER_COOKIE_SECURE=1`
  - `SESSION_COOKIE_SAMESITE=Lax`
  - `PREFERRED_URL_SCHEME=https`
  - `API_TOKEN_MAX_AGE` (optional, seconds)

- Database:
  - Provision Render Postgres and set `DATABASE_URL`.
  - Migrate existing SQLite data if needed (export/import).
  - Enable automated backups in Render.

- App settings:
  - Ensure debug is off (Render uses production by default).
  - Confirm `gunicorn run:app` starts successfully.
  - Set a custom domain and force HTTPS in Render.

- Observability:
  - Enable Render logs and set alerting.
  - Add error tracking (Sentry) when ready.

- Smoke tests:
  - Visit `/` and `/locations`.
  - Generate a route and save it.
  - Check `/api/v1/health`.
