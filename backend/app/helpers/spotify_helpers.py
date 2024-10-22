def is_spotify_link(url: str) -> bool:
   """
   Check if a URL is a valid Spotify episode link
   
   Args:
       url (str): URL to check
       
   Returns:
       bool: True if valid Spotify episode URL, False otherwise
       
   Examples:
       >>> is_spotify_link("https://open.spotify.com/episode/3OgWEiux8vnqZ2eRf5y9OY")
       True
       >>> is_spotify_link("https://open.spotify.com/episode/3OgWEiux8vnqZ2eRf5y9OY?si=72228ca0626c4f5a")
       True
       >>> is_spotify_link("https://something-else.com")
       False
   """
   return (
       url.startswith("https://open.spotify.com/episode/") or 
       url.startswith("spotify:episode:")
   )