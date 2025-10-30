# Topcit Quest

## Quick start

- Install Python 3.10+ and create a virtualenv (optional).
- Set `DATABASE_URL` to a Postgres connection (Neon supported).
- Start the server: `PORT=8000 python server.py`
- Open `http://localhost:8000/index.html`.

## Environment variables

- `DATABASE_URL`: PostgreSQL connection string.
- `PORT`: Server port (default `8000`).

### Email (SMTP) — optional but recommended
To send verification emails, configure these SMTP variables:

- `SMTP_HOST`: SMTP server host (e.g., `smtp.gmail.com`).
- `SMTP_PORT`: SMTP port (587 for STARTTLS, 465 for SSL).
- `SMTP_USER`: SMTP username (usually your email address).
- `SMTP_PASS`: SMTP password (or app password).
- `SMTP_FROM`: From address (defaults to `SMTP_USER`).
- `SMTP_USE_SSL`: `true` to use SMTPS (port 465); otherwise STARTTLS is attempted.

Notes:
- For Gmail, enable 2FA and create an App Password.
- If SMTP is not configured, the API still issues verification tokens; you can verify via the link on the verify page.
