from dotenv import load_dotenv
import os

load_dotenv()

environment = os.getenv("ENVIRONMENT")
open_ai_api_key = os.getenv("OPENAI_API_KEY")
