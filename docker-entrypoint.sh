#!/bin/sh
set -e

CERT_DIR=/app/certs

if [ ! -f "$CERT_DIR/cert.pem" ] || [ ! -f "$CERT_DIR/key.pem" ]; then
    echo "[appia-tools] Gerando certificado autoassinado (primeira vez neste volume)..."
    openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
        -keyout "$CERT_DIR/key.pem" \
        -out "$CERT_DIR/cert.pem" \
        -subj "/C=BR/ST=SP/L=SaoPaulo/O=ViaAppia/OU=AppiaTools/CN=appia-tools" \
        -addext "subjectAltName=IP:${APP_IP:-10.254.255.178},IP:127.0.0.1,DNS:localhost"
else
    echo "[appia-tools] Certificado existente encontrado, mantendo."
fi

exec "$@"
