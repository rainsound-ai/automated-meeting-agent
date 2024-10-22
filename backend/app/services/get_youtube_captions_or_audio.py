import re
import os
import logging
import nltk
from pytubefix import YouTube
from pytubefix.cli import on_progress
from fastapi import HTTPException
from deepmultilingualpunctuation import PunctuationModel

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download NLTK data if not already present
nltk.download('punkt')

async def get_youtube_captions_or_audio(youtube_url: str) -> str:
    """
    Downloads YouTube captions or audio. If captions are available, cleans and punctuates them.
    Otherwise, downloads the audio.
    
    Returns:
        str: Path to the audio file if captions are not available.
    """
    logger.info(f"💡 Downloading video from YouTube link: {youtube_url}")
    captions_available = False
    video_path = None
    punctuated_transcript = ""
    
    try:
        yt = YouTube(youtube_url, on_progress_callback=on_progress)
        print("🚨 Video Title:", yt.title)
        
        # Attempt to find English captions
        for caption_key in ['en', 'a.en']:
            try:
                youtube_captions = yt.captions[caption_key]
                if youtube_captions:
                    captions_available = True
                    break
            except (KeyError, AttributeError):
                continue
        
        captions_available = False
        if captions_available:
            # Save captions to a temporary file
            temp_caption_file = "captions.srt"
            youtube_captions.download(title=temp_caption_file)
            
            # Read the SRT file
            for suffix in ['en', 'a.en']:
              try:
                with open("captions (" + suffix + ").srt", 'r', encoding='utf-8') as f:
                    youtube_captions_txt = f.read()
                    break
              except FileNotFoundError:
                continue
            
            # Clean the captions by removing numbers and timestamps
            cleaned_captions = re.sub(r'^\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', youtube_captions_txt, flags=re.MULTILINE)
            cleaned_captions = re.sub(r'\n\s*\n', '\n', cleaned_captions)  # Remove empty lines
            cleaned_captions = '\n'.join(line.strip() for line in cleaned_captions.split('\n') if line.strip())
            
            # Initialize the punctuation model
            model = PunctuationModel()
            logger.info("🛠 Restoring punctuation...")
            punctuated_transcript = model.restore_punctuation(cleaned_captions)
            
            # Optionally, capitalize sentences
            sentences = nltk.sent_tokenize(punctuated_transcript)
            capitalized_sentences = [sentence.capitalize() for sentence in sentences]
            punctuated_transcript = ' '.join(capitalized_sentences)
            
            # Save the punctuated transcript to a file
            output_path = "captions_punctuated.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(punctuated_transcript)
            
            logger.info(f"✅ Punctuated transcript saved to '{output_path}'")
            
            # Delete the SRT file
            for suffix in ['en', 'a.en']:
                try:
                    os.remove("captions (" + suffix + ").srt")
                    break
                except FileNotFoundError:
                    continue
            
            captions_available = True
        else:
            logger.info("🚨 No captions available for this video. Downloading audio instead.")
            youtube_audio = yt.streams.get_audio_only()
            video_path = youtube_audio.download()
            logger.info(f"✅ Audio downloaded to '{video_path}'")

        return video_path, captions_available
    
    except Exception as e:
        logger.error(f"🚨 Error downloading YouTube video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading YouTube video: {str(e)}")