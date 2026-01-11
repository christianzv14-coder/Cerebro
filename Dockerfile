FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  gcc \
  postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Create directory for SQLite
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV DATABASE_URL=sqlite:///./cerebro.db

# Expose port
EXPOSE 8080

# Run the application with increased timeout
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --timeout-keep-alive 300
