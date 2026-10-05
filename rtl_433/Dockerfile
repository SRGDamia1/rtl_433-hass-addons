# syntax=docker/dockerfile:1

ARG BUILD_FROM=ghcr.io/home-assistant/base:3.24
FROM $BUILD_FROM AS builder

ENV LANG=C.UTF-8

# Copied with minor edits from https://github.com/hertzg/rtl_433_docker/blob/master/images/alpine/build-context/Dockerfile
RUN apk add --no-cache --virtual .buildDeps \
    build-base \
    libusb-dev \
    hackrf \
    hackrf-dev \
    librtlsdr-dev \
    soapy-sdr \
    soapy-sdr-dev \
    openssl-dev \
    cmake \
    git

WORKDIR /build

FROM builder AS rtl_433_builder

# Resolve master on every build so new commits invalidate the source cache.
# Keep Git metadata for rtl_433's version and commit reporting.
ADD --keep-git-dir=true https://github.com/merbanan/rtl_433.git#master /build/rtl_433
WORKDIR /build/rtl_433
WORKDIR ./build
RUN cmake ..
RUN make -j 4

WORKDIR /build/root
WORKDIR /build/rtl_433/build
RUN make DESTDIR=/build/root/ install

FROM builder AS soapy_hackrf_builder
RUN git clone https://github.com/pothosware/SoapyHackRF.git
WORKDIR SoapyHackRF
RUN git checkout 6c0c33f0aa44c3080674e6bca0273184d3e9eb44
WORKDIR build
# This pinned plugin predates CMake 4's minimum policy version.
RUN cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
RUN make -j4
RUN make DESTDIR=/build/soapy-root/ install

FROM $BUILD_FROM

ARG BUILD_VERSION=dev
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.source="https://github.com/SRGDamia1/rtl_433-hass-addons"

ENV LANG=C.UTF-8

RUN apk add --no-cache libusb \
    hackrf \
    librtlsdr \
    soapy-sdr \
    sed \
    libssl3 \
    libcrypto3 \
    mosquitto-clients
WORKDIR /root
COPY --from=rtl_433_builder /build/root/ /

COPY --from=soapy_hackrf_builder /build/soapy-root/ /

# Run script
COPY run.sh /
RUN chmod a+x /run.sh

# Expose rtl_433 web interface port
EXPOSE 8433 8434

CMD [ "/run.sh" ]
