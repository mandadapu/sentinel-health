FROM rust:1.83-slim AS rust-builder

RUN pip install maturin

WORKDIR /rust
COPY rust/ .
RUN maturin build --release --out /rust/dist

FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY --from=rust-builder /rust/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

COPY src/ src/
COPY schemas/ schemas/

EXPOSE 8081

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8081"]
