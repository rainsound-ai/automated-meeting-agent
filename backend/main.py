from app.lib.Env import environment
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
import sys
from app.lib import JsonSchemas

app = FastAPI()

# CORS settings
frontend_url = "https://meeting-agent-frontend.onrender.com"

# We want this service's endpoints to be available from /api.
prefix = "/api"
print(f"Running in {environment} environment")
if environment == "dev":
    print("setting up CORS middleware for dev")
    prefix = prefix
    logger = logging.getLogger("uvicorn")
    logger.warning("Running in development mode - allowing CORS for all origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # In production, allow only the frontend URL
    print("setting up CORS middleware for production")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],  # Allow only the SvelteKit frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=prefix)

if environment == "dev":
    if __name__ == "__main__":
        if "--save-json-schemas" in sys.argv:
            JsonSchemas.save_all()
        else:
            uvicorn.run(app="main:app", host="0.0.0.0", reload=True)
