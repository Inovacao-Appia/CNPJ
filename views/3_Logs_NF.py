import streamlit as st
from utils.logger import buscar_logs, exibir_dashboard_logs
from utils.auth import require_login

require_login()

st.title("📊 Logs de Notas Fiscais")

exibir_dashboard_logs(buscar_logs(), "Total de NFs analisadas")
