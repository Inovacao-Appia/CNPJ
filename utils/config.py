import os

import psycopg2
import streamlit as st

FAVICON_PATH = "Logos/Via Appia/PNG/favicon.png"


def cfg(key: str):
    """Lê uma variável de configuração: env var primeiro (Docker/produção),
    com fallback para st.secrets (uso local via .streamlit/secrets.toml).
    st.secrets lança exceção (em vez de retornar None) quando não há nenhum
    secrets.toml no ambiente — por isso o try/except em vez de um .get() direto."""
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def get_db_conn():
    dsn = cfg("DATABASE_URL")
    if not dsn:
        return None
    return psycopg2.connect(dsn)
