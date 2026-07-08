from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("🚀 Starting up...")
    # e.g., connect to DB, load models, etc.
    # app.state.db = await connect_to_db()

    yield  # The app runs here

    # --- Shutdown ---
    logger.info("🛑 Shutting down...")
    # e.g., close connections
    # await app.state.db.close()
