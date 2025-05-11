import requests
from bs4 import BeautifulSoup
import re
import time
import random
import urllib.parse
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import urllib.parse

def get_lyrics(artist, song_title, max_attempts=3):
    """
    Find lyrics for a song using direct searches on lyrics sites.
    
    Args:
        artist: Artist name
        song_title: Song title
        max_attempts: Maximum number of sites to try
        
    Returns:
        String with lyrics or error message
    """
    # Try direct searches on multiple lyrics sites
    sites = [
        try_genius_lyrics,
        try_azlyrics,
        try_lyrics_com,
        try_musixmatch
    ]
    
    # Clean up song info
    artist = re.sub(r'[^\w\s]', '', artist.lower())
    song_title = re.sub(r'[^\w\s]', '', song_title.lower())
    
    print(f"Searching for lyrics: {artist} - {song_title}")
    
    # Try each site until we get lyrics
    attempts = 0
    for site_func in sites:
        if attempts >= max_attempts:
            break
            
        try:
            lyrics = site_func(artist, song_title)
            if lyrics and len(lyrics) > 100:  # Assume successful if we got substantial text
                return lyrics
        except Exception as e:
            print(f"Error with {site_func.__name__}: {str(e)}")
        
        attempts += 1
        # Add delay between requests to different sites
        time.sleep(1 + random.random())
    
    # If all direct attempts failed, try Google
    try:
        return google_lyrics_search(artist, song_title)
    except Exception as e:
        return f"Could not find lyrics: {str(e)}"

