#!/bin/bash
set -euo pipefail

# Generate self-signed dev certificates for mTLS between orchestrator and sidecar.
# Usage: bash certs/generate-dev-certs.sh
#
# Produces:
#   certs/ca.pem          — CA certificate (trusted by both sides)
#   certs/ca-key.pem      — CA private key
#   certs/server.pem      — Server certificate (sidecar)
#   certs/server-key.pem  — Server private key (sidecar)
#   certs/client.pem      — Client certificate (orchestrator backend)
#   certs/client-key.pem  — Client private key (orchestrator backend)

CERT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Generating dev mTLS certificates in ${CERT_DIR}..."

# CA
openssl genrsa -out "${CERT_DIR}/ca-key.pem" 4096 2>/dev/null
openssl req -new -x509 \
    -key "${CERT_DIR}/ca-key.pem" \
    -out "${CERT_DIR}/ca.pem" \
    -days 3650 \
    -subj "/CN=Sentinel-Health-Dev-CA" 2>/dev/null

# Server cert (sidecar) — SANs: sidecar, localhost
openssl genrsa -out "${CERT_DIR}/server-key.pem" 2048 2>/dev/null
openssl req -new \
    -key "${CERT_DIR}/server-key.pem" \
    -out "${CERT_DIR}/server.csr" \
    -subj "/CN=sidecar" 2>/dev/null
openssl x509 -req \
    -in "${CERT_DIR}/server.csr" \
    -CA "${CERT_DIR}/ca.pem" \
    -CAkey "${CERT_DIR}/ca-key.pem" \
    -CAcreateserial \
    -out "${CERT_DIR}/server.pem" \
    -days 365 \
    -extfile <(printf "subjectAltName=DNS:sidecar,DNS:localhost") 2>/dev/null

# Client cert (orchestrator)
openssl genrsa -out "${CERT_DIR}/client-key.pem" 2048 2>/dev/null
openssl req -new \
    -key "${CERT_DIR}/client-key.pem" \
    -out "${CERT_DIR}/client.csr" \
    -subj "/CN=orchestrator" 2>/dev/null
openssl x509 -req \
    -in "${CERT_DIR}/client.csr" \
    -CA "${CERT_DIR}/ca.pem" \
    -CAkey "${CERT_DIR}/ca-key.pem" \
    -CAcreateserial \
    -out "${CERT_DIR}/client.pem" \
    -days 365 2>/dev/null

# Clean up CSR files
rm -f "${CERT_DIR}/server.csr" "${CERT_DIR}/client.csr" "${CERT_DIR}/ca.srl"

echo "Dev certificates generated:"
echo "  CA:     ${CERT_DIR}/ca.pem"
echo "  Server: ${CERT_DIR}/server.pem + server-key.pem"
echo "  Client: ${CERT_DIR}/client.pem + client-key.pem"
