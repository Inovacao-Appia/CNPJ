FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Certificado autoassinado — Entra ID exige redirect URI em https. Gerado em
# runtime (docker-entrypoint.sh) dentro de um volume, não aqui no build, para
# não trocar de certificado (e derrubar a confiança já dada pelo usuário) a
# cada rebuild da imagem.
RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /app/certs \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["streamlit", "run", "Home.py"]
