# Build v3.0.6 - HOTFIX (Backend Consistent User Lookup)
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/static /app/app/static
COPY . .

# Use shell form to allow variable expansion for $PORT
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
