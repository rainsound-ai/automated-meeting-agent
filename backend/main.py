from app.lib.Env import environment
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.api.update_notion_with_transcript_and_summary import update_notion_with_transcript_and_summary
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

app = FastAPI()
scheduler = AsyncIOScheduler()
is_task_running = False

# CORS settings
prefix = "/api"

print(f"Running in {environment} environment")

# Get allowed origins from environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

if environment == "dev":
    print("Setting up CORS middleware for dev")
    logger = logging.getLogger("uvicorn")
    logger.warning("Running in development mode - allowing all origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif allowed_origins:
    print("Setting up CORS middleware for production with specified origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
else:
    print("No CORS middleware set up - API will not be accessible from browsers")

app.include_router(api_router, prefix=prefix)

async def scheduled_task():
    global is_task_running
    if is_task_running:
        print("Previous task is still running. Skipping this run.")
        return

    is_task_running = True
    try:
        await update_notion_with_transcript_and_summary()
    except Exception as e:
        print(f"Error in scheduled task: {str(e)}")
    finally:
        is_task_running = False

@app.on_event("startup")
async def startup_event():
    print("Running Notion update on startup")
    await update_notion_with_transcript_and_summary()
    
    # Schedule the task to run every 15 minutes
    scheduler.add_job(scheduled_task, CronTrigger.from_crontab("*/15 * * * *"))
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

if environment == "dev":
    if __name__ == "__main__":
        uvicorn.run(app="main:app", host="0.0.0.0", reload=True)