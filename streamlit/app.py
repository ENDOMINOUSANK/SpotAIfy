import streamlit as st
import time
import os, sys

# 1) tell Python where to find your src folder
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# now this will work
from src.onboard import signin ,get_sql_connection
conn = get_sql_connection()

st.set_page_config(page_title="VibeTune", page_icon="🎵")
# st.image("vibetune.png", width=120)
st.title("Welcome to VibeTune")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def do_signin():
    user, sp_client = signin(conn)
    if user:
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    if st.button("Sign in with Spotify"):
        do_signin()
        with st.spinner("Signing in…"):
            time.sleep(10)
        st.rerun()

if st.session_state.authenticated:
    st.header("🎤 VibeTune Chat")
    chat_container = st.container()
    user_input = st.text_input("You:", placeholder="Type your message here…")
    if user_input:
        with chat_container:
            st.markdown(f"**You:** {user_input}")
            st.markdown(f"**VibeTune:** 🤖 _(response goes here)_")