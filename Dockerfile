FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libfontconfig1 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser && \
    mkdir -p /app/output && \
    chown -R appuser:appuser /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY git_commit_reviewer.py .
COPY .env.example .

RUN mkdir -p /app/output && \
    chown -R appuser:appuser /app/output

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OUTPUT_DIR="/app/output"

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Container healthy'); sys.exit(0)" || exit 1

CMD ["python", "git_commit_reviewer.py", "--help"]