FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir /service
WORKDIR /service

# Switching to Debian dependencies instead of Alpine ones
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    gcc \
    g++ \
    make \
    git \
    libpq-dev \
    librdkafka-dev \
    libffi-dev \
    libssl-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=etransfer-builder:latest /build/etransfer/*-native-opt/etc /usr/local/bin/

COPY --from=etransfer-builder:latest /build/etransfer/*-native-opt/etd /usr/local/bin/

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
