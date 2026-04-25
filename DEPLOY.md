# Deploy Focus-AI

This project is not a static-only site anymore.
It has a Python backend in `server.py` for:

- saving responses
- protecting the admin dashboard with login credentials
- serving the site

Because of that, do not deploy it to a static host like GitHub Pages.

## Recommended option: Render

1. Push this project to GitHub.
2. Create a new Web Service on Render.
3. Connect the repository.
4. Use these settings:

   - Runtime: `Python`
   - Build Command: `python3 --version`
   - Start Command: `python3 server.py`

5. Add environment variables:

   - `FOCUS_AI_ADMIN_USERNAME=your-admin-username`
   - `FOCUS_AI_ADMIN_PASSWORD=your-real-password`
   - `FOCUS_AI_SECURE_COOKIES=1`

6. Deploy.

## Connect your domain

After deployment on Render:

1. Open the service dashboard.
2. Go to `Settings` -> `Custom Domains`.
3. Add your domain, for example `app.yourdomain.com`.
4. Update your DNS records at your domain provider exactly as Render shows.
5. Wait for DNS verification and SSL certificate issuance.

## Persistent feedback storage

This app now stores responses in SQLite.

By default it uses a stable SQLite file path.

On local machines, the default is:

```text
~/.focus-ai/focus_ai.db
```

This keeps your data outside the project folder, so normal frontend/backend code changes do not affect your saved responses.

In hosted environments, it uses whatever you set in `FOCUS_AI_DB_PATH`.

Example old in-project location:

```text
focus_ai.db
```

For real hosting, put the database on persistent storage.

On Render, the recommended setup is:

1. Add a persistent disk to the service.
2. Mount it at `/var/data`.
3. Add this environment variable:

   - `FOCUS_AI_DB_PATH=/var/data/focus_ai.db`

This ensures user feedback survives redeploys and restarts.

The app also migrates existing data from `responses-data.json` into SQLite automatically the first time the database is initialized.

## Local run

Use:

```bash
python3 server.py
```

With `.env` containing:

```env
FOCUS_AI_ADMIN_USERNAME=admin
FOCUS_AI_ADMIN_PASSWORD=your-password
FOCUS_AI_SECURE_COOKIES=0
FOCUS_AI_DB_PATH=/absolute/path/to/your/stable/focus_ai.db
```

`FOCUS_AI_RESPONSES_PASSWORD` is still accepted as a fallback for backward compatibility, but new deployments should use `FOCUS_AI_ADMIN_PASSWORD`.