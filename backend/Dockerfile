FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Shared requirements live at the project root, so build with the
# repo root as context:  docker build -f backend/Dockerfile -t secureguard-backend .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