def get_random_headers():
    """Generate randomized headers to avoid blocking"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
    }

def try_genius_lyrics(artist, song_title):
    """Try to get lyrics directly from Genius"""
    # Format the URL - Genius uses dashes and lowercase
    url_title = song_title.replace(' ', '-').lower()
    url_artist = artist.replace(' ', '-').lower()
    url = f"https://genius.com/{url_artist}-{url_title}-lyrics"
    
    response = requests.get(url, headers=get_random_headers(), timeout=10)
    if response.status_code != 200:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try new format first
    lyrics_divs = soup.find_all('div', attrs={'data-lyrics-container': 'true'})
    if lyrics_divs:
        lyrics = "\n".join([div.get_text(separator="\n") for div in lyrics_divs])
        return clean_lyrics(lyrics)
    
    # Try older format
    lyrics_container = soup.find('div', class_=re.compile(r'Lyrics__Container'))
    if lyrics_container:
        return clean_lyrics(lyrics_container.get_text(separator="\n"))
        
    return None

def try_azlyrics(artist, song_title):
    """Try to get lyrics directly from AZLyrics"""
    # Format the URL - AZLyrics uses lowercase with no spaces
    url_artist = artist.replace(' ', '').lower()
    url_title = song_title.replace(' ', '').lower()
    url = f"https://www.azlyrics.com/lyrics/{url_artist}/{url_title}.html"
    
    response = requests.get(url, headers=get_random_headers(), timeout=10)
    if response.status_code != 200:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the div that has no class/id but contains the lyrics
    main_div = soup.find('div', class_='col-xs-12 col-lg-8 text-center')
    if not main_div:
        return None
        
    for div in main_div.find_all('div'):
        if not div.get('class') and not div.get('id'):
            text = div.get_text()
            if len(text) > 100:  # Verify it's likely lyrics
                return clean_lyrics(text)
    
    return None

def try_lyrics_com(artist, song_title):
    """Try to get lyrics directly from Lyrics.com"""
    # Encode for URL
    search_url = f"https://www.lyrics.com/search/both/{urllib.parse.quote(artist + ' ' + song_title)}"
    
    response = requests.get(search_url, headers=get_random_headers(), timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the first search result
    results = soup.find('div', class_='sec-lyric')
    if not results:
        return None
    
    result_link = results.find('a', {'href': re.compile(r'/lyric/')})
    if not result_link:
        return None
        
    lyrics_url = "https://www.lyrics.com" + result_link['href']
    
    # Get the lyrics page
    response = requests.get(lyrics_url, headers=get_random_headers(), timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    lyrics_div = soup.find('pre', id='lyric-body-text')
    if not lyrics_div:
        return None
        
    return clean_lyrics(lyrics_div.get_text())

def try_musixmatch(artist, song_title):
    """Try to get lyrics from MusixMatch - often has partial lyrics only"""
    # Prepare URL-friendly strings
    artist_url = artist.replace(' ', '-').lower()
    title_url = song_title.replace(' ', '-').lower()
    url = f"https://www.musixmatch.com/lyrics/{artist_url}/{title_url}"
    
    response = requests.get(url, headers=get_random_headers(), timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    lyrics_spans = soup.find_all('span', class_=re.compile('lyrics__content'))
    if lyrics_spans:
        lyrics = "\n".join([span.get_text(separator="\n") for span in lyrics_spans])
        return clean_lyrics(lyrics)
    
    return None

def google_lyrics_search(artist, song_title):
    """Search Google for lyrics as a last resort"""
    query = f"{artist} {song_title} lyrics"
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    
    response = requests.get(url, headers=get_random_headers(), timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check if Google has lyrics in its info box
    lyrics_box = soup.find('div', class_=re.compile('hwc'))
    if lyrics_box:
        lyrics_spans = lyrics_box.find_all(['span', 'div'], class_=re.compile('ujudUb'))
        if lyrics_spans:
            lyrics = "\n".join([span.get_text() for span in lyrics_spans])
            return clean_lyrics(lyrics)
    
    # Otherwise try to find a lyrics site link
    sites = ["azlyrics.com", "genius.com", "lyrics.com", "musixmatch.com"]
    for link in soup.find_all('a'):
        href = link.get('href', '')
        if "url?q=" in href:
            actual_url = href.split("url?q=")[1].split("&")[0]
            if any(site in actual_url for site in sites):
                try:
                    print(f"Found link: {actual_url}")
                    response = requests.get(actual_url, headers=get_random_headers(), timeout=10)
                    return extract_lyrics_from_url(actual_url, response.text)
                except:
                    continue
    
    return "Could not find lyrics through Google search"

def extract_lyrics_from_url(url, html_content):
    """Extract lyrics based on the website URL"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    if "genius.com" in url:
        lyrics_divs = soup.find_all('div', attrs={'data-lyrics-container': 'true'})
        if lyrics_divs:
            return clean_lyrics("\n".join([div.get_text(separator="\n") for div in lyrics_divs]))
    
    elif "azlyrics.com" in url:
        main_div = soup.find('div', class_='col-xs-12 col-lg-8 text-center')
        if main_div:
            for div in main_div.find_all('div'):
                if not div.get('class') and not div.get('id'):
                    text = div.get_text()
                    if len(text) > 100:
                        return clean_lyrics(text)
    
    elif "lyrics.com" in url:
        lyrics_div = soup.find('pre', id='lyric-body-text')
        if lyrics_div:
            return clean_lyrics(lyrics_div.get_text())
    
    elif "musixmatch.com" in url:
        lyrics_spans = soup.find_all('span', class_=re.compile('lyrics__content'))
        if lyrics_spans:
            return clean_lyrics("\n".join([span.get_text() for span in lyrics_spans]))
    
    return "Could not extract lyrics from the found page"

def clean_lyrics(lyrics_text):
    """Clean up the lyrics text"""
    # Remove extra whitespace and normalize line breaks
    lyrics = re.sub(r'\s*\n\s*', '\n', lyrics_text.strip())
    lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
    
    # Remove common annotations and ads
    lyrics = re.sub(r'\[.+?\]', '', lyrics)
    lyrics = re.sub(r'\(.+?\)', '', lyrics)
    lyrics = re.sub(r'<!--.*?-->', '', lyrics, flags=re.DOTALL)
    
    return lyrics



def get_song_details(artist, title):
    """
    Get comprehensive details about a song including lyrics
    
    Args:
        artist: Artist name
        song_title: Song title
        
    Returns:
        Dictionary with song details
    """
    # Generate a clean ID for the song based on artist and title
    clean_artist = re.sub(r'[^\w\s]', '', artist.lower()).strip()
    clean_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
    song_id = f"{clean_artist}_{clean_title}".replace(' ', '_')
    
    # Get lyrics using existing function
  # Random delay to avoid blocking
    lyrics = get_lyrics(artist, title)
    lyrics_status = "found" if lyrics and not lyrics.startswith("Could not find") else "not_found"
    
    # Create the song details dictionary
    song_details = {
        "song_id": song_id,
        "title": title,
        "artist": artist,
        "metadata": {
            "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lyrics_status": lyrics_status,
            "lyrics_source": determine_lyrics_source(lyrics) if lyrics_status == "found" else None,
            "lyrics_length": len(lyrics) if lyrics else 0
        },
        "lyrics": lyrics
    }
    
    return song_details

