
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
# ...existing code...

# def get_top_tracks(sp, conn, limit=20, time_range='short_term'):
#     # 1) fetch top tracks
#     resp = sp.current_user_top_tracks(limit=limit, time_range=time_range)
#     ascii_tracks = []
#     for item in resp.get('items', []):
#         track_id = item['id']
#         name     = item['name']
#         artist   = item['artists'][0]['name']
#         if name.isascii() and name.replace(' ', '').isalpha():
#             ascii_tracks.append({'id': track_id, 'name': name, 'artist': artist})

#     if conn:
#         cur = conn.cursor()
#         # insert into songs table
#         for t in ascii_tracks:
#             cur.execute("""
#                 IF NOT EXISTS (SELECT 1 FROM songs WHERE song_id = ?)
#                 INSERT INTO songs (song_id, title, artist)
#                 VALUES (?, ?, ?)
#             """, t['id'], t['id'], t['name'], t['artist'])
#         conn.commit()

#         # record or update user preference
#         user = sp.current_user()
#         cur.execute("SELECT userid FROM users WHERE email = ?", user['email'])
#         row = cur.fetchone()
#         if row:
#             user_id  = row[0]
#             top_json = json.dumps(ascii_tracks, ensure_ascii=False)
#             # check existing preference
#             cur.execute("SELECT 1 FROM user_song_preferences WHERE userid = ?", user_id)
#             if cur.fetchone():
#                 cur.execute("""
#                     UPDATE user_song_preferences
#                        SET top_tracks = ?
#                      WHERE userid = ?
#                 """, top_json, user_id)
#             else:
#                 cur.execute("""
#                     INSERT INTO user_song_preferences (userid, user_name, top_tracks)
#                     VALUES (?, ?, ?)
#                 """, user_id, user['display_name'], top_json)
#             conn.commit()

#     return ascii_tracks


# def get_liked_tracks(sp, conn, limit=50):
#     """
#     Fetch the user's saved tracks, filter to ASCII-only titles,
#     insert song metadata into the songs table, and record
#     the liked_songs in user_song_preferences.
#     """
#     liked = []
#     offset = 0

#     # 1) fetch all saved tracks
#     while True:
#         resp = sp.current_user_saved_tracks(limit=limit, offset=offset)
#         items = resp.get("items", [])
#         if not items:
#             break
#         for item in items:
#             track = item["track"]
#             name = track["name"]
#             artists = ", ".join(a["name"] for a in track["artists"])
#             # filter ASCII letters & spaces only
#             if name.isascii() and name.replace(" ", "").isalpha():
#                 liked.append({
#                     "id":    track["id"],
#                     "name":  name,
#                     "artists": artists
#                 })
#         offset += len(items)

#     # 2) persist into songs & user preferences
#     if conn:
#         cur = conn.cursor()

#         # insert into songs table if missing
#         for t in liked:
#             cur.execute("""
#                 IF NOT EXISTS (SELECT 1 FROM songs WHERE song_id = ?)
#                 INSERT INTO songs (song_id, title, artist)
#                 VALUES (?, ?, ?)
#             """, t["id"], t["id"], t["name"], t["artists"])
#         conn.commit()

#         # record or update liked_songs in preferences
#         user = sp.current_user()
#         cur.execute("SELECT userid FROM users WHERE email = ?", user["email"])
#         row = cur.fetchone()
#         if row:
#             user_id    = row[0]
#             likes_json = json.dumps(liked, ensure_ascii=False)

#             # upsert into user_song_preferences
#             cur.execute("""
#                 SELECT 1 FROM user_song_preferences WHERE userid = ?
#             """, user_id)
#             if cur.fetchone():
#                 cur.execute("""
#                     UPDATE user_song_preferences
#                        SET liked_songs = ?
#                      WHERE userid = ?
#                 """, likes_json, user_id)
#             else:
#                 cur.execute("""
#                     INSERT INTO user_song_preferences
#                         (userid, user_name, liked_songs)
#                     VALUES (?, ?, ?)
#                 """, user_id, user["display_name"], likes_json)
#             conn.commit()

#     return liked


