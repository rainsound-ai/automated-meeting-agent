from app.lib.Env import environment
import logging
import asyncio
from app.api.update_notion_with_transcript_and_summary import update_notion_with_transcript_and_summary

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"💡 Running in {environment} environment")

async def run_update_task():
    try:
        logger.info("🌺Starting Notion update task")
        await update_notion_with_transcript_and_summary()
        logger.info("🎬 Notion update task completed successfully")
    except Exception as e:
        logger.error(f"🚨 Error in Notion update task: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_update_task())