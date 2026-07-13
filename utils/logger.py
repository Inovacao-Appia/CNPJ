import streamlit as st
from supabase import create_client

from utils.contratos import COLUMNS


def _get_client():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def registrar_nf(arquivo: str, dados: dict, status: str = "sucesso", erro: str = None):
    client = _get_client()
    if not client:
        return
    try:
        client.table("logs_nf").insert({
            "arquivo": arquivo,
            "num_nota": dados.get("numero_nota"),
            "data_emissao": dados.get("data_emissao"),
            "prestador": dados.get("nome_prestador"),
            "valor_bruto": str(dados.get("valor_bruto", "")),
            "valor_liquido": str(dados.get("valor_liquido", "")),
            "status": status,
            "erro": erro,
        }).execute()
    except Exception as e:
        st.warning(f"Falha ao registrar log: {e}")


def buscar_logs() -> list[dict]:
    client = _get_client()
    if not client:
        return []
    try:
        resp = client.table("logs_nf").select("*").order("timestamp", desc=True).execute()
        return resp.data
    except Exception:
        return []


def registrar_contrato(nome_grupo: str, arquivos: list[str], dados: dict, status: str = "sucesso", erro: str = None):
    client = _get_client()
    if not client:
        return
    try:
        registro = {chave: dados.get(chave) for chave, _rotulo in COLUMNS}
        registro.update({
            "arquivo": nome_grupo,
            "arquivos_origem": ", ".join(arquivos),
            "status": status,
            "erro": erro,
        })
        client.table("logs_contratos").insert(registro).execute()
    except Exception as e:
        st.warning(f"Falha ao registrar log: {e}")


def buscar_logs_contratos() -> list[dict]:
    client = _get_client()
    if not client:
        return []
    try:
        resp = client.table("logs_contratos").select("*").order("timestamp", desc=True).execute()
        return resp.data
    except Exception:
        return []
