import pandas as pd
import streamlit as st

from utils.access import excluir_usuario, listar_usuarios, salvar_usuario
from utils.auth import logout_button, require_login
from utils.config import FAVICON_PATH
from utils.graph import buscar_usuarios_entra

st.set_page_config(page_title="Appia Tools", layout="wide", page_icon=FAVICON_PATH)

require_login()

st.logo("Logos/Via Appia/PNG/Via Appia Negativo.png", size="large")
logout_button()

st.title("🔐 Administração")

if st.session_state["user"].get("role") != "admin":
    st.error("Acesso restrito a administradores.")
    st.stop()

tab_cadastrados, tab_entra = st.tabs(["Usuários Cadastrados", "Importar do Entra ID"])

# =============================
# ABA: USUÁRIOS CADASTRADOS
# =============================
with tab_cadastrados:
    st.write("Usuários com acesso à plataforma. Só quem está listado aqui (e ativo) consegue logar.")

    busca = st.text_input("Buscar por email ou nome", key="busca_usuarios")
    usuarios = listar_usuarios(busca)

    df = pd.DataFrame(usuarios, columns=["email", "nome", "role", "ativo", "criado_em"])
    if "criado_em" in df.columns:
        df = df.drop(columns=["criado_em"])

    st.caption("Edite direto na tabela (papel, ativo) ou adicione uma linha nova com o email. Clique em Salvar para aplicar.")
    editado = st.data_editor(
        df,
        column_config={
            "email": st.column_config.TextColumn("Email", required=True),
            "nome": st.column_config.TextColumn("Nome"),
            "role": st.column_config.SelectboxColumn("Papel", options=["admin", "usuario"], required=True),
            "ativo": st.column_config.CheckboxColumn("Ativo", default=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="editor_usuarios",
    )

    if st.button("💾 Salvar alterações"):
        emails_originais = {u["email"] for u in usuarios}
        emails_editados = {e.strip().lower() for e in editado["email"].dropna() if e.strip()}

        for email in emails_originais - emails_editados:
            excluir_usuario(email)

        for _, linha in editado.iterrows():
            email = str(linha.get("email") or "").strip()
            if not email:
                continue
            salvar_usuario(
                email=email,
                nome=linha.get("nome") or "",
                role=linha.get("role") or "usuario",
                ativo=bool(linha.get("ativo", True)),
            )

        st.success("Alterações salvas.")
        st.rerun()

# =============================
# ABA: IMPORTAR DO ENTRA ID
# =============================
with tab_entra:
    st.write("Busque um colaborador no diretório da Microsoft (Entra ID) pelo nome ou email e libere o acesso dele.")
    st.caption(
        "Precisa da permissão de aplicativo **User.Read.All** (Microsoft Graph) concedida "
        "com consentimento de admin no mesmo App Registration usado pelo login."
    )

    termo = st.text_input("Nome ou email", key="busca_entra")
    if termo:
        resultados = buscar_usuarios_entra(termo)

        if not resultados:
            st.info("Nenhum resultado (ou falha na busca — veja o aviso acima, se houver).")

        emails_ja_cadastrados = {u["email"].lower() for u in listar_usuarios()}

        for pessoa in resultados:
            ja_importado = pessoa["email"].lower() in emails_ja_cadastrados
            col_nome, col_papel, col_acao = st.columns([3, 2, 1])
            col_nome.write(f"**{pessoa['nome']}**  \n{pessoa['email']}")
            papel = col_papel.selectbox(
                "Papel",
                ["usuario", "admin"],
                key=f"papel_{pessoa['email']}",
                label_visibility="collapsed",
                disabled=ja_importado,
            )
            if ja_importado:
                col_acao.button("Já importado", key=f"btn_{pessoa['email']}", disabled=True)
            elif col_acao.button("Importar", key=f"btn_{pessoa['email']}"):
                salvar_usuario(email=pessoa["email"], nome=pessoa["nome"], role=papel, ativo=True)
                st.success(f"{pessoa['email']} importado como {papel}.")
                st.rerun()
