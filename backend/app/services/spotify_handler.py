from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
import json
from app.lib.Env import spotify_client_id, spotify_client_secret

def get_spotify_client():
    """
    Create Spotify client using Client Credentials flow.
    No user authentication required.
    """
    client_credentials_manager = SpotifyClientCredentials(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret
    )
    sp = Spotify(client_credentials_manager=client_credentials_manager)
    return sp

def get_episode_id_from_url(spotify_url):
    """
    Extract episode ID from Spotify URL or URI.
    
    Examples:
    - https://open.spotify.com/episode/1234567890abcdef1234567890abcdef
    - spotify:episode:1234567890abcdef1234567890abcdef
    """
    if "spotify.com/episode/" in spotify_url:
        return spotify_url.split("/episode/")[1].split("?")[0]
    elif "spotify:episode:" in spotify_url:
        return spotify_url.split("spotify:episode:")[1]
    else:
        raise ValueError("Invalid Spotify episode URL or URI")

def handle_spotify(spotify_url):
    """Get transcript for a Spotify podcast episode."""
    episode_id = get_episode_id_from_url(spotify_url)
    sp = get_spotify_client()
    print(f"🚨 Client initialized: {sp}")

    try:
        # Fetch episode details
        episode = sp.episode(episode_id)
        # Uncomment the next line to inspect the full episode object
        # print(json.dumps(episode, indent=2))
        
        print(f"Episode found: {episode['name']}")
        print(f"Show: {episode['show']['name']}")
        print(f"Language: {episode.get('language', 'unknown')}")
        print(f"Duration: {episode['duration_ms'] / 1000 / 60:.1f} minutes")
        
        # Inspect all fields to find where the transcript might be
        # For debugging purposes, you can uncomment the following line
        # print(json.dumps(episode, indent=2))
        
        # Attempt to retrieve the transcript from known fields
        transcript = None

        # Example 1: Check if transcript is in the 'description'
        if 'description' in episode and 'transcript' in episode['description'].lower():
            transcript = episode['description']
            print("Transcript found in 'description' field.")
        
        # Example 2: Check for a custom field (hypothetical)
        # Adjust the key based on actual data structure
        if not transcript and 'transcript' in episode:
            transcript = episode['transcript']
            print("Transcript found in 'transcript' field.")
        
        if transcript:
            return transcript
        else:
            print("Transcript not available in the fetched episode data.")
            return None

    except Exception as e:
        print(f"Error fetching episode or transcript: {e}")
        return None
