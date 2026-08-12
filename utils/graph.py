import requests
import streamlit as st

from utils.auth import build_msal_app

_GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def _app_token() -> str | None:
    """Token app-only (client credentials) — precisa da permissão de aplicativo
    'User.Read.All' (Microsoft Graph) concedida com consentimento de admin no
    mesmo App Registration usado pelo login."""
    result = build_msal_app().acquire_token_for_client(scopes=_GRAPH_SCOPE)
    return result.get("access_token")


def buscar_usuarios_entra(busca: str, limite: int = 25) -> list[dict]:
    """Busca usuários no diretório do Entra ID por nome ou email. Retorna
    [{"nome": ..., "email": ...}]. Lista vazia se a busca falhar (sem
    permissão, tenant sem acesso, etc.) — a tela mostra o aviso."""
    if not busca or not busca.strip():
        return []

    token = _app_token()
    if not token:
        st.warning("Não foi possível obter token do Microsoft Graph.")
        return []

    termo = busca.strip().replace("'", "''")
    filtro = (
        f"(startswith(displayName,'{termo}') or startswith(mail,'{termo}') "
        f"or startswith(userPrincipalName,'{termo}')) and userType eq 'Member'"
    )

    resp = requests.get(
        "https://graph.microsoft.com/v1.0/users",
        headers={"Authorization": f"Bearer {token}", "ConsistencyLevel": "eventual"},
        params={
            "$filter": filtro,
            "$select": "displayName,mail,userPrincipalName",
            "$top": limite,
            "$count": "true",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        st.warning(f"Falha ao buscar no Entra ID ({resp.status_code}): {resp.text[:300]}")
        return []

    usuarios = []
    for u in resp.json().get("value", []):
        email = u.get("mail") or u.get("userPrincipalName")
        if email:
            usuarios.append({"nome": u.get("displayName") or "", "email": email})
    return usuarios
