import os
import tempfile
import zipfile

import pandas as pd
import streamlit as st

from utils.contratos import (
    COLUMNS,
    agrupar_arquivos_zip,
    analisar_contrato,
    extrair_texto_documentos,
    gerar_excel_formatado,
)
from utils.logger import registrar_contrato

st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)

st.title("📑 Leitor de Contratos com IA")

tab_individual, tab_lote = st.tabs(["📄 Contrato Individual", "📦 Lote (ZIP)"])

COLUNA_ARQUIVOS = "ARQUIVO(S) DE ORIGEM"


def processar_grupos(grupos: list[tuple[str, list[tuple[str, str]]]]) -> pd.DataFrame:
    """Recebe lista de (nome_do_contrato, [(rótulo, caminho), ...]) e retorna
    DataFrame com uma linha por contrato analisado."""
    resultados = []
    progress = st.progress(0)
    total = len(grupos)

    for i, (nome, documentos) in enumerate(grupos):
        nomes_arquivos = [os.path.basename(caminho) for _rotulo, caminho in documentos]
        st.write(f"Processando {i + 1}/{total}: {nome} ({', '.join(nomes_arquivos)})")
        try:
            texto = extrair_texto_documentos(documentos)
            dados = analisar_contrato(texto)
            linha = {rotulo: dados.get(chave) for chave, rotulo in COLUMNS}
            linha[COLUNA_ARQUIVOS] = ", ".join(nomes_arquivos)
            resultados.append(linha)
            registrar_contrato(nome, nomes_arquivos, dados, status="sucesso")
        except Exception as e:
            st.warning(f"Erro em {nome}: {e}")
            registrar_contrato(nome, nomes_arquivos, {}, status="erro", erro=str(e))
        progress.progress((i + 1) / total)

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
        "Selecione todos os PDFs referentes ao MESMO contrato "
        "(contrato principal, Ordem de Serviço, aditivos, DocuSign etc.). "
        "Eles serão analisados juntos como um único contrato."
    )
    uploaded_pdfs = st.file_uploader(
        "Selecione os PDFs do contrato",
        type=["pdf"],
        accept_multiple_files=True,
        key="contrato_individual",
    )

    if uploaded_pdfs and st.button("🚀 Analisar Contrato"):
        with tempfile.TemporaryDirectory() as tmpdir:
            documentos = []
            for pdf in uploaded_pdfs:
                caminho = os.path.join(tmpdir, pdf.name)
                with open(caminho, "wb") as f:
                    f.write(pdf.read())
                documentos.append((os.path.splitext(pdf.name)[0], caminho))

            nome_grupo = os.path.splitext(uploaded_pdfs[0].name)[0]
            df = processar_grupos([(nome_grupo, documentos)])
            exibir_resultado(df)

# =============================
# ABA: LOTE (ZIP)
# =============================
with tab_lote:
    st.info(
        "Suba um arquivo `.zip` com vários contratos. Cada subpasta é tratada como "
        "um único contrato (todos os PDFs dentro dela são analisados juntos); "
        "PDFs soltos na raiz do ZIP são tratados cada um como um contrato próprio."
    )
    uploaded_zip = st.file_uploader("Selecione o ZIP", type=["zip"], key="lote_zip")

    if uploaded_zip and st.button("🚀 Processar Lote"):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "arquivo.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.read())

            extract_dir = os.path.join(tmpdir, "extraido")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            grupos = agrupar_arquivos_zip(extract_dir)

            if not grupos:
                st.error("Nenhum PDF encontrado dentro do ZIP.")
            else:
                st.write(f"{len(grupos)} contrato(s) identificado(s) no ZIP.")
                df = processar_grupos(grupos)
                exibir_resultado(df)
