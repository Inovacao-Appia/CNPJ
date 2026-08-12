import streamlit as st

from utils.auth import logout_button, require_login
from utils.config import FAVICON_PATH
from utils.paginas import PAGINAS, PAGINA_ADMIN

st.set_page_config(page_title="Appia Tools", layout="wide", page_icon=FAVICON_PATH)

require_login()


def _inicio():
    st.title("Appia Tools")
    st.write("Selecione uma ferramenta no menu lateral.")


usuario = st.session_state["user"]
bloqueadas = set(usuario.get("paginas_bloqueadas") or [])

paginas = [st.Page(_inicio, title="Início", icon="🏠", default=True)]
paginas += [
    st.Page(p["path"], title=p["title"], icon=p["icon"])
    for p in PAGINAS
    if p["key"] not in bloqueadas
]
if usuario.get("role") == "admin":
    paginas.append(st.Page(PAGINA_ADMIN["path"], title=PAGINA_ADMIN["title"], icon=PAGINA_ADMIN["icon"]))

st.logo("Logos/Via Appia/PNG/Via Appia Negativo.png", size="large")
logout_button()

pg = st.navigation(paginas)
pg.run()