def determine_lyrics_source(lyrics):
    """Try to determine the source of lyrics based on content patterns"""
    if not lyrics:
        return None
    
    if "genius.com" in lyrics.lower():
        return "genius"
    elif "azlyrics.com" in lyrics.lower():
        return "azlyrics"
    elif "musixmatch" in lyrics.lower():
        return "musixmatch"
    elif "lyrics.com" in lyrics.lower():
        return "lyrics.com"
    elif "google" in lyrics.lower():
        return "google"
    else:
        return "unknown"

# def save_song_lyrics(song_details, base_dir="song_details"):
#     """Save song details to a JSON file in the appropriate directory"""
#     # Create base directory if it doesn't exist
#     os.makedirs(base_dir, exist_ok=True)
    
#     # Get song ID for file naming
#     song_id = song_details["song_id"]
    
#     # Create artist directory if it doesn't exist
#     artist_dir = os.path.join(base_dir, re.sub(r'[\\/*?:"<>|]', "", song_details["artist"].lower().replace(' ', '_')))
#     os.makedirs(artist_dir, exist_ok=True)
    
#     # Define file path
#     file_path = os.path.join(artist_dir, f"{song_id}.json")
    
#     # Write the data
#     with open(file_path, 'w', encoding='utf-8') as f:
#         json.dump(song_details, f, indent=2, ensure_ascii=False)
    
#     print(f"Saved details for '{song_details['title']}' to {file_path}")
    
#     return file_path
# Change this in utils/web_scraper.py
def save_song_lyrics(artist, title, base_dir="song_details"):
    """Save song lyrics to a JSON file"""
    # First get the song details
    song_details = get_song_details(artist, title)
    
    # Create base directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Generate a clean ID for the song based on artist and title
    clean_artist = re.sub(r'[^\w\s]', '', artist.lower()).strip()
    clean_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
    song_id = f"{clean_artist}_{clean_title}".replace(' ', '_')
    
    # Create artist directory if it doesn't exist
    artist_dir = os.path.join(base_dir, clean_artist.replace(' ', '_'))
    os.makedirs(artist_dir, exist_ok=True)
    
    # Define file path
    file_path = os.path.join(artist_dir, f"{song_id}.json")
    
    # Write the data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(song_details, f, indent=2, ensure_ascii=False)
    
    print(f"Saved details for '{title}' to {file_path}")
    
    return file_path


'''
# Enhanced example usage
if __name__ == "__main__":
    # Test with a few songs
    songs = [
        ("kodaline", "All I Want"),
    ]
    
    successful_songs = []
    failed_songs = []
    
    for artist, title in songs:
        print(f"\n{'='*50}")
        print(f"Processing: {artist} - {title}")
        
        # Get song details including lyrics
        song_details = get_song_details(artist, title)
        
        # Save to JSON file
        file_path = save_song_lyrics(artist, title)
        
        # Display preview of lyrics
        lyrics = song_details["lyrics"]
        print(f"\n📝 {artist} - {title}\n")
        if lyrics and not lyrics.startswith("Could not find"):
            print(lyrics[:300] + "..." if len(lyrics) > 300 else lyrics)
            successful_songs.append((artist, title))
        else:
            print("No lyrics found.")
            failed_songs.append((artist, title))
        
        time.sleep(1)  # Small delay between songs
    
    # Print summary
    print("\n" + "="*50)
    print(f"Summary: Processed {len(songs)} songs")
    print(f"Success: {len(successful_songs)} songs")
    print(f"Failed: {len(failed_songs)} songs")
    if failed_songs:
        print("\nFailed songs:")
        for artist, title in failed_songs:
            print(f"- {artist} - {title}")

            '''