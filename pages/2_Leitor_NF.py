import streamlit as st
import zipfile
import os
import tempfile
import pandas as pd
from io import BytesIO

from utils.nf import extrair_texto_pdf, analisar_nf

st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)

st.title("📄 Leitor de Notas Fiscais com IA")

tab_zip, tab_pdfs = st.tabs(["📦 Enviar ZIP", "📂 Enviar PDFs"])


def processar_pdfs(caminhos: list[tuple[str, str]]) -> pd.DataFrame:
    """Recebe lista de (nome_arquivo, caminho) e retorna DataFrame com resultados."""
    resultados = []
    progress = st.progress(0)
    total = len(caminhos)

    for i, (nome, caminho) in enumerate(caminhos):
        st.write(f"Processando {i + 1}/{total}: {nome}")
        texto = extrair_texto_pdf(caminho)
        if texto:
            try:
                dados = analisar_nf(texto)
                dados["arquivo"] = nome
                resultados.append(dados)
            except Exception as e:
                st.warning(f"Erro em {nome}: {e}")
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
            zip_path = os.path.join(tmpdir, "arquivo.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.read())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)

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
