FROM ghcr.io/osgeo/gdal:ubuntu-full-latest

# GDAL/ogr2ogr does the preprocessing; Planetiler (Java) cuts the tiles.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        openjdk-21-jre-headless \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pin a Planetiler release with e.g. --build-arg PLANETILER_VERSION=v0.9.1
ARG PLANETILER_VERSION=latest
RUN set -eux; \
    if [ "$PLANETILER_VERSION" = "latest" ]; then \
        url="https://github.com/onthegomap/planetiler/releases/latest/download/planetiler.jar"; \
    else \
        url="https://github.com/onthegomap/planetiler/releases/download/${PLANETILER_VERSION}/planetiler.jar"; \
    fi; \
    curl -fsSL -o /opt/planetiler.jar "$url"

WORKDIR /app
COPY src/ /app/src/
COPY config/ /app/config/
COPY viewer/ /app/viewer/

ENV PYTHONPATH=/app/src
ENV PLANETILER_JAR=/opt/planetiler.jar

ENTRYPOINT ["python3", "-m", "vt3857"]
