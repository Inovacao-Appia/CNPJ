import base64
from pathlib import Path

import msal
import streamlit as st

from utils.access import buscar_usuario
from utils.config import cfg

_SCOPES = ["User.Read"]
_LOGO_PATH = Path(__file__).resolve().parent.parent / "Logos" / "Via Appia" / "PNG" / "Via Appia Positivo.png"

_LOGIN_CSS = """
<style>
header, [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer,
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
.block-container { padding: 0 !important; max-width: none !important; }
.login-wrap {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f8fafc;
    padding: 1rem;
}
.login-card {
    width: 100%;
    max-width: 420px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.15);
    padding: 2rem 2rem 2.25rem;
    text-align: center;
}
.login-logo {
    display: inline-flex;
    background: #fff;
    border: 1px solid #f1f5f9;
    border-radius: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    padding: 12px 18px;
    margin-bottom: 1.25rem;
}
.login-logo img { height: 32px; width: auto; display: block; }
.login-card h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.01em;
    margin: 0 0 0.25rem;
}
.login-subtitle { color: #64748b; font-size: 1rem; margin: 0 0 1.5rem; }
.login-info {
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
    text-align: left;
    background: rgba(59, 130, 246, 0.06);
    border: 1px solid rgba(59, 130, 246, 0.12);
    border-radius: 10px;
    padding: 0.9rem 1rem;
    font-size: 0.875rem;
    color: #475569;
    margin-bottom: 1.5rem;
}
.ms-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    width: 100%;
    height: 48px;
    background: #0f172a;
    color: #fff !important;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 500;
    text-decoration: none !important;
    transition: background 0.15s ease;
    box-sizing: border-box;
}
.ms-button:hover { background: #1e293b; }
.login-disclaimer { color: #94a3b8; font-size: 0.75rem; margin-top: 1rem; }
</style>
"""


@st.cache_data
def _logo_base64() -> str:
    return base64.b64encode(_LOGO_PATH.read_bytes()).decode()


def build_msal_app():
    return msal.ConfidentialClientApplication(
        client_id=cfg("AZURE_CLIENT_ID"),
        client_credential=cfg("AZURE_CLIENT_SECRET"),
        authority=f"https://login.microsoftonline.com/{cfg('AZURE_TENANT_ID')}",
    )


def _redirect_uri() -> str:
    return cfg("AZURE_REDIRECT_URI")


def _exchange_code(code: str):
    result = build_msal_app().acquire_token_by_authorization_code(
        code, scopes=_SCOPES, redirect_uri=_redirect_uri()
    )
    return result.get("id_token_claims")


def _tela_acesso_negado(email: str):
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="login-wrap">
          <div class="login-card">
            <div class="login-logo">
              <img src="data:image/png;base64,{_logo_base64()}" alt="Via Appia" />
            </div>
            <h1>Acesso não liberado</h1>
            <p class="login-subtitle">{email}</p>
            <div class="login-info">
              <span>🚫</span>
              <span>Sua conta ainda não tem acesso a esta ferramenta. Peça a um administrador para liberar seu email.</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_login():
    """Bloqueia a página (via st.stop()) até o usuário autenticar com a Microsoft (Entra ID)."""
    if "user" in st.session_state:
        return

    code = st.query_params.get("code")

    if code:
        claims = _exchange_code(code)
        st.query_params.clear()
        if claims:
            email = claims.get("preferred_username") or claims.get("email")
            usuario = buscar_usuario(email)
            if usuario and usuario["ativo"]:
                st.session_state["user"] = {
                    "name": claims.get("name") or usuario.get("nome"),
                    "email": email,
                    "role": usuario["role"],
                }
                st.rerun()
            _tela_acesso_negado(email)
            st.stop()
        st.error("Falha ao autenticar com a Microsoft. Tente novamente.")
        st.stop()

    # ponytail: sem validação de "state" — o Streamlit não mantém st.session_state
    # através do redirect para a Microsoft (não usa cookie de sessão, só a conexão
    # WebSocket da aba, que se perde na ida e volta). Guardar e comparar um state
    # aqui nunca bate. Resíduo aceito: login-CSRF (alguém induzir a vítima a abrir um
    # link com um "code" de UMA CONTA MICROSOFT DO ATACANTE, o que logaria a vítima
    # como o atacante — não vaza dados da vítima). Upgrade: cookie assinado
    # (ex.: extra-streamlit-components) guardando o state esperado, se isso importar.
    auth_url = build_msal_app().get_authorization_request_url(
        _SCOPES, redirect_uri=_redirect_uri()
    )

    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="login-wrap">
          <div class="login-card">
            <div class="login-logo">
              <img src="data:image/png;base64,{_logo_base64()}" alt="Via Appia" />
            </div>
            <h1>Appia Tools</h1>
            <p class="login-subtitle">Ferramentas internas de automação</p>
            <div class="login-info">
              <span>🛡️</span>
              <span>O acesso é restrito aos colaboradores autorizados. Utilize sua conta corporativa da Microsoft.</span>
            </div>
            <a class="ms-button" href="{auth_url}" target="_self">
              <svg viewBox="0 0 21 21" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 0H0V10H10V0Z" fill="#F25022"/>
                <path d="M21 0H11V10H21V0Z" fill="#7FBA00"/>
                <path d="M10 11H0V21H10V11Z" fill="#00A4EF"/>
                <path d="M21 11H11V21H21V11Z" fill="#FFB900"/>
              </svg>
              Entrar com Microsoft
            </a>
            <p class="login-disclaimer">Ao entrar, você concorda com as políticas de acesso da Via Appia.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


_ACCOUNT_CSS = """
<style>
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] hr { margin: 0.75rem 0 1rem; opacity: 0.15; }
.account-block { display: flex; align-items: center; gap: 0.6rem; padding: 0 0.1rem 0.85rem; }
.account-avatar {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: rgba(59, 130, 246, 0.18);
    color: #93c5fd;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
}
.account-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: #e2e8f0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
[data-testid="stSidebar"] button {
    background: transparent !important;
    border: 1px solid rgba(148, 163, 184, 0.3) !important;
    color: #94a3b8 !important;
    font-size: 0.8rem !important;
}
[data-testid="stSidebar"] button:hover {
    border-color: rgba(148, 163, 184, 0.6) !important;
    color: #e2e8f0 !important;
}
</style>
"""


def logout_button():
    user = st.session_state.get("user")
    if not user:
        return
    nome = user.get("name") or user.get("email") or "Usuário"
    inicial = nome.strip()[0].upper() if nome.strip() else "?"

    st.sidebar.divider()
    st.sidebar.markdown(_ACCOUNT_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(
        f"""
        <div class="account-block">
          <div class="account-avatar">{inicial}</div>
          <div class="account-name">{nome}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()
