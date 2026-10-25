# syntax=docker/dockerfile:1.7
# Ninefruits application image (porting-plan 5.4): python:3.14-slim, uv, non-root.
# Targets: `production` (default; gunicorn, built assets, no dev tools) and `development`
# (dev dependency group, used by compose.yaml with the source mounted).

ARG PYTHON_VERSION=3.14
ARG NODE_VERSION=22

# --- Frontend assets (static/dist/manifest.json) ---------------------------------------------
FROM node:${NODE_VERSION}-alpine AS assets
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY vite.config.js ./
COPY frontend ./frontend
COPY templates ./templates
COPY ninefruits ./ninefruits
RUN npm run build

# --- Base: system packages, uv, unprivileged user --------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext libmagic1 postgresql-client \
    && rm -rf /var/lib/apt/lists/*
ARG UV_VERSION=0.11.32
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app /opt/venv \
    && chown app:app /app /opt/venv
WORKDIR /app

# --- Development ------------------------------------------------------------------------------
FROM base AS development
USER app
COPY --chown=app:app pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/app/.cache/uv,uid=1000,gid=1000 \
    UV_CACHE_DIR=/app/.cache/uv uv sync --frozen --no-install-project
COPY --chown=app:app . .
EXPOSE 8000
CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]

# --- Production -------------------------------------------------------------------------------
FROM base AS production
USER app
COPY --chown=app:app pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/app/.cache/uv,uid=1000,gid=1000 \
    UV_CACHE_DIR=/app/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY --chown=app:app . .
COPY --from=assets --chown=app:app /build/static/dist ./static/dist
ENV DJANGO_SETTINGS_MODULE=config.settings.production
RUN DJANGO_SECRET_KEY=build-only uv run --no-sync manage.py compilemessages --ignore=.venv \
    && DJANGO_SECRET_KEY=build-only uv run --no-sync manage.py collectstatic --noinput
EXPOSE 8000
# Worker count and the rest: config/gunicorn.py (GUNICORN_* variables, operations manual, load testing).
ENV GUNICORN_BIND=0.0.0.0:8000 GUNICORN_ACCESS_LOG=-
CMD ["uv", "run", "--no-sync", "gunicorn", "config.wsgi", "-c", "config/gunicorn.py"]
