import streamlit as st
from utils.logger import buscar_logs_contratos, exibir_dashboard_logs
from utils.auth import logout_button, require_login
from utils.config import FAVICON_PATH

st.set_page_config(page_title="Appia Tools", layout="wide", page_icon=FAVICON_PATH)

require_login()

st.logo("Logos/Via Appia/PNG/Via Appia Negativo.png", size="large")
logout_button()

st.title("📊 Logs de Contratos")

exibir_dashboard_logs(buscar_logs_contratos(), "Total de contratos analisados")
