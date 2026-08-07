import msal
import streamlit as st

from utils.config import cfg

_SCOPES = ["User.Read"]


def _build_msal_app():
    return msal.ConfidentialClientApplication(
        client_id=cfg("AZURE_CLIENT_ID"),
        client_credential=cfg("AZURE_CLIENT_SECRET"),
        authority=f"https://login.microsoftonline.com/{cfg('AZURE_TENANT_ID')}",
    )


def _redirect_uri() -> str:
    return cfg("AZURE_REDIRECT_URI")


def _exchange_code(code: str):
    result = _build_msal_app().acquire_token_by_authorization_code(
        code, scopes=_SCOPES, redirect_uri=_redirect_uri()
    )
    return result.get("id_token_claims")


def require_login():
    """Bloqueia a página (via st.stop()) até o usuário autenticar com a Microsoft (Entra ID)."""
    if "user" in st.session_state:
        return

    code = st.query_params.get("code")

    if code:
        claims = _exchange_code(code)
        st.query_params.clear()
        if claims:
            st.session_state["user"] = {
                "name": claims.get("name"),
                "email": claims.get("preferred_username") or claims.get("email"),
            }
            st.rerun()
        st.error("Falha ao autenticar com a Microsoft. Tente novamente.")
        st.stop()

    # ponytail: sem validação de "state" — o Streamlit não mantém st.session_state
    # através do redirect para a Microsoft (não usa cookie de sessão, só a conexão
    # WebSocket da aba, que se perde na ida e volta). Guardar e comparar um state
    # aqui nunca bate. Resíduo aceito: login-CSRF (alguém induzir a vítima a abrir um
    # link com um "code" de UMA CONTA MICROSOFT DO ATACANTE, o que logaria a vítima
    # como o atacante — não vaza dados da vítima). Upgrade: cookie assinado
    # (ex.: extra-streamlit-components) guardando o state esperado, se isso importar.
    auth_url = _build_msal_app().get_authorization_request_url(
        _SCOPES, redirect_uri=_redirect_uri()
    )

    st.title("Appia Tools")
    st.info("Faça login com sua conta Microsoft (Entra ID) para continuar.")
    st.link_button("🔐 Entrar com Microsoft", auth_url)
    st.stop()


def logout_button():
    user = st.session_state.get("user")
    if not user:
        return
    st.sidebar.divider()
    st.sidebar.caption(f"👤 {user.get('name') or user.get('email') or 'Usuário'}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
