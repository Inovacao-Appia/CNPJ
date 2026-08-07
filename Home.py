import streamlit as st

from utils.auth import logout_button, require_login

st.set_page_config(page_title="Appia Tools", layout="wide")

require_login()

st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)
logout_button()

st.title("Appia Tools")
st.write("Selecione uma ferramenta no menu lateral.")
