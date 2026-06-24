# This has not been tested at all.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for Postgres compiled drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# FIXED: Copies into your active workdir root (/app/) to match execution paths
COPY . /app/

# Expose port 8000 for web delivery configurations
EXPOSE 8000

CMD ["gunicorn", "ngRadar_Website.wsgi:application", "--bind", "0.0.0.0:8000"]
