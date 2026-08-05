#==========================
# etransfer builder stage
#==========================
FROM debian:bookworm-slim AS etransfer-builder 

RUN apt-get update && apt-get install -y gcc g++ make git 

WORKDIR /build 

RUN git clone --branch v2.0 https://github.com/jive-vlbi/etransfer.git

RUN sed -i 's/MACHINE),arm64)/MACHINE),aarch64)/' /build/etransfer/libudt5ab/Makefile

RUN sed -i 's/MACHINE),arm64)/MACHINE),aarch64)/' /build/etransfer/libsrt5ab/Makefile

RUN cd etransfer && make 


#==========================
# main application image
#==========================
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

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


#================
# etransfer
#================
# Putting this here means that every additional simulator image will contain both executables.
# Only the VLBA simulator ever calls etc.
# Only the ETD container ever runs etd.
COPY --from=etransfer-builder /build/etransfer/*-native-opt/etc /usr/local/bin/
COPY --from=etransfer-builder /build/etransfer/*-native-opt/etd /usr/local/bin/

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
