import os
import tempfile
import time

import pandas as pd
import streamlit as st

from utils.contratos import (
    CATEGORIA_SERVICO,
    CATEGORIAS,
    COLUMNS,
    analisar_documento,
    gerar_excel_formatado,
    listar_pdfs_zip,
)
from utils.logger import registrar_contrato
from utils.auth import logout_button, require_login
from utils.zipsafe import extrair_zip_seguro

require_login()

st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)
logout_button()

st.title("📑 Leitor de Contratos com IA")

categoria = st.radio(
    "Categoria dos documentos deste lote",
    options=list(CATEGORIAS.keys()),
    format_func=lambda chave: CATEGORIAS[chave],
    index=list(CATEGORIAS.keys()).index(CATEGORIA_SERVICO),
    horizontal=True,
    help=(
        "Define qual prompt de vigências (2.1 ou 2.2) será usado. Todos os "
        "documentos enviados de uma vez devem ser da mesma categoria."
    ),
)

tab_individual, tab_lote = st.tabs(["📄 Contrato Individual", "📦 Lote (ZIP)"])

COLUNA_ARQUIVOS = "ARQUIVO(S) DE ORIGEM"

# Pausa entre o processamento de cada PDF, para não sobrecarregar a API/memória.
_DELAY_ENTRE_DOCUMENTOS_SEGUNDOS = 3


def processar_documentos(documentos: list[tuple[str, str]], categoria: str) -> pd.DataFrame:
    """Recebe lista de (rótulo, caminho) — um PDF por contrato/aditivo — e processa
    CADA arquivo isoladamente (lê o PDF, roda os 3 prompts só sobre ele, grava a
    linha), um por vez, com uma pausa entre cada um. categoria define qual prompt
    de vigências (2.1 ou 2.2) é usado para todo o lote."""
    resultados = []
    progress = st.progress(0)
    total = len(documentos)

    for i, (rotulo, caminho) in enumerate(documentos):
        nome_arquivo = os.path.basename(caminho)
        with st.status(f"[{i + 1}/{total}] {nome_arquivo}", expanded=True) as status:
            try:
                dados = analisar_documento(rotulo, caminho, categoria, on_progress=status.write)
                linha = {rotulo_coluna: dados.get(chave) for chave, rotulo_coluna in COLUMNS}
                linha[COLUNA_ARQUIVOS] = nome_arquivo
                resultados.append(linha)
                registrar_contrato(rotulo, [nome_arquivo], dados, status="sucesso")
                status.update(label=f"[{i + 1}/{total}] {nome_arquivo} — concluído", state="complete")
            except Exception as e:
                registrar_contrato(rotulo, [nome_arquivo], {}, status="erro", erro=str(e))
                status.update(label=f"[{i + 1}/{total}] {nome_arquivo} — erro: {e}", state="error")
        progress.progress((i + 1) / total)

        if i < total - 1:
            time.sleep(_DELAY_ENTRE_DOCUMENTOS_SEGUNDOS)

    return pd.DataFrame(resultados)


def exibir_resultado(df: pd.DataFrame):
    if df.empty:
        st.error("Nenhum contrato processado com sucesso.")
        return

    st.success(f"✅ {len(df)} contrato(s) processado(s)!")
    st.dataframe(df)

    excel_bytes = gerar_excel_formatado(df)
    st.download_button(
        "📥 Baixar Excel",
        excel_bytes,
        file_name="analise_contratos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# =============================
# ABA: CONTRATO INDIVIDUAL
# =============================
with tab_individual:
    st.info(
        "Selecione um ou mais PDFs. Cada PDF é tratado como um contrato "
        "independente: é lido e analisado sozinho, um por vez, gerando sua "
        "própria linha na planilha."
    )
    uploaded_pdfs = st.file_uploader(
        "Selecione os PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="contrato_individual",
    )

    if uploaded_pdfs and st.button("🚀 Analisar Contrato(s)"):
        with tempfile.TemporaryDirectory() as tmpdir:
            documentos = []
            for pdf in uploaded_pdfs:
                caminho = os.path.join(tmpdir, pdf.name)
                with open(caminho, "wb") as f:
                    f.write(pdf.read())
                documentos.append((os.path.splitext(pdf.name)[0], caminho))

            df = processar_documentos(documentos, categoria)
            exibir_resultado(df)

# =============================
# ABA: LOTE (ZIP)
# =============================
with tab_lote:
    st.info(
        "Suba um arquivo `.zip` com vários PDFs, em qualquer estrutura de pastas. "
        "Cada PDF encontrado é tratado como um contrato independente e "
        "processado um por vez."
    )
    uploaded_zip = st.file_uploader("Selecione o ZIP", type=["zip"], key="lote_zip")

    if uploaded_zip and st.button("🚀 Processar Lote"):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "arquivo.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.read())

            extract_dir = os.path.join(tmpdir, "extraido")
            os.makedirs(extract_dir, exist_ok=True)
            try:
                extrair_zip_seguro(zip_path, extract_dir)
            except ValueError as e:
                st.error(f"ZIP inválido: {e}")
                st.stop()

            documentos = listar_pdfs_zip(extract_dir)

            if not documentos:
                st.error("Nenhum PDF encontrado dentro do ZIP.")
            else:
                st.write(f"{len(documentos)} PDF(s) identificado(s) no ZIP.")
                df = processar_documentos(documentos, categoria)
                exibir_resultado(df)
