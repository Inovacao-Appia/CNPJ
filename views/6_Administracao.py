import pandas as pd
import streamlit as st

from utils.access import excluir_usuario, listar_usuarios, salvar_usuario
from utils.auth import require_login
from utils.graph import buscar_usuarios_entra
from utils.paginas import PAGINAS

require_login()

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
    st.caption(
        "Marque as caixas \"Vê ...\" pra decidir quais páginas aparecem no menu de cada usuário "
        "(matriz de acesso). \"Administração\" não entra aqui: é liberada só pelo Papel = admin."
    )

    busca = st.text_input("Buscar por email ou nome", key="busca_usuarios")
    usuarios = listar_usuarios(busca)

    colunas_paginas = [p["key"] for p in PAGINAS]
    linhas = []
    for u in usuarios:
        bloqueadas = set(u.get("paginas_bloqueadas") or [])
        linha = {"email": u["email"], "nome": u["nome"], "role": u["role"], "ativo": u["ativo"]}
        linha.update({p["key"]: p["key"] not in bloqueadas for p in PAGINAS})
        linhas.append(linha)

    df = pd.DataFrame(linhas, columns=["email", "nome", "role", "ativo"] + colunas_paginas)

    column_config = {
        "email": st.column_config.TextColumn("Email", required=True),
        "nome": st.column_config.TextColumn("Nome"),
        "role": st.column_config.SelectboxColumn("Papel", options=["admin", "usuario"], required=True),
        "ativo": st.column_config.CheckboxColumn("Ativo", default=True),
    }
    column_config.update(
        {p["key"]: st.column_config.CheckboxColumn(f"Vê {p['title']}", default=True) for p in PAGINAS}
    )

    st.caption("Edite direto na tabela ou adicione uma linha nova com o email. Clique em Salvar para aplicar.")
    editado = st.data_editor(
        df,
        column_config=column_config,
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
            paginas_bloqueadas = [chave for chave in colunas_paginas if not bool(linha.get(chave, True))]
            salvar_usuario(
                email=email,
                nome=linha.get("nome") or "",
                role=linha.get("role") or "usuario",
                ativo=bool(linha.get("ativo", True)),
                paginas_bloqueadas=paginas_bloqueadas,
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
