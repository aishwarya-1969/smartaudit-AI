FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && mkdir -p /data
COPY backend backend
COPY frontend frontend
ENV DB_PATH=/data/smartaudit.db OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /app/backend
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
