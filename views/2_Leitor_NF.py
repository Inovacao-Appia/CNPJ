import streamlit as st
import os
import tempfile
import pandas as pd
from io import BytesIO

from utils.nf import extrair_texto_pdf, analisar_nf
from utils.logger import registrar_nf
from utils.zipsafe import extrair_upload_zip_seguro
from utils.auth import require_login

require_login()

st.title("📄 Leitor de Notas Fiscais com IA")

tab_zip, tab_pdfs = st.tabs(["📦 Enviar ZIP", "📂 Enviar PDFs"])


def processar_pdfs(caminhos: list[tuple[str, str]]) -> pd.DataFrame:
    """Recebe lista de (nome_arquivo, caminho) e retorna DataFrame com resultados."""
    resultados = []
    progress = st.progress(0)
    total = len(caminhos)

    for i, (nome, caminho) in enumerate(caminhos):
        st.write(f"Processando {i + 1}/{total}: {nome}")
        texto, paginas_sem_texto, imagens_paginas = extrair_texto_pdf(caminho)
        if paginas_sem_texto:
            st.warning(f"{nome}: {len(paginas_sem_texto)} página(s) sem texto extraível, lendo como imagem.")
        if texto or imagens_paginas:
            try:
                dados = analisar_nf(texto, imagens_paginas)
                dados["arquivo"] = nome
                resultados.append(dados)
                registrar_nf(nome, dados, status="sucesso")
            except Exception as e:
                st.warning(f"Erro em {nome}: {e}")
                registrar_nf(nome, {}, status="erro", erro=str(e))
        progress.progress((i + 1) / total)

    return pd.DataFrame(resultados)


def exibir_resultado(df: pd.DataFrame):
    st.success(f"✅ {len(df)} nota(s) processada(s)!")
    st.dataframe(df)

    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button(
        "📥 Baixar Excel",
        buffer.getvalue(),
        file_name="notas_fiscais.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# =============================
# ABA: ZIP
# =============================
with tab_zip:
    st.info("Suba um arquivo `.zip` contendo os PDFs das notas fiscais.")
    uploaded_zip = st.file_uploader("Selecione o ZIP", type=["zip"], key="zip")

    if uploaded_zip and st.button("🚀 Processar ZIP"):
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                extrair_upload_zip_seguro(uploaded_zip, tmpdir)
            except ValueError as e:
                st.error(f"ZIP inválido: {e}")
                st.stop()

            caminhos = []
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        caminhos.append((file, os.path.join(root, file)))

            if not caminhos:
                st.error("Nenhum PDF encontrado dentro do ZIP.")
            else:
                df = processar_pdfs(caminhos)
                exibir_resultado(df)

# =============================
# ABA: PDFs DIRETOS
# =============================
with tab_pdfs:
    st.info("Selecione um ou mais arquivos `.pdf` diretamente.")
    uploaded_pdfs = st.file_uploader(
        "Selecione os PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdfs",
    )

    if uploaded_pdfs and st.button("🚀 Processar PDFs"):
        with tempfile.TemporaryDirectory() as tmpdir:
            caminhos = []
            for pdf in uploaded_pdfs:
                caminho = os.path.join(tmpdir, pdf.name)
                with open(caminho, "wb") as f:
                    f.write(pdf.read())
                caminhos.append((pdf.name, caminho))

            df = processar_pdfs(caminhos)
            exibir_resultado(df)
