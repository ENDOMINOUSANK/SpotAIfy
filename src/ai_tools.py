from llm_axe import OllamaChat, Agent, OnlineAgent
import re, json
import json
import time
from urllib.parse import urlencode
import spotipy
import random
from IPython.display import display, HTML


def get_recommendations(prompt):
    prompt2 = f"""
You are a music recommendation agent.

Your task is to recommend songs based on the user's emotional state or request. You must follow these rules strictly:

1.  Recommend a MAXIMUM of 20 songs.
2.  Respond in **valid JSON format only**, with NO extra text, no commentary, and no explanations.
3.  Each song must follow this format:
   {{
       "name": "Name of the song",
       "artist": "Main artist of the song"
   }}
4. If the user request is unrelated to music or songs, respond with this exact text (without JSON):  
   `"I CAN'T HELP YOU WITH THAT"`

MAIN TASK:  
Determine the user's mood or intent based on this input, and return an appropriate list of songs in JSON:

USER INPUT: {prompt} https://www.google.com/
"""
    llm = OllamaChat(model="gemma3:4b-it-qat")
    searcher = OnlineAgent(llm)
    resp_raw = searcher.search(prompt2)
    print("Raw response:", resp_raw)
    # coerce into a string
    resp = resp_raw if isinstance(resp_raw, str) else getattr(resp_raw, "text", str(resp_raw))

    # now regex on resp
    match = re.search(r"json\s*(\[\s*{.*?}\s*])\s*", resp, re.DOTALL)
    if match:
        js = match.group(1)
        try:
            data = json.loads(js)
            with open("recommendations.json", "w") as f:
                json.dump(data, f, indent=2)
            print("Extracted JSON:", data)
        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
    else:
        print("❌ No JSON found in response:\n", resp)

    return resp

# test it

def fetch_recommendation_ids(recs, sp):
    """
    For each recommendation dict {'name':…, 'artist':…},
    search Spotify and return the first track ID (or None).
    """
    ids = []
    for rec in recs:
        query = f"{rec['name']} {rec['artist']}"
        res = sp.search(q=query, limit=1, type="track", market="from_token")
        items = res.get("tracks", {}).get("items", [])
        if items:
            ids.append(items[0]["id"])
        else:
            ids.append(None)
    return ids




def create_playlist_from_tracks(sp,track_ids, playlist_name=None, playlist_description=None):
    """
    Create a new Spotify playlist from a list of track IDs
    
    Parameters:
        track_ids (list): List of Spotify track IDs to add to the playlist
        playlist_name (str): Name for the new playlist (default: "Recommended Tracks YYYY-MM-DD")
        playlist_description (str): Description for the new playlist
        
    Returns:
        str: URL to the created playlist
    """
    if not track_ids:
        print("❌ No tracks provided to create playlist")
        return None
    rand = random.randint(1, 1000)
        
    # Use default name if none provided
    if not playlist_name:
        playlist_name = f"SpotAIfy-{rand}-{time.strftime('%Y-%m-%d')}"
        
    # Use default description if none provided
    if not playlist_description:
        playlist_description = f"Playlist created on {time.strftime('%Y-%m-%d')} with recommended tracks"
    
    try:
        # Get current user ID
        user_id = sp.current_user()['id']
        
        # Create an empty playlist
        print(f"Creating new playlist: '{playlist_name}'")
        created_playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=True,
            description=playlist_description
        )
        
        # Get the playlist ID
        playlist_id = created_playlist['id']
        
        # Add tracks in batches (Spotify has a limit of 100 per request)
        batch_size = 100
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i+batch_size]
            sp.playlist_add_items(playlist_id=playlist_id, items=batch)
            print(f"Added tracks {i+1}-{i+len(batch)} to playlist")
        
        # Get the playlist URL
        playlist_url = created_playlist['external_urls']['spotify']
        
        print(f"✅ Successfully created playlist with {len(track_ids)} tracks!")
        print(f"Playlist URL: {playlist_url}")
        
        # Display clickable link (works in Jupyter)
        display(HTML(f'<a href="{playlist_url}" target="_blank">Open playlist in Spotify</a>'))
        
        return playlist_url
        
    except Exception as e:
        print(f"❌ Error creating playlist: {str(e)}")
        return None
    
def make_playlist_from_prompt(prompt, sp):
    """
    Create a Spotify playlist based on a user prompt.
    
    Parameters:
        prompt (str): User's input for music recommendation
        sp (spotipy.Spotify): Authenticated Spotipy client
        
    Returns:
        str: URL to the created playlist
    """
    # Get recommendations based on the prompt
    recs = get_recommendations(prompt)
    with open("recommendations.json", "r") as f:
        recs = json.load(f)
    
    # Check if recommendations were successfully retrieved
    if not recs:
        print("❌ No recommendations found.")
        return None
    
    # Extract track IDs from recommendations
    track_ids = fetch_recommendation_ids(recs, sp)
    
    # Create a new playlist with the recommended tracks
    playlist_url = create_playlist_from_tracks(sp, track_ids)
    
    return playlist_url

# with open("recommendations.json", "r") as f:
#     recs = json.load(f)

