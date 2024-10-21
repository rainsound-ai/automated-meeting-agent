from fastapi import HTTPException
import logging
import re
from pytubefix import YouTube
from pytubefix.cli import on_progress
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_youtube_captions_or_audio(youtube_url: str) -> str:
    logger.info(f"💡 Downloading video from YouTube link: {youtube_url}")
    captions_available = False
    video_path = None
    
    try:
        yt = YouTube(youtube_url, on_progress_callback = on_progress)
        print("🚨video title", yt.title)
        
        for caption_key in ['a.en', 'en']:
            try:
                youtube_captions = yt.captions[caption_key]
                if youtube_captions:
                    captions_available = True
                    break
            except (KeyError, AttributeError):
                continue
        if youtube_captions:
            # Remove caption numbers and timestamps
            youtube_captions.save_captions("captions.txt")
            
            # get the file called captions.txt at the root of the directory
            with open("captions.txt") as f:
                youtube_captions_txt = f.read()

            cleaned_captions = re.sub(r'^\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', youtube_captions_txt, flags=re.MULTILINE)

            # Remove any remaining empty lines
            cleaned_captions = re.sub(r'\n\s*\n', '\n', cleaned_captions)

            # Remove leading/trailing whitespace from each line
            cleaned_captions = '\n'.join(line.strip() for line in cleaned_captions.split('\n') if line.strip())

            # save cleaned captions to a file called captions.txt
            with open("captions.txt", "w") as f:
                f.write(cleaned_captions)

            captions_available = True
        else:
            logger.info("🚨 No captions available for this video.")
            youtube_audio = yt.streams.get_audio_only()
            video_path = youtube_audio.download(mp3=True)
            captions_available = False
        return video_path, captions_available
 
    
    except Exception as e:
        logger.error(f"🚨 Error downloading YouTube video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading YouTube video: {str(e)}")