FROM debian:bookworm-slim AS builder 

RUN apt-get update && apt-get install -y gcc g++ make git 

WORKDIR /build 

RUN git clone --branch v2.0 https://github.com/jive-vlbi/etransfer.git

RUN sed -i 's/MACHINE),arm64)/MACHINE),aarch64)/' /build/etransfer/libudt5ab/Makefile

RUN sed -i 's/MACHINE),arm64)/MACHINE),aarch64)/' /build/etransfer/libsrt5ab/Makefile

RUN cd etransfer && make 