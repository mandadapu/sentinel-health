FROM rust:1.83-slim AS rust-builder

WORKDIR /rust
COPY rust/ .
RUN cargo build --release

FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY --from=rust-builder /rust/target/release/*.so /app/lib/
COPY src/ src/

EXPOSE 8081

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8081"]
