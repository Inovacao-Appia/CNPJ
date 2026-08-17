import streamlit as st

from utils.auth import logout_button, require_login
from utils.config import FAVICON_PATH
from utils.paginas import PAGINAS, PAGINA_ADMIN


def _inicio():
    st.title("Appia Tools")
    st.write("Selecione uma ferramenta no menu lateral.")


# Streamlit executa este arquivo como "__main__" — mas os workers do
# ProcessPoolExecutor (mp_context="spawn") também reimportam o script que o
# processo principal usou como entrypoint, só que com __name__ = "__mp_main__"
# (convenção do multiprocessing, ver docs: "Safe importing of main module"),
# exatamente pra evitar reexecutar código de nível de módulo indevidamente.
# Sem esse guard, cada worker novo tentava rodar isto de novo fora do runtime
# do Streamlit e quebrava em st.session_state["user"] (sem sessão real ali).
if __name__ == "__main__":
    st.set_page_config(page_title="Appia Tools", layout="wide", page_icon=FAVICON_PATH)

    require_login()

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
