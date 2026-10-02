# Render Deployment

1. Push this repository to GitHub.
2. Create a Render PostgreSQL database.
3. Create the web service from `render.yaml`.
4. Set `DATABASE_URL` to the Render PostgreSQL connection string.
5. Set a strong `SECRET_KEY`.
6. Set `CORS_ORIGINS` to the final HTTPS origin.
7. For UPI, set `UPI_VPA` and `UPI_MERCHANT_NAME`.
8. For real AI, set `AI_PROVIDER` and the corresponding provider API key.
9. Deploy.

The Docker startup command runs `alembic upgrade head` before Uvicorn.

## Health

- `/api/health` — process health
- `/api/readiness` — database readiness

## Free vs business production

Render's free/test infrastructure should be treated as a development/demo environment. Do not assume free service availability or free PostgreSQL storage constitutes permanent business-grade backup/retention. Use a paid/reliable database and an independently tested backup/restore process for a real store.
