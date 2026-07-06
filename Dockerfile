FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir /service
WORKDIR /service

RUN apk update && apk add --no-cache \
    bash curl gcc g++ make libc-dev libffi-dev \
    git \
    make \
    build-base \
    postgresql-dev \
    musl-dev \
    librdkafka-dev \
    openssl-dev \
    cyrus-sasl-dev \
    && rm -rf /var/cache/apk/*

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput


CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
