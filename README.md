# Starting Development Server

Create a virtual environment:

Linux
python3 venv -m .venv

Activate:

Linux
source .venv/bin/activate

Install dependencies
pip install -r requirements.txt

Neon database setup

Run `npx neonctl@latest init` and accept the AI-guided setup so Neon creates a PostgreSQL connection string for this project. Put the generated `DATABASE_URL` into `.env`, then run Django migrations against that database.

Petrock (Touchstone) login

Register the app at https://forms.gle/VirozJ8tRZK2hBax9 and add these redirect URLs:

- `https://trexdormcon.com/oidc/callback/`
- `https://www.trexdormcon.com/oidc/callback/` (if using www)
- `http://localhost:4000/oidc/callback/` (local development)

Add the credentials Petrock emails you to `.env`:

```
OIDC_RP_CLIENT_ID=your-client-id
OIDC_RP_CLIENT_SECRET=your-client-secret
```

When these variables are set, users can log in via Touchstone. Approver roles are assigned by creating `RexUser` records in the Django admin with the user's MIT email address.

Gmail notification email

User login is handled by Petrock. Outbound event notification emails are sent separately through the shared `mit.rex.events@gmail.com` Gmail account via SMTP.

1. Sign in to the Gmail account that will send mail (default: `mit.rex.events@gmail.com`).
2. Enable **2-Step Verification** on that Google account.
3. Open [Google App Passwords](https://myaccount.google.com/apppasswords) and create a password for Tyranno (type: Mail / Other).
4. Add to `.env` locally and to Render environment variables:

```
GMAIL_SENDER_EMAIL=mit.rex.events@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password
```

When `GMAIL_APP_PASSWORD` is not set, local development prints emails to the console instead of sending them.

Production deployment (Render)

Production URL: https://trexdormcon.com

Set these environment variables on Render:

```
DEBUG=false
SECRET_KEY=<django-secret-key>
DATABASE_URL=<neon-postgres-url>
SITE_URL=https://trexdormcon.com
ALLOWED_HOSTS=trexdormcon.com,www.trexdormcon.com
CSRF_TRUSTED_ORIGINS=https://trexdormcon.com,https://www.trexdormcon.com
OIDC_RP_CLIENT_ID=...
OIDC_RP_CLIENT_SECRET=...
GMAIL_SENDER_EMAIL=mit.rex.events@gmail.com
GMAIL_APP_PASSWORD=...
```

Render uses Gunicorn (see `render.yaml`) and runs `collectstatic` at build time. WhiteNoise serves static assets in production.

After deploying, run migrations and create approver `RexUser` records in Django admin. Notification emails link to event pages using `SITE_URL`.

Local development

```
cd archaeo
python manage.py migrate
python manage.py runserver 0.0.0.0:4000
```

Site to streamline REX event submissions.

---------------------------------------------
Uses Django.

Built by DormCon Tech Chair.
