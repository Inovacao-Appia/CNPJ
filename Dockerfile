FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HTTPS público é terminado no IIS (portalcnpj.viaappia.com.br), que encaminha
# pra cá em HTTP simples — não precisa de certificado neste container.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "Home.py"]
