from openai import OpenAI
from app.lib.Env import open_ai_api_key
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=open_ai_api_key)

async def get_openai_chat_response(prompt: str, transcription= "") -> str:
    try:
        response = client.chat.completions.create(
            model="o1-mini",
            messages=[{"role": "user", "content": prompt + transcription}]
        )
        if not response or not response.choices:
            raise ValueError("Invalid response from OpenAI")
            
        content = response.choices[0].message.content
        logger.info(f"💡 OpenAI API response: {content}")
        return content
    except Exception as e:
        logger.error(f"🚨 Error getting OpenAI response: {str(e)}")
        raise  # Propagate the error instead of returning None