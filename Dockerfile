FROM python:3.13-slim

COPY LICENSE /LICENSE

EXPOSE 5000
ENV PORT=5000
ENV WORKERS=2
ENV THREADS=4
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=true

# nginx in front of gunicorn serves the static files (docker/nginx.conf)
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

# The versions are locked in uv.lock.
COPY pyproject.toml uv.lock* README.md ./
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --no-dev --no-install-project --frozen || uv sync --no-dev --no-install-project

COPY manage.py REUSE.toml ./
COPY LICENSES LICENSES
COPY ai_pycal ai_pycal
COPY static static
COPY docker/start-service.sh docker/healthcheck.py ./
COPY docker/nginx.conf docker/nginx.conf
# throwaway key: nothing secret is written into the image
RUN SECRET_KEY=build python manage.py collectstatic --noinput

VOLUME /app/data
HEALTHCHECK --start-period=60s --start-interval=5s --interval=30s --timeout=10s --retries=3 \
    CMD python healthcheck.py
ENTRYPOINT ["/bin/sh", "start-service.sh"]
