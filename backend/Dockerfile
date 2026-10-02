FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY --from=frontend /frontend/dist ./app/static
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
EXPOSE 8000
CMD ["sh","-c","alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
