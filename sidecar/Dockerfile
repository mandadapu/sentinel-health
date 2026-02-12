FROM rust:1.83-slim AS rust-builder

RUN pip install maturin

WORKDIR /rust
COPY rust/ .
RUN maturin build --release --out /rust/dist

FROM python:3.12-slim AS base

RUN groupadd -r sentinel && useradd -r -g sentinel -d /app -s /sbin/nologin sentinel

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY --from=rust-builder /rust/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

COPY src/ src/
COPY schemas/ schemas/

RUN chown -R sentinel:sentinel /app

USER sentinel

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8081"]
