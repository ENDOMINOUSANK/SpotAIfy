
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI  = os.getenv("REDIRECT_URI", "http://127.0.0.1:8000/error")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Missing CLIENT_ID or CLIENT_SECRET in environment")

import pyodbc



# SQL Server credentials
SQL_SERVER = os.getenv("SQL_SERVER")           # Or 'localhost\\SQLEXPRESS'
SQL_DATABASE = os.getenv("SQL_DATABASE", "spotify")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

# Global SQL connection (initialize as None)
sql_conn = None

def get_sql_connection():
    """
    Create a singleton connection to SQL Server.
    """
    global sql_conn
    if sql_conn is None:
        try:
            sql_conn = pyodbc.connect(
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={SQL_SERVER};'
                f'DATABASE={SQL_DATABASE};'
                f'UID={SQL_USERNAME};'
                f'PWD={SQL_PASSWORD}'
            )
            print("✓ Connected to SQL Server")
        except Exception as e:
            print(f"✗ SQL Server connection failed: {e}")
            sql_conn = None
    return sql_conn
conn = get_sql_connection()

def signin(conn):
    """
    Sign in to Spotify and insert the user into SQL Server if not present.
    """
    # Authenticate Spotify
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-library-read playlist-modify-public user-top-read user-read-recently-played user-read-private user-read-email",
        cache_path=".spotify_cache"
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)
    sp.auth_manager.get_access_token(as_dict=False)

    user = sp.current_user()
    print(f"✓ Logged in as: {user['display_name']}")

    # Connect to SQL Server once
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM users WHERE email = ?)
                INSERT INTO users (user_name, country, email)
                VALUES (?, ?, ?)
            """, user['email'], user['display_name'], user.get('country', ''), user['email'])
            conn.commit()
            print("✓ User data handled successfully")
        except Exception as e:
            print(f"✗ Failed to insert user: {e}")
    else:
        print("✗ Skipping DB operations due to failed connection.")

    return user, sp

# def signin():
#     """
#     Sign in to Spotify using the Spotipy library.
#     This function will open a web browser for the user to log in.
#     """
#     auth_manager = SpotifyOAuth(
#     client_id=CLIENT_ID,
#     client_secret=CLIENT_SECRET,
#     redirect_uri=REDIRECT_URI,
#     scope="user-library-read playlist-modify-public user-top-read user-read-recently-played user-read-private user-read-email",
#     cache_path=".spotify_cache"  # Add this line
# )

#     # Create client with auth manager
#     sp = spotipy.Spotify(auth_manager=auth_manager)

#     # Force a token refresh
#     sp.auth_manager.get_access_token(as_dict=False)

#     # Check authentication status
#     user = sp.current_user()
#     print(f"✓ Authentication successful - logged in as: {user['display_name']}")

#     return user,sp



import json
# ...existing imports...

def get_top_tracks(sp, conn, limit=20, time_range='short_term'):
    """
    Fetch the user's top tracks, filter to ASCII-only titles,
    insert song metadata into the songs table, and record
    the top_tracks in user_song_preferences.
    """
    # 1) fetch top tracks
    resp = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    ascii_tracks = []
    for item in resp.get('items', []):
        track_id = item['id']
        name     = item['name']
        artist   = item['artists'][0]['name']
        # filter ASCII letters/spaces only
        if name.isascii() and name.replace(' ', '').isalpha():
            ascii_tracks.append({
                'id': track_id,
                'name': name,
                'artist': artist
            })

    # 2) insert each into songs table if not exists
    if conn:
        cur = conn.cursor()
        for t in ascii_tracks:
            cur.execute("""
                IF NOT EXISTS (SELECT 1 FROM songs WHERE song_id = ?)
                INSERT INTO songs (song_id, title, artist)
                VALUES (?, ?, ?)
            """, t['id'], t['id'], t['name'], t['artist'])
        conn.commit()

        # 3) record user preference
        user = sp.current_user()
        # fetch userid from users table
        cur.execute("SELECT userid FROM users WHERE email = ?", user['email'])
        row = cur.fetchone()
        if row:
            user_id = row[0]
            top_json = json.dumps(ascii_tracks, ensure_ascii=False)
            cur.execute("""
                INSERT INTO user_song_preferences (userid, user_name, top_tracks)
                VALUES (?, ?, ?)
            """, user_id, user['display_name'], top_json)
            conn.commit()

    return ascii_tracks
# def get_top_tracks(sp, limit=20, time_range='short_term'):
#     """
#     Fetch the user's top tracks and return only those whose titles
#     consist purely of Latin letters and spaces (no non-ASCII scripts).

#     Parameters:
#         sp: Authenticated spotipy.Spotify client
#         limit: Number of top tracks to fetch (1–50)
#         time_range: 'short_term', 'medium_term', or 'long_term'

#     Returns:
#         List of dicts: [{ 'name': track_name, 'artist': first_artist_name }, ...]
#     """
#     resp = sp.current_user_top_tracks(limit=limit, time_range=time_range)
#     ascii_tracks = []
#     for item in resp.get('items', []):
#         name = item['name']
#         artist = item['artists'][0]['name']
#         # Keep only pure ASCII and letters/spaces
#         if name.isascii() and name.replace(' ', '').isalpha():
#             ascii_tracks.append({'name': name, 'artist': artist})
#     return ascii_tracks




def get_liked_tracks(sp, limit=50):
    """
    Fetch the user's saved tracks and return only those whose titles
    consist purely of Latin letters and spaces (no non-ASCII scripts).

    Parameters:
        sp: Authenticated spotipy.Spotify client
        limit: Page size for each API call (1–50)

    Returns:
        List of dicts: [{ 'name': track_name, 'artists': 'Artist1, Artist2' }, ...]
    """
    liked = []
    offset = 0
    while True:
        resp = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = resp.get("items", [])
        if not items:
            break
        for item in items:
            track = item["track"]
            name = track["name"]
            artists = ", ".join(a["name"] for a in track["artists"])
            # filter for ASCII letters and spaces only
            if name.isascii() and name.replace(" ", "").isalpha():
                liked.append({"name": name, "artists": artists})
        offset += len(items)
    return liked

