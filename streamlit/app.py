import streamlit as st
import time
import os, sys

# 1) tell Python where to find your src folder
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from src.onboard import signin, get_sql_connection, get_top_tracks, get_liked_tracks
from src.ai_tools import make_playlist_from_prompt
conn = get_sql_connection()

st.set_page_config(page_title="VibeTune", page_icon="🎵")
st.title("Welcome to VibeTune")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def do_signin():
    user, sp = signin(conn)
    if user:
        st.session_state.authenticated = True
        st.session_state.sp = sp
    return user, sp

if not st.session_state.authenticated:
    if st.button("Sign in with Spotify"):
        user, sp = do_signin()
        with st.spinner("Signing in…"):
            time.sleep(10)
        st.rerun()

if st.session_state.authenticated:
    sp = st.session_state.sp  # retrieve saved client
    st.header("🎤 VibeTune Chat")
    tracks = []
    liked = []

    with st.spinner("Loading your top tracks…"):
        time.sleep(2)
        tracks = get_top_tracks(sp, conn)
        liked  = get_liked_tracks(sp, conn)
        if not tracks:
            st.error("No top tracks found. Please check your Spotify account.")
            st.stop()

    # --- Sidebar with your tracks ---
    st.sidebar.header("🎶 Your Music")
    st.sidebar.subheader("Top Tracks")
    for t in tracks:
        st.sidebar.write(f"{t['name']} — {t['artist']}")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Liked Tracks")
    for l in liked:
        st.sidebar.write(f"{l['name']} — {l['artists']}")

    # --- Main chat interface ---
    chat_container = st.container()
    user_input = st.text_input("You:", placeholder="Type your message here…")
    if user_input:
        with chat_container:
            st.markdown(f"**You:** {user_input}")
            with st.spinner("Creating playlist…"):
                # pass the user query into your AI tool
                playlist_url = make_playlist_from_prompt(user_input, sp)
            if playlist_url:
                st.markdown(
                    f"**VibeTune:** Your playlist is ready 🎉\n\n"
                    f"[Open it in Spotify]({playlist_url})"
                )
            else:
                st.markdown("**VibeTune:** ❌ Sorry, I couldn't create a playlist.")
# ...existing code...