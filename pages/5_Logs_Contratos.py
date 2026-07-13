import streamlit as st
import pandas as pd
from utils.logger import buscar_logs_contratos

st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)

st.title("📊 Logs de Contratos")

logs = buscar_logs_contratos()

if not logs:
    st.info("Nenhum log registrado ainda.")
else:
    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M")

    total = len(df)
    sucesso = (df["status"] == "sucesso").sum()
    erro = (df["status"] == "erro").sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de contratos analisados", total)
    col2.metric("Com sucesso", sucesso)
    col3.metric("Com erro", erro)

    st.divider()
    st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
