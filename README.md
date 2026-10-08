
# Stock Inventory MGM

## Deploying to Vercel

This is a Django WSGI project. Import the repository into Vercel with the
repository root as the project root. Vercel detects `manage.py`,
`inventory_config.settings`, and the WSGI application automatically; no custom
`vercel.json` or separate build command is needed. Vercel also collects and
serves Django static files from `STATIC_ROOT`.

### Required environment variables

Set these for every Vercel environment in which you deploy (Production and
Preview, as needed):

- `SECRET_KEY`: a long, random Django secret. Do not reuse the development
  value or commit this secret.
- `DATABASE_URL`: a URL for a persistent PostgreSQL database. Vercel's
  function filesystem is temporary, so the local SQLite database is not
  suitable for production.

The project automatically allows Vercel's `VERCEL_URL` and
`VERCEL_PROJECT_PRODUCTION_URL` hostnames and trusts their HTTPS origins for
CSRF. If you use a custom domain, also set:

- `ALLOWED_HOSTS`: comma-separated hostnames, without `https://`.
- `CSRF_TRUSTED_ORIGINS`: comma-separated full origins, including `https://`.

For example, use `inventory.example.com` for `ALLOWED_HOSTS` and
`https://inventory.example.com` for `CSRF_TRUSTED_ORIGINS`.

### Database setup

After the first deployment, run Django migrations against the same production
database referenced by `DATABASE_URL`:

```powershell
python manage.py migrate
```

Run this from a local checkout configured with the production database
environment variable, or from an environment with access to that database.
Create an administrator separately with `python manage.py createsuperuser`.
Do not run migrations against the database bundled in the repository.

### Email and uploaded files

Configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` if the app's
email features should work. Without SMTP credentials, email delivery will
fail when those features are used.

Uploaded logos, avatars, and product images currently use Django's local
`MEDIA_ROOT`. Vercel's filesystem is temporary, so use persistent object
storage before relying on uploaded files in production; otherwise uploads may
disappear between function instances or deployments.
