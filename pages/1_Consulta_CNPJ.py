import streamlit as st
import pandas as pd
import time
from io import BytesIO
from datetime import datetime

from utils.cnpj import limpa_cnpj, consultar_cnpj, processar_dados_cnpj

st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)

st.title("🔍 Consulta CNPJ")

tab1, tab2 = st.tabs(["Consulta Única", "Em Massa"])

# =============================
# CONSULTA ÚNICA
# =============================
with tab1:
    cnpj_input = st.text_input("Digite o CNPJ")

    if st.button("Consultar"):
        cnpj = limpa_cnpj(cnpj_input)

        if len(cnpj) == 14:
            with st.spinner("Buscando dados na Receita..."):
                res = consultar_cnpj(cnpj)
                dados = processar_dados_cnpj(res)

            if dados:
                st.success(f"Dados de {dados['NOME']}")

                c1, c2, c3 = st.columns(3)
                c1.metric("Situação", dados["SITUACAO CADASTRAL"])
                c2.metric("Capital Social", f"R$ {dados['CAPITAL SOCIAL']:,.2f}")
                c3.metric("Data de Abertura", dados["DATA ABERTURA"])

                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📧 Email:** {dados['EMAIL'] or 'Não informado'}")
                    st.markdown(f"**📍 Endereço:** {dados['ENDEREÇO']}")
                with col2:
                    st.markdown(f"**📅 Data da Situação:** {dados['DATA SITUACAO CADASTRADA']}")
                    st.markdown(f"**🆔 CNPJ:** {dados['CNPJ']}")

                st.divider()

                st.subheader("Atividades Econômicas")
                st.info(f"**Primária:** {dados['CNAE PRIMARIO']}")
                with st.expander("Ver Atividades Secundárias"):
                    if dados["CNAE SECUNDARIO"]:
                        st.text(dados["CNAE SECUNDARIO"])
                    else:
                        st.write("Sem atividades secundárias registradas.")

                st.divider()

                st.subheader("Quadro de Sócios e Administradores")
                socios = [dados[f"SOCIO {i}"] for i in range(1, 11) if dados[f"SOCIO {i}"]]
                if socios:
                    for i, socio in enumerate(socios, 1):
                        st.write(f"{i}. {socio}")
                else:
                    st.write("Informação de sócios não disponível.")

            else:
                st.error(res.get("message", "Erro desconhecido ou CNPJ não encontrado.") if res else "Erro ao consultar")
        else:
            st.warning("CNPJ inválido. Deve conter 14 dígitos.")

# =============================
# PROCESSAMENTO EM MASSA
# =============================
with tab2:
    st.info("⚠️ Delay de 20s por CNPJ (limite da API gratuita)")

    col_modelo_1, col_modelo_2 = st.columns([3, 1])
    with col_modelo_1:
        st.write("1. Baixe o modelo se ainda não tiver a lista formatada:")
    with col_modelo_2:
        df_modelo = pd.DataFrame({"CNPJ": ["00.000.000/0000-00"]})
        buffer_modelo = BytesIO()
        with pd.ExcelWriter(buffer_modelo, engine="openpyxl") as writer:
            df_modelo.to_excel(writer, index=False)
        st.download_button(
            label="📄 Baixar Modelo",
            data=buffer_modelo.getvalue(),
            file_name="modelo_cnpjs.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.divider()
    st.write("2. Suba sua planilha preenchida:")
    file = st.file_uploader("Arraste o arquivo aqui", type=["xlsx"], label_visibility="collapsed")

    if file:
        df = pd.read_excel(file)
        st.write("Visualização da entrada:", df.head())

        if st.button("🚀 Iniciar Processamento"):
            col_cnpj = next((c for c in df.columns if "cnpj" in c.lower()), None)

            if not col_cnpj:
                st.error("Coluna CNPJ não encontrada na planilha.")
            else:
                lista = df[col_cnpj].dropna().tolist()
                total = len(lista)
                resultados = []
                progress = st.progress(0)

                for i, c in enumerate(lista):
                    cnpj = limpa_cnpj(c)
                    st.write(f"Processando {i + 1}/{total}: {cnpj}")

                    res_api = consultar_cnpj(cnpj)
                    dados_tratados = processar_dados_cnpj(res_api)

                    if dados_tratados:
                        resultados.append(dados_tratados)

                    progress.progress((i + 1) / total)

                    if i < total - 1:
                        time.sleep(21)

                df_final = pd.DataFrame(resultados)
                st.dataframe(df_final)

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_final.to_excel(writer, index=False)

                st.success("✅ Processamento concluído!")
                st.download_button(
                    "📥 Baixar Planilha Completa",
                    output.getvalue(),
                    file_name=f"Resultado_CNPJ_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx",
                )
