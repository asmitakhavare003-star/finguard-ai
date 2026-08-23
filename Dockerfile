# syntax=docker/dockerfile:1
# FinGuard AI — production multi-stage image

############################
# Stage 1: builder
############################
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Compiler toolchain for any packages that need native extensions.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels once in the builder so the runner stays slim.
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


############################
# Stage 2: runner
############################
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Minimal runtime OS deps (certs for HTTPS to OpenAI / LangSmith).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser

# Install pre-built wheels from the builder stage (no compilers in runner).
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code only — secrets come from env / mounted .env at runtime.
COPY app/ ./app/
COPY data/ ./data/

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
