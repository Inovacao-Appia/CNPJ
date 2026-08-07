import os

import streamlit as st


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
