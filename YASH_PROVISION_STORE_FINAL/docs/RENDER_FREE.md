# Render deployment — current free-tier reality

1. Push this repository to GitHub.
2. In Render, create a PostgreSQL database first if you want a real Postgres service.
3. Create a Docker Web Service from the GitHub repository.
4. Use `backend/Dockerfile` and the repository root as Docker context.
5. Set `DATABASE_URL` to the Render Postgres **internal** connection string.
6. Set `SECRET_KEY` to a long random value. Do not commit it.
7. Set `CORS_ORIGINS` to the final `https://<service>.onrender.com` URL after you know it.
8. Deploy and open `/api/health`.
9. Open the app, log in, change credentials, create a test product, scan/type its barcode, sell it, create an order, cancel/complete it, test a return, and download a backup.

### Free-tier limitation
The Render Free web service can spin down after 15 minutes of inactivity. Free Render Postgres is 1 GB and expires 30 days after creation; Render also states that Free Postgres has no backups. Therefore **do not treat the free database as permanent business storage**. Keep regular owner-exported backups and upgrade the database before the 30-day deadline if the store becomes real.

### Images
V5 stores product images in PostgreSQL rather than the web container filesystem, so redeploying the web service does not remove product images. This is a practical free-tier strategy but consumes database storage.

### Migrations
Render's documented pre-deploy command feature is not available on the Free web-service plan. V5 therefore keeps schema creation compatible with first deployment. When you move to a paid production plan, add an Alembic migration step before deploy and manage revisions as normal.

### Free deployment cannot guarantee
- 24/7 always-on response
- permanent free Postgres
- free managed database backups
- production-grade SLA

For a real shop, “free forever” and “production-safe” are conflicting requirements on this platform.
