FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/hydrophone

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config ./config
COPY config.example.yaml ./config.example.yaml

ENV PYTHONPATH=/opt/hydrophone/src \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /usr/sbin/nologin hydrophone \
    && mkdir -p /opt/hydrophone/out /config \
    && chown -R hydrophone:hydrophone /opt/hydrophone /config
USER hydrophone

ENTRYPOINT ["python", "-m", "hydrophone_node"]
# Default is one simulated minute, offline. Mount /config/node.yaml and drop
# --dry-run to publish to Supabase from a Pi or a long-running simulator.
CMD ["--config", "/opt/hydrophone/config/poughkeepsie.yaml", "--dry-run", "--replay-speed", "0", "--max-segments", "1"]
