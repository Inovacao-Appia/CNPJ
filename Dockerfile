FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Certificado autoassinado — Entra ID exige redirect URI em https.
# Igual ao padrão já usado no CEDOC (self-signed com IP no SAN).
ARG APP_IP=10.254.255.178
RUN openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
    -keyout /app/.streamlit/key.pem \
    -out /app/.streamlit/cert.pem \
    -subj "/C=BR/ST=SP/L=SaoPaulo/O=ViaAppia/OU=AppiaTools/CN=appia-tools" \
    -addext "subjectAltName=IP:${APP_IP},IP:127.0.0.1,DNS:localhost"

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "Home.py"]
