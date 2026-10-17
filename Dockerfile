# evac-ai API + UI for IBM LinuxONE (s390x). Base image is multi-arch; every heavy dependency comes from
# Ubuntu's s390x packages (pip has no s390x wheels for numpy/scipy/sklearn/rasterio).

# Stage 1: compile prediction mode's C search once (keeps gcc out of the runtime image).
FROM ubuntu:24.04 AS cbuild
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
COPY engine/escape_search.c /src/
RUN mkdir -p /opt/evac-build && gcc -O2 -shared -fPIC -o /opt/evac-build/escape_search.so /src/escape_search.c -lm

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-numpy python3-scipy python3-sklearn python3-pandas \
      python3-rasterio python3-shapely python3-pyproj grass-core gdal-bin curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/venv && /opt/venv/bin/pip install --no-cache-dir fastapi uvicorn
WORKDIR /app
COPY engine/ engine/
COPY models/ models/
COPY api/ api/
COPY web/ web/
COPY replay/ replay/
COPY pipeline/ pipeline/
# data/ (DEM products, OSM, GRASS db) is mounted at runtime: -v $PWD/data:/app/data
# Prebuilt; touched after engine/ is copied so it is always newer than escape_search.c and escape.py never calls cc.
COPY --from=cbuild /opt/evac-build/escape_search.so /opt/evac-build/escape_search.so
RUN touch /opt/evac-build/escape_search.so
ENV EVAC_BUILD_DIR=/opt/evac-build
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=30s CMD curl -fs localhost:8000/api/replays || exit 1
CMD ["/opt/venv/bin/uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