def get_top_tracks(sp, conn, limit=20, time_range='short_term'):
    """
    Fetch the user's top tracks, filter to ASCII-only titles,
    insert song metadata into the songs table, and record
    the top_tracks in user_song_preferences.
    """
    resp = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    ascii_tracks = []
    for item in resp.get('items', []):
        name     = item['name']
        if not (name.isascii() and name.replace(' ', '').isalpha()):
            continue
        ascii_tracks.append({
            'id':         item['id'],
            'name':       name,
            'artist':     item['artists'][0]['name'],
            'popularity': item['popularity'],
            'duration_ms':item['duration_ms'],
            'explicit':   int(item['explicit']),
            'artists':    ", ".join(a['name'] for a in item['artists']),
            'album':      item['album']['name']
        })

    if conn:
        cur = conn.cursor()
        # insert into songs table
        for t in ascii_tracks:
            cur.execute("""
                IF NOT EXISTS (SELECT 1 FROM songs WHERE song_id = ?)
                INSERT INTO songs
                  (song_id, title, artist, popularity, duration_ms, explicit, artists, album)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            t['id'], t['id'], t['name'], t['artist'],
            t['popularity'], t['duration_ms'], t['explicit'],
            t['artists'], t['album'])
        conn.commit()

        # record/update user preference
        user = sp.current_user()
        cur.execute("SELECT userid FROM users WHERE email = ?", user['email'])
        row = cur.fetchone()
        if row:
            user_id  = row[0]
            top_json = json.dumps(ascii_tracks, ensure_ascii=False)
            cur.execute("SELECT 1 FROM user_song_preferences WHERE userid = ?", user_id)
            if cur.fetchone():
                cur.execute("""
                    UPDATE user_song_preferences
                       SET top_tracks = ?
                     WHERE userid = ?
                """, top_json, user_id)
            else:
                cur.execute("""
                    INSERT INTO user_song_preferences (userid, user_name, top_tracks)
                    VALUES (?, ?, ?)
                """, user_id, user['display_name'], top_json)
            conn.commit()

    return ascii_tracks


def get_liked_tracks(sp, conn, limit=50):
    """
    Fetch the user's saved tracks, filter to ASCII-only titles,
    insert song metadata into the songs table (including added_at),
    and record the liked_songs in user_song_preferences.
    """
    liked = []
    offset = 0
    while True:
        resp = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = resp.get('items', [])
        if not items:
            break
        for item in items:
            added_at = item.get('added_at')
            track    = item['track']
            name     = track['name']
            if not (name.isascii() and name.replace(' ', '').isalpha()):
                continue
            liked.append({
                'id':          track['id'],
                'name':        name,
                'artist':      track['artists'][0]['name'],
                'added_at':    added_at,
                'popularity':  track['popularity'],
                'duration_ms': track['duration_ms'],
                'explicit':    int(track['explicit']),
                'artists':     ", ".join(a['name'] for a in track['artists']),
                'album':       track['album']['name']
            })
        offset += len(items)

    if conn:
        cur = conn.cursor()
        for t in liked:
            cur.execute("""
                IF NOT EXISTS (SELECT 1 FROM songs WHERE song_id = ?)
                INSERT INTO songs
                  (song_id, title, artist, added_at, popularity, duration_ms,
                   explicit, artists, album)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            t['id'], t['id'], t['name'], t['artist'],
            t['added_at'], t['popularity'], t['duration_ms'],
            t['explicit'], t['artists'], t['album'])
        conn.commit()

        user = sp.current_user()
        cur.execute("SELECT userid FROM users WHERE email = ?", user['email'])
        row = cur.fetchone()
        if row:
            user_id    = row[0]
            likes_json = json.dumps(liked, ensure_ascii=False)
            cur.execute("SELECT 1 FROM user_song_preferences WHERE userid = ?", user_id)
            if cur.fetchone():
                cur.execute("""
                    UPDATE user_song_preferences
                       SET liked_songs = ?
                     WHERE userid = ?
                """, likes_json, user_id)
            else:
                cur.execute("""
                    INSERT INTO user_song_preferences
                      (userid, user_name, liked_songs)
                    VALUES (?, ?, ?)
                """, user_id, user['display_name'], likes_json)
            conn.commit()

    return liked

# def get_liked_tracks(sp, limit=50):
#     """
#     Fetch the user's saved tracks and return only those whose titles
#     consist purely of Latin letters and spaces (no non-ASCII scripts).

#     Parameters:
#         sp: Authenticated spotipy.Spotify client
#         limit: Page size for each API call (1–50)

#     Returns:
#         List of dicts: [{ 'name': track_name, 'artists': 'Artist1, Artist2' }, ...]
#     """
#     liked = []
#     offset = 0
#     while True:
#         resp = sp.current_user_saved_tracks(limit=limit, offset=offset)
#         items = resp.get("items", [])
#         if not items:
#             break
#         for item in items:
#             track = item["track"]
#             name = track["name"]
#             artists = ", ".join(a["name"] for a in track["artists"])
#             # filter for ASCII letters and spaces only
#             if name.isascii() and name.replace(" ", "").isalpha():
#                 liked.append({"name": name, "artists": artists})
#         offset += len(items)
#     return liked

