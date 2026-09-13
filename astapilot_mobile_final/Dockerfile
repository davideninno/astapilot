FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY mobile /app/mobile
ENV PYTHONPATH=/app/backend ASTAPILOT_DB=/data/astapilot.sqlite3 ASTAPILOT_APP_URL=http://localhost:8000
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn","app.main:app","--app-dir","/app/backend","--host","0.0.0.0","--port","8000"]
FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY mobile /app/mobile

ENV PYTHONPATH=/app/backend
ENV ASTAPILOT_DB=/data/astapilot.sqlite3

RUN mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}"]
