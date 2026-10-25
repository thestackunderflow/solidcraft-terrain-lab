# PrusaSlicer CLI (AGPL-3.0), Debian trixie package 2.9.2+dfsg-1, for headless slicing of the lighthouse STL.
# Base pinned by digest (pulled 2026-10-19). Nothing on the host.
FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends prusa-slicer python3 \
 && rm -rf /var/lib/apt/lists/*
