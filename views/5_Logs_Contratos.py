import streamlit as st
from utils.logger import buscar_logs_contratos, exibir_dashboard_logs
from utils.auth import require_login

require_login()

st.title("📊 Logs de Contratos")

exibir_dashboard_logs(buscar_logs_contratos(), "Total de contratos analisados")
