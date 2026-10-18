# evac-ai API + UI for IBM LinuxONE (s390x). Base image is multi-arch; every heavy dependency comes from
# Ubuntu's s390x packages (pip has no s390x wheels for numpy/scipy/sklearn/rasterio).

# Stage 1: compile prediction mode's C search once (keeps gcc out of the runtime image).
FROM ubuntu:24.04 AS cbuild
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev libzdnn-dev && rm -rf /var/lib/apt/lists/*
COPY engine/escape_search.c /src/
COPY scripts/nnpa/zdnn_mlp.c /src/
# Same name escape.py looks for: escape_search-<first 10 hex of sha1(source)>.so
RUN mkdir -p /opt/evac-build && TAG=$(sha1sum /src/escape_search.c | cut -c1-10)     && gcc -O2 -shared -fPIC -o /opt/evac-build/escape_search-$TAG.so /src/escape_search.c -lm
# What-if floods on the Telum AI accelerator (engine/surrogate.py): the zDNN forward pass
RUN gcc -O2 -shared -fPIC -o /opt/evac-build/zdnn_mlp.so /src/zdnn_mlp.c -lzdnn

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-numpy python3-scipy python3-sklearn python3-pandas \
      python3-rasterio python3-shapely python3-pyproj python3-pil grass-core gdal-bin curl ca-certificates libzdnn0 \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/venv && /opt/venv/bin/pip install --no-cache-dir fastapi uvicorn
WORKDIR /app
COPY engine/ engine/
COPY models/ models/
COPY api/ api/
COPY web/ web/
# 3D replay, served by the API at /viewer/ (bake scripts and tests stay out of the image)
COPY viewer/index.html viewer/
COPY viewer/js/ viewer/js/
COPY viewer/vendor/ viewer/vendor/
COPY viewer/data/ viewer/data/
COPY replay/ replay/
COPY pipeline/ pipeline/
# data/ (DEM products, OSM, GRASS db) is mounted at runtime: -v $PWD/data:/app/data
# Prebuilt (named by the source hash), so escape.py finds it and never calls cc at runtime.
COPY --from=cbuild /opt/evac-build/ /opt/evac-build/
ENV EVAC_BUILD_DIR=/opt/evac-build EVAC_NNPA_LIB=/opt/evac-build/zdnn_mlp.so
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=30s CMD curl -fs localhost:8000/api/replays || exit 1
CMD ["/opt/venv/bin/uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
